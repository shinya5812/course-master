# -*- coding: utf-8 -*-
"""
grade_race_predictor.py - 重賞レース予測モジュール

G1/G2/G3重賞に特化した予測スクリプト。
CourseMASTERv73エンジンで◎/○/▲を予測し、荒れ指数も算出する。

【使い方】
  # デモ実行（愛知杯2026-03-22のデータで動作確認）
  python grade_race_predictor.py --demo

  # Claude（Playwright MCP）からJSONデータを渡して予測
  python grade_race_predictor.py --race '<JSON>'

【JSONフォーマット（--race モード）】
  {
    "race_name": "愛知杯 GⅢ",
    "venue": "中京",
    "surface": "芝",
    "distance": 1400,
    "track_cond": "良",
    "horses": [
      {"horse_no": 1, "horse_name": "...", "jockey": "...",
       "sire": "...", "dam_sire": "...", "age": 5, "weight": 55.0,
       "popularity": 1, "odds": 3.6},
      ...
    ]
  }
"""

import os
import sys
import json
import io

# Windows環境での日本語出力設定
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# エンジン・データのパス
PKL_PATH   = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_CSV  = os.path.join(BASE_DIR, 'data', 'pedigree', '血統_0410.csv')

# エンジンをインポート可能にする
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np


# ─────────────────────────────────────────────────────────
# グレード判定
# ─────────────────────────────────────────────────────────
GRADE_KEYWORDS = {
    'G1': ['G1', 'GⅠ'],
    'G2': ['G2', 'GⅡ'],
    'G3': ['G3', 'GⅢ'],
}

def detect_grade(race_name: str):
    """
    レース名からグレードを検出する。
    戻り値: 'G1' / 'G2' / 'G3' / None（グレードレースでない）
    """
    for grade, keywords in GRADE_KEYWORDS.items():
        for kw in keywords:
            if kw in race_name:
                return grade
    return None


# ─────────────────────────────────────────────────────────
# エンジン読み込み
# ─────────────────────────────────────────────────────────
def load_engine():
    """CourseMASTERv73エンジンをpklと血統CSVから読み込む。"""
    from course_master_v73_engine import CourseMASTERv73

    engine = CourseMASTERv73()
    engine.load(PKL_PATH)

    engine.df_blood = pd.read_csv(BLOOD_CSV, encoding='cp932')
    print(f'  エンジン読み込み完了（pkl: {os.path.basename(PKL_PATH)}  血統: {len(engine.df_blood):,}馬）')
    return engine


# ─────────────────────────────────────────────────────────
# JSON → DataFrame変換（score_race()互換）
# ─────────────────────────────────────────────────────────
def build_race_df(race: dict) -> pd.DataFrame:
    """
    レースJSON → score_race()に渡せるDataFrameに変換する。
    未取得項目（走破時計・通過順等）は0を設定し、
    エンジン内部でデフォルト50点が適用される。
    """
    distance = int(race.get('distance', 0))
    venue    = race.get('venue', '')
    surface  = race.get('surface', '芝')
    cond     = race.get('track_cond', '良')

    rows = []
    for h in race['horses']:
        rows.append({
            '馬名':             h.get('horse_name', ''),
            '騎手名':           h.get('jockey', ''),
            '父馬名':           h.get('sire', ''),
            '母の父馬名':       h.get('dam_sire', ''),
            '人気順':           int(h.get('popularity', 0)),
            '単勝オッズ_num':   float(h.get('odds', 0.0)),
            '斤量_num':         float(h.get('weight', 56.0)),
            '年齢':             int(h.get('age', 4)),
            '馬体重_num':       float(h.get('body_weight', 0)),
            # 予測前なので走破時計・上がり・通過順は取得不可 → 0でデフォルト50点
            '走破時計_sec':         0.0,
            '上がり3Fタイム_sec':   0.0,
            '通過順1':  0,
            '通過順2':  0,
            '通過順3':  0,
            '通過順4':  0,
            '確定着順': 0,
            'クラスコード': int(race.get('class_code', 800)),
            '場所':    venue,
            '芝・ダ':  surface,
            '距離':    distance,
            '馬場状態': cond,
        })

    df = pd.DataFrame(rows)
    return df


# ─────────────────────────────────────────────────────────
# 荒れ指数計算（3要素加重平均）
# ─────────────────────────────────────────────────────────
def calc_chaos_index(race: dict) -> dict:
    """
    荒れ指数を3要素の加重平均で算出する（0〜100）。

    要素A（オッズ分散 40%）:
        ratio = 1番人気オッズ / 3番人気オッズ
        比が1に近い = 混戦 = 荒れやすい
        比が小さい（0.1前後）= 本命圧倒 = 荒れにくい
        score_A = min(100, ratio * 100)

    要素B（人気集中度 40%）:
        support = (1/odds_1番人気) / Σ(1/全馬odds)
        1番人気への資金集中度。高いほど本命決着しやすい。
        score_B = max(0, min(100, (0.50 - support) / 0.20 * 100))
        ※ support=30%→100点（超分散）/ support=50%→0点（本命圧倒）

    要素C（馬場状態 20%）:
        良=20 / 稍重=50 / 重=80 / 不良=100

    Final = 0.4×A + 0.4×B + 0.2×C

    ラベル: 0〜30:安定 / 30〜50:やや波乱含み / 50〜70:波乱の可能性あり / 70〜:大波乱注意
    """
    horses     = race['horses']
    track_cond = race.get('track_cond', '良')

    # 人気順でソート
    sorted_h = sorted(horses, key=lambda h: int(h.get('popularity', 99)))

    if len(sorted_h) < 3:
        return {'score': 50.0, 'A': 50.0, 'B': 50.0, 'C': 50.0, 'label': 'データ不足'}

    odds_1 = float(sorted_h[0].get('odds', 1.0)) or 1.0
    odds_3 = float(sorted_h[2].get('odds', 1.0)) or 1.0

    # 要素A: オッズ分散
    score_A = min(100.0, (odds_1 / odds_3) * 100.0)

    # 要素B: 人気集中度
    inv_sum = sum(1.0 / max(float(h.get('odds', 99.9)), 0.1) for h in horses)
    if inv_sum > 0:
        support = (1.0 / odds_1) / inv_sum
    else:
        support = 0.5
    score_B = max(0.0, min(100.0, (0.50 - support) / 0.20 * 100.0))

    # 要素C: 馬場状態
    cond_map = {'良': 20.0, '稍重': 50.0, '重': 80.0, '不良': 100.0}
    score_C  = cond_map.get(track_cond, 20.0)

    final = 0.4 * score_A + 0.4 * score_B + 0.2 * score_C

    if final < 30:
        label = '安定（本命有力）'
    elif final < 50:
        label = 'やや波乱含み'
    elif final < 70:
        label = '波乱の可能性あり'
    else:
        label = '大波乱注意'

    return {
        'score': round(final, 1),
        'A':     round(score_A, 1),
        'B':     round(score_B, 1),
        'C':     score_C,
        'label': label,
    }


# ─────────────────────────────────────────────────────────
# 予測実行
# ─────────────────────────────────────────────────────────
def _calc_edge(win_prob: float, odds: float) -> float | None:
    """エッジ値 = エンジン推定勝率 - 市場確率（1/オッズ×0.80）"""
    if odds <= 0:
        return None
    return win_prob - (1.0 / odds) * 0.80


def edge_label(edge) -> str:
    """エッジ値 → 購入判定ラベル"""
    if edge is None:
        return '  -  '
    if edge >= 0.05:
        return '★購入推奨'
    elif edge >= 0.00:
        return '△様子見  '
    else:
        return '✗見送り  '


def run_prediction(engine, race: dict) -> dict:
    """
    エンジンで◎/○/▲を予測する。

    戻り値:
        {
          '◎': [(horse_name, score, win_prob, idx, edge)],   ← 1頭
          '○': [(horse_name, score, win_prob, idx, edge)],   ← 3頭
          '▲': [(horse_name, score, win_prob, idx, edge)],   ← 5頭
          'all': [(idx, horse_name, score, win_prob, edge)]  ← 全馬・スコア降順
        }
        edge: エッジ値（float）またはNone（オッズ不明時）
    """
    race_df   = build_race_df(race)
    scores    = engine.score_race(race_df)
    win_probs = engine.score_to_win_prob(scores, race_df)

    # オッズ辞書（馬名 → odds）を事前構築
    odds_map = {h['horse_name']: float(h.get('odds', 0)) for h in race['horses']}

    # スコア降順でソート
    sorted_entries = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    result = {'◎': [], '○': [], '▲': [], 'all': []}

    # 全馬リストを先に構築（スコア降順）
    for idx, score in sorted_entries:
        horse_name = race_df.loc[idx, '馬名']
        win_prob   = win_probs.get(idx, 0.0)
        odds       = odds_map.get(horse_name, 0.0)
        edge       = _calc_edge(win_prob, odds)
        result['all'].append((idx, horse_name, score, win_prob, edge))

    # all リストからスライスで印を割り当て
    # → 出走頭数に関わらず ◎1頭・○最大3頭・▲最大5頭を確実に確保
    def _to_mark(t):
        idx, horse_name, score, win_prob, edge = t
        return (horse_name, score, win_prob, idx, edge)

    n = len(result['all'])
    if n >= 1:
        result['◎'] = [_to_mark(result['all'][0])]
    if n >= 2:
        result['○'] = [_to_mark(t) for t in result['all'][1:4]]
    if n >= 5:
        result['▲'] = [_to_mark(t) for t in result['all'][4:9]]

    return result


# ─────────────────────────────────────────────────────────
# 結果表示
# ─────────────────────────────────────────────────────────
def print_result(race: dict, prediction: dict, chaos: dict):
    """予測結果・荒れ指数・エッジ値判定・購入サマリーを日本語で整形表示する。"""
    grade    = detect_grade(race['race_name']) or '重賞'
    distance = int(race.get('distance', 0))
    print('\n' + '=' * 76)
    print(f"  {race['race_name']}  [{grade}]")
    print(f"  {race.get('venue','')} {race.get('surface','')} {distance}m  "
          f"馬場:{race.get('track_cond','')}  {len(race['horses'])}頭")
    print('=' * 76)

    # ── 荒れ指数 ──
    print(f"\n  【荒れ指数】{chaos['score']:5.1f} / 100  ─  {chaos['label']}")
    print(f"    A（オッズ分散）:{chaos['A']:6.1f}  "
          f"B（人気集中度）:{chaos['B']:6.1f}  "
          f"C（馬場）:{chaos['C']:5.1f}")
    if chaos['score'] < 50:
        chaos_strategy = '単勝◎'
    elif chaos['score'] < 70:
        chaos_strategy = '単勝◎＋馬連◎○'
    elif chaos['score'] < 85:
        chaos_strategy = '穴馬注目・単勝見送りも可'
    else:
        chaos_strategy = '見送りまたは大穴総流し'
    print(f"    → 荒れ指数戦略: {chaos_strategy}")

    # ── ◎/○/▲ ＋ エッジ値 ──
    print('\n  【予測とエッジ値】')
    horse_map = {h['horse_name']: h for h in race['horses']}
    for mark in ['◎', '○', '▲']:
        for horse_name, score, win_prob, idx, edge in prediction[mark]:
            h   = horse_map.get(horse_name, {})
            pop = h.get('popularity', '-')
            ods = h.get('odds', '-')
            hno = h.get('horse_no', '-')
            market_p = (1.0 / float(ods)) * 0.80 if isinstance(ods, (int, float)) and ods > 0 else None
            edge_str = f"{edge:+.3f}" if edge is not None else '  N/A '
            mp_str   = f"{market_p*100:.1f}%" if market_p is not None else ' N/A'
            e_label  = edge_label(edge)
            print(f"    {mark}  馬番{str(hno):>2}  {horse_name:<16}  "
                  f"スコア:{score:5.1f}  推定勝率:{win_prob*100:4.1f}%  市場:{mp_str}  "
                  f"エッジ:{edge_str}  {e_label}")

    # ── 全馬スコア一覧（上位10頭）＋ エッジ値 ──
    print('\n  【全馬スコア順位（上位10頭）】')
    print(f"    {'順':>2}  {'馬番':>2}  {'馬名':<16}  {'スコア':>6}  "
          f"{'推定勝率':>6}  {'市場確率':>6}  {'エッジ値':>7}  判定")
    print('    ' + '─' * 72)
    for rank, (idx, horse_name, score, win_prob, edge) in enumerate(prediction['all'][:10], 1):
        h        = horse_map.get(horse_name, {})
        pop      = h.get('popularity', '-')
        ods      = h.get('odds', '-')
        hno      = h.get('horse_no', '-')
        market_p = (1.0 / float(ods)) * 0.80 if isinstance(ods, (int, float)) and ods > 0 else None
        edge_str = f"{edge:+.3f}" if edge is not None else '  N/A'
        mp_str   = f"{market_p*100:.1f}%" if market_p is not None else ' N/A'
        e_label  = edge_label(edge)
        print(f"    {rank:2}  {str(hno):>2}  {horse_name:<16}  "
              f"{score:6.1f}  {win_prob*100:5.1f}%  {mp_str:>6}  {edge_str:>7}  {e_label}")

    # ── 最終購入判断サマリー ──
    print('\n' + '─' * 76)
    print('  【最終購入判断サマリー】')

    # ◎の情報を取得
    if prediction['◎']:
        honmei_name, honmei_score, honmei_wp, honmei_idx, honmei_edge = prediction['◎'][0]
        h_main = horse_map.get(honmei_name, {})
        honmei_pop  = int(h_main.get('popularity', 0))
        honmei_dist = distance
    else:
        honmei_name = '(なし)'
        honmei_pop  = 0
        honmei_edge = None
        honmei_dist = distance

    # 条件①: 穴馬戦略（◎4番人気以上 × 距離2200m未満）
    is_anaba = (honmei_pop >= 4) and (honmei_dist < 2200)
    anaba_str = '✅ 該当（◎{}番人気・{}m）'.format(honmei_pop, honmei_dist) if is_anaba \
                else '─ 非該当（◎{}番人気）'.format(honmei_pop)

    # 条件②: エッジ値フィルター（+0.05以上 × 距離2200m未満）
    edge_ok    = (honmei_edge is not None) and (honmei_edge >= 0.05) and (honmei_dist < 2200)
    edge_ng_ld = (honmei_edge is not None) and (honmei_edge >= 0.05) and (honmei_dist >= 2200)
    if edge_ok:
        edge_filt_str = '✅ 購入（エッジ{:+.3f}・{}m）'.format(honmei_edge, honmei_dist)
    elif edge_ng_ld:
        edge_filt_str = '─ 見送り（エッジはプラスだが2200m以上）'
    elif honmei_edge is not None and honmei_edge < 0.05:
        edge_filt_str = '✗ 見送り（エッジ{:+.3f} < +0.05閾値）'.format(honmei_edge)
    else:
        edge_filt_str = '─ 判定不可（オッズ不明）'

    # 条件③: 荒れ指数（50〜60×良馬場→堅め補正）
    cond_track   = race.get('track_cond', '良')
    is_firm      = (50.0 <= chaos['score'] <= 60.0) and (cond_track == '良')
    chaos_note   = '⚠ 荒れ指数50〜60×良馬場 → 堅め決着補正あり' if is_firm else \
                   f"荒れ指数{chaos['score']:.1f}（{chaos['label']}）"

    print(f"\n    ①穴馬戦略   : {anaba_str}")
    print(f"    ②エッジ値   : {edge_filt_str}")
    print(f"    ③荒れ指数   : {chaos_note}")

    # 総合判断
    print()
    if edge_ok and is_anaba:
        verdict = f'★★ ◎{honmei_name} 単勝 強推奨（穴馬戦略＋エッジ両方該当）'
    elif edge_ok:
        verdict = f'★  ◎{honmei_name} 単勝 購入推奨（エッジ+0.05以上）'
    elif is_anaba:
        verdict = f'△  ◎{honmei_name} 単勝 検討（穴馬戦略は該当・エッジ基準未達）'
    elif honmei_edge is not None and honmei_edge < 0:
        verdict = f'✗  ◎{honmei_name} 単勝 見送り推奨（エッジ{honmei_edge:+.3f}・市場過大評価）'
    else:
        verdict = f'△  ◎{honmei_name} 単勝 様子見（エッジ+0.05未満）'

    # 荒れ指数が高い場合の追記
    if chaos['score'] >= 85:
        verdict += '  ※荒れ指数85以上: 全体見送りも選択肢'
    elif chaos['score'] >= 70:
        verdict += '  ※荒れ指数70以上: 穴馬注目'

    print(f"    ▶ 総合判断: {verdict}")
    print('─' * 76)
    print('=' * 76)
    print()


# ─────────────────────────────────────────────────────────
# デモデータ（愛知杯 2026-03-22 中京芝1400m 18頭）
# ─────────────────────────────────────────────────────────
# ※ オッズ・人気は一部推定値を含む。実際の結果: 1着アイサンサン（12番人気・27.6倍）
DEMO_RACE = {
    'race_name':  '愛知杯 GⅢ',
    'venue':      '中京',
    'surface':    '芝',
    'distance':   1400,
    'track_cond': '良',
    'class_code': 800,
    'horses': [
        # 馬番  馬名                     騎手            父馬              母父               年 斤量   人気  オッズ
        {'horse_no':  1, 'horse_name': 'ドロップオブライト', 'jockey': '坂井瑠星', 'sire': 'モーリス',        'dam_sire': 'ハービンジャー',    'age': 5, 'weight': 55.0, 'popularity':  1, 'odds':  3.6},
        {'horse_no':  2, 'horse_name': 'コガネノソラ',       'jockey': '幸英明',    'sire': 'ロードカナロア',   'dam_sire': 'スクリーンヒーロー', 'age': 5, 'weight': 54.0, 'popularity':  8, 'odds': 18.5},
        {'horse_no':  3, 'horse_name': 'サンセットビュー',   'jockey': '岩田望来',  'sire': 'キズナ',          'dam_sire': 'スペシャルウィーク', 'age': 5, 'weight': 55.0, 'popularity':  5, 'odds':  9.1},
        {'horse_no':  4, 'horse_name': 'ルージュスエルテ',   'jockey': '団野大成',  'sire': 'ハーツクライ',     'dam_sire': 'ロードカナロア',     'age': 5, 'weight': 55.0, 'popularity':  7, 'odds': 14.3},
        {'horse_no':  5, 'horse_name': 'ピューロマジック',   'jockey': '横山武史',  'sire': 'エピファネイア',   'dam_sire': 'ダイワメジャー',     'age': 5, 'weight': 55.0, 'popularity':  2, 'odds':  4.5},
        {'horse_no':  6, 'horse_name': 'ナムラクララ',       'jockey': '幸英明',    'sire': 'キタサンブラック', 'dam_sire': 'ディープインパクト', 'age': 5, 'weight': 54.0, 'popularity':  9, 'odds': 21.4},
        {'horse_no':  7, 'horse_name': 'ソーダズリング',     'jockey': '川田将雅',  'sire': 'ソールオリエンス', 'dam_sire': 'キングカメハメハ',   'age': 4, 'weight': 54.0, 'popularity':  4, 'odds':  7.6},
        {'horse_no':  8, 'horse_name': 'レディバランタイン', 'jockey': '浜中俊',    'sire': 'ルーラーシップ',   'dam_sire': 'キングカメハメハ',   'age': 5, 'weight': 55.0, 'popularity': 11, 'odds': 26.0},
        {'horse_no':  9, 'horse_name': 'スタニングローズ',   'jockey': '池添謙一',  'sire': 'キングカメハメハ', 'dam_sire': 'ルーラーシップ',     'age': 6, 'weight': 55.0, 'popularity':  3, 'odds':  5.8},
        {'horse_no': 10, 'horse_name': 'ウインピクシス',     'jockey': '松山弘平',  'sire': 'シルバーステート', 'dam_sire': 'ハービンジャー',     'age': 5, 'weight': 55.0, 'popularity': 13, 'odds': 33.2},
        {'horse_no': 11, 'horse_name': 'サクセスシュート',   'jockey': '荻野極',    'sire': 'ハービンジャー',   'dam_sire': 'ダイワメジャー',     'age': 6, 'weight': 55.0, 'popularity': 14, 'odds': 44.7},
        {'horse_no': 12, 'horse_name': 'エリカヴィータ',     'jockey': '岩田康誠',  'sire': 'ブラックタイド',   'dam_sire': 'アドマイヤムーン',   'age': 7, 'weight': 55.0, 'popularity': 10, 'odds': 22.8},
        {'horse_no': 13, 'horse_name': 'ミアネーロ',         'jockey': '菅原明良',  'sire': 'モーリス',         'dam_sire': 'ダイワメジャー',     'age': 5, 'weight': 54.0, 'popularity':  6, 'odds': 12.4},
        {'horse_no': 14, 'horse_name': 'コスタボニータ',     'jockey': '武豊',      'sire': 'ミッキーアイル',   'dam_sire': 'ディープインパクト', 'age': 6, 'weight': 55.0, 'popularity': 16, 'odds': 61.3},
        {'horse_no': 15, 'horse_name': 'ルビーカサブランカ', 'jockey': '藤岡佑介',  'sire': 'ルーラーシップ',   'dam_sire': 'スペシャルウィーク', 'age': 7, 'weight': 55.0, 'popularity': 15, 'odds': 53.8},
        {'horse_no': 16, 'horse_name': 'マピュース',         'jockey': '三浦皇成',  'sire': 'ディープインパクト','dam_sire': 'ジャングルポケット', 'age': 5, 'weight': 55.0, 'popularity':  3, 'odds':  7.4},
        {'horse_no': 17, 'horse_name': 'ポリプルーム',       'jockey': '永野猛蔵',  'sire': 'リオンディーズ',   'dam_sire': 'ハービンジャー',     'age': 5, 'weight': 54.0, 'popularity': 17, 'odds': 72.5},
        {'horse_no': 18, 'horse_name': 'アイサンサン',       'jockey': '松若風馬',  'sire': 'ヘニーヒューズ',   'dam_sire': 'ダイワメジャー',     'age': 5, 'weight': 55.0, 'popularity': 12, 'odds': 27.6},
    ]
}
# ↑ 実際の結果: 1着アイサンサン（馬番18・12番人気・27.6倍）大波乱
# ↑ 荒れ指数検証: 1番人気3.6倍×3番人気7.4倍 → 荒れ指数 ~63点「波乱の可能性あり」


# ─────────────────────────────────────────────────────────
# 皐月賞2026 デモデータ（中山 芝2000m G1 2026-04-20）
# ─────────────────────────────────────────────────────────
# ※ 出走馬・オッズは2026-04-15時点の想定値（未確定）
# ※ 実際の出馬表確定後に差し替えて使用すること
SATSUKI_RACE = {
    'race_name':  '皐月賞 GⅠ',
    'venue':      '中山',
    'surface':    '芝',
    'distance':   2000,
    'track_cond': '良',
    'class_code': 800,
    # 出馬表: 2026-04-19 中山11R（keibalab確認済み 2026-04-16時点）
    # オッズ: 未発売のため人気順から推定した仮置き値。4/18夕〜4/19朝に実際の値で更新すること。
    'horses': [
        {'horse_no':  1, 'horse_name': 'カヴァレリッツォ',   'jockey': 'レーン',      'sire': 'ハーツクライ',       'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 18, 'odds':120.0},
        {'horse_no':  2, 'horse_name': 'サウンドムーブ',     'jockey': '団野大成',    'sire': 'スクリーンヒーロー', 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 17, 'odds': 90.0},
        {'horse_no':  3, 'horse_name': 'サノノグレーター',   'jockey': '松山弘平',    'sire': 'ジャングルポケット', 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 15, 'odds': 75.0},
        {'horse_no':  4, 'horse_name': 'ロブチェン',         'jockey': '岩田康誠',    'sire': "Giant's Causeway", 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 14, 'odds': 65.0},
        {'horse_no':  5, 'horse_name': 'アスクエジンバラ',   'jockey': '荻野極',      'sire': 'マンハッタンカフェ', 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 13, 'odds': 55.0},
        {'horse_no':  6, 'horse_name': 'フォルテアンジェロ', 'jockey': '武豊',        'sire': 'Dark Angel',        'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 12, 'odds': 50.0},
        {'horse_no':  7, 'horse_name': 'ロードフィレール',   'jockey': '横山和生',    'sire': 'オルフェーヴル',     'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 11, 'odds': 45.0},
        {'horse_no':  8, 'horse_name': 'マテンロウゲイル',   'jockey': '佐々木大',    'sire': 'Candy Ride',        'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 10, 'odds': 40.0},
        {'horse_no':  9, 'horse_name': 'ライヒスアドラー',   'jockey': '高杉吏麒',    'sire': 'ハーツクライ',       'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  9, 'odds': 35.0},
        {'horse_no': 10, 'horse_name': 'ラージアンサンブル', 'jockey': 'ルメール',    'sire': 'ジャスタウェイ',     'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  8, 'odds': 25.0},
        {'horse_no': 11, 'horse_name': 'パントルナイーフ',   'jockey': '戸崎圭太',    'sire': 'Makfi',             'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  7, 'odds': 20.0},
        {'horse_no': 12, 'horse_name': 'グリーンエナジー',   'jockey': '西村淳也',    'sire': 'Singspiel',         'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  6, 'odds': 16.0},
        {'horse_no': 13, 'horse_name': 'アクロフェイズ',     'jockey': '岩田望来',    'sire': 'ディープインパクト', 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  5, 'odds': 12.0},
        {'horse_no': 14, 'horse_name': 'ゾロアストロ',       'jockey': '津村明秀',    'sire': 'ディープインパクト', 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  4, 'odds':  9.0},
        {'horse_no': 15, 'horse_name': 'リアライズシリウス', 'jockey': '横山武史',    'sire': 'ステイゴールド',     'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  3, 'odds':  7.5},
        {'horse_no': 16, 'horse_name': 'アルトラムス',       'jockey': '坂井瑠星',    'sire': 'スクリーンヒーロー', 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  2, 'odds':  5.5},
        {'horse_no': 17, 'horse_name': 'アドマイヤクワッズ', 'jockey': '川田将雅',    'sire': 'Zoffany',           'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 12, 'odds': 50.0},
        {'horse_no': 18, 'horse_name': 'バステール',         'jockey': '川田将雅',    'sire': 'Aldebaran',         'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  1, 'odds':  4.0},
    ]
}


# ─────────────────────────────────────────────────────────
# メイン
# ─────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    def _run_race(race):
        """共通の予測実行・表示フロー"""
        grade = detect_grade(race['race_name'])
        if grade is None:
            print(f"スキップ: {race['race_name']} はG1/G2/G3ではありません")
            return
        print(f"\n[{grade}] {race['race_name']}  "
              f"{race.get('venue','')} {race.get('surface','')} {race.get('distance','')}m  "
              f"馬場:{race.get('track_cond','')}  {len(race['horses'])}頭")
        print('エンジン読み込み中...')
        engine = load_engine()
        chaos  = calc_chaos_index(race)
        pred   = run_prediction(engine, race)
        print_result(race, pred, chaos)

    if '--demo' in args:
        # ── デモモード（愛知杯 2026-03-22）──────────────────
        _run_race(DEMO_RACE)

    elif '--satsuki' in args:
        # ── 皐月賞2026 デモモード ────────────────────────────
        _run_race(SATSUKI_RACE)

    elif '--race' in args:
        # ── Claude（Playwright MCP）からJSONデータを受け取るモード ──
        idx = args.index('--race')
        if idx + 1 >= len(args):
            print('[エラー] --race の後にJSONを指定してください。')
            sys.exit(1)
        try:
            race = json.loads(args[idx + 1])
        except json.JSONDecodeError as e:
            print(f'[エラー] JSON解析に失敗しました: {e}')
            sys.exit(1)

        _run_race(race)

    else:
        # ── 使い方案内 ──────────────────────────────────────
        print()
        print('【grade_race_predictor.py - 重賞レース予測モジュール】')
        print()
        print('使い方:')
        print('  python grade_race_predictor.py --demo')
        print('    → 愛知杯2026-03-22のデモデータで動作確認')
        print()
        print('  python grade_race_predictor.py --satsuki')
        print('    → 皐月賞2026（想定データ）で動作確認')
        print()
        print('  python grade_race_predictor.py --race \'<JSON>\'')
        print('    → ClaudeがPlaywright MCPで取得したJSONデータで予測')
        print()
        print('JSONフォーマット:')
        example = {
            'race_name': '愛知杯 GⅢ',
            'venue': '中京',
            'surface': '芝',
            'distance': 1400,
            'track_cond': '良',
            'horses': [
                {'horse_no': 1, 'horse_name': 'ドロップオブライト',
                 'jockey': '坂井瑠星', 'sire': 'モーリス', 'dam_sire': 'ハービンジャー',
                 'age': 5, 'weight': 55.0, 'popularity': 1, 'odds': 3.6},
                {'horse_no': 2, 'horse_name': '（以降同様）',
                 'jockey': '', 'sire': '', 'dam_sire': '',
                 'age': 4, 'weight': 55.0, 'popularity': 2, 'odds': 5.0},
            ]
        }
        print(json.dumps(example, ensure_ascii=False, indent=2))
        print()
        print('通常はClaudeに「grade_race_predictor.py を --demo で実行して」と')
        print('指示するだけで動作確認できます。')


if __name__ == '__main__':
    main()
