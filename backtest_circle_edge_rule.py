# -*- coding: utf-8 -*-
"""
backtest_circle_edge_rule.py
○以下エッジルール バックテスト検証

【仮説】
  ◎のエッジが閾値未達（< +0.06）でも、
  ○（エンジン上位2〜5位の馬）にエッジ+0.06以上があれば
  ◎×○ の馬連を購入する。

【比較ベースライン】
  現行ルール：◎エッジ+0.06以上 → 単勝購入

使い方:
  python backtest_circle_edge_rule.py
"""

import sys
import io
import os
import re
import pickle
import numpy as np
import pandas as pd
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PKL_PATH   = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_FILE = os.path.join(BASE_DIR, 'data', 'pedigree', '血統_0410.csv')
CSV_FILES  = [
    os.path.join(BASE_DIR, 'data', 'race', '2015_2016結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2017_2018結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2019_2020結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2021_2023結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2024_2026結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2026結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '202602280331結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '結果202603070405.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '結果202604110419.csv'),
]

TEMPERATURE    = 5.0
BET_UNIT       = 100
EDGE_THRESHOLD = 0.06   # 標準閾値
GRADE_PAT      = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
TEST_YEAR_MIN  = 24     # 2024〜 が検証データ


# ============================================================
# ユーティリティ
# ============================================================
def detect_grade(race_name):
    if not race_name:
        return None
    m = GRADE_PAT.search(str(race_name))
    if not m:
        return None
    g = m.group()
    if g[-1] in ('Ⅰ', '1', '１'):
        return 'G1'
    elif g[-1] in ('Ⅱ', '2', '２'):
        return 'G2'
    elif g[-1] in ('Ⅲ', '3', '３'):
        return 'G3'
    return None


def dist_band(d):
    if d <= 0:
        return '不明'
    elif d <= 1400:
        return '〜1400m'
    elif d <= 2000:
        return '1600〜2000m'
    else:
        return '2200m〜'


# ============================================================
# pkl 読み込み
# ============================================================
print("■ pkl 読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

sire_stats      = state.get('sire_stats', {})
jockey_stats    = state.get('jockey_stats', {})
distance_stats  = state.get('distance_stats', {})
career_penalty  = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
odds_mk_table   = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]

print(f"  sire_stats:{len(sire_stats)}件  jockey_stats:{len(jockey_stats)}件")


# ============================================================
# CSV 読み込み
# ============================================================
print("\n■ CSV 読み込み中...")
dfs = []
for fpath in CSV_FILES:
    if os.path.exists(fpath):
        dfs.append(pd.read_csv(fpath, encoding='cp932', low_memory=False))
        print(f"  {os.path.basename(fpath)}: {len(dfs[-1]):,}件")
    else:
        print(f"  [スキップ] {os.path.basename(fpath)}")

df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}件")

for col, dtype in [('確定着順','int'),('人気順','int'),('距離','int'),('年齢','float')]:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(
        int if dtype == 'int' else float)
df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'],       errors='coerce')
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'],     errors='coerce').fillna(0.0)
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
for col in ['通過順1','通過順2','通過順3','通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

print("\n■ 血統データ読み込み...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数','全成績2着数','全成績3着数','全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)

blood_slim = df_blood[['血統登録番号','種牡馬名','母の父名']].copy()
blood_slim.columns = ['血統登録番号','父馬名_b','母の父馬名_b']
df_all = df_all.merge(blood_slim, on='血統登録番号', how='left')
df_all['父馬名']     = df_all['父馬名'].fillna(df_all['父馬名_b'])
df_all['母の父馬名'] = df_all['母の父馬名'].fillna(df_all['母の父馬名_b'])
df_all.drop(['父馬名_b','母の父馬名_b'], axis=1, inplace=True)

horse_place_rate = {}
for _, brow in df_blood.iterrows():
    name = str(brow['馬名']).strip()
    total = (brow['全成績1着数'] + brow['全成績2着数'] +
             brow['全成績3着数'] + brow['全成績着外数'])
    if total >= 5:
        placed = brow['全成績1着数'] + brow['全成績2着数'] + brow['全成績3着数']
        horse_place_rate[name] = float(placed) / float(total)

# 重賞抽出
df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None)
grade_df = df_all[df_all['grade'].notna()].copy()

grade_df['race_key'] = (
    grade_df['年'].astype(str) + '_' +
    grade_df['月'].astype(str).str.zfill(2) + '_' +
    grade_df['日'].astype(str).str.zfill(2) + '_' +
    grade_df['場所'].astype(str) + '_' +
    grade_df['日次'].astype(str) + '_' +
    grade_df['レース番号'].astype(str).str.zfill(2)
)
grade_df = grade_df.drop_duplicates(subset=['race_key','馬名'])

# 検証データのみ（2024〜）
grade_df['year_2d'] = grade_df['年'].astype(str).str[-2:].astype(int)
test_df = grade_df[grade_df['year_2d'] >= TEST_YEAR_MIN].copy()
print(f"\n検証データ（2024〜）: {test_df['race_key'].nunique()}R")


# ============================================================
# スコア計算関数（v7.3 再現）
# ============================================================
def score_horse(row, team_type='I'):
    axes = {}

    horse_name = str(row['馬名']).strip()
    bi = df_blood[df_blood['馬名'] == horse_name]
    if not bi.empty:
        total = int(bi['全成績1着数'].iloc[0] + bi['全成績2着数'].iloc[0] +
                    bi['全成績3着数'].iloc[0] + bi['全成績着外数'].iloc[0])
        wins  = int(bi['全成績1着数'].iloc[0])
        if total > 0:
            conf = min(1.0, total / 10)
            cf   = wins / total * 100 * conf + 50 * (1 - conf)
            cf   = min(100, cf)
            pen  = career_penalty.get(total, 1.0)
            if pen < 1.0 and cf > 50:
                cf = 50 + (cf - 50) * pen
        else:
            cf = 20
    else:
        cf = 20
    axes['CF'] = cf

    agari = row['上がり3Fタイム_sec']
    axes['SI'] = max(10, 100 - (agari - 30) * 2) if pd.notna(agari) else 50

    jockey = row['騎手名']
    if pd.notna(jockey) and jockey in jockey_stats:
        axes['JT'] = min(100, jockey_stats[jockey]['win_rate'] * 100)
    else:
        axes['JT'] = 50

    passages = [row.get('通過順1'), row.get('通過順2'),
                row.get('通過順3'), row.get('通過順4')]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    axes['PD'] = max(10, 100 - abs(np.mean(passages) - 7) * 3) if passages else 50

    pop = int(row['人気順'])
    axes['BL'] = max(10, 100 - pop * 5) if pop > 0 else 50

    dist  = int(row['距離'])
    jikan = row['走破時計_sec']
    if dist in distance_stats and pd.notna(jikan):
        ds = distance_stats[dist]
        if ds['std_time'] > 0:
            z = (float(jikan) - ds['avg_time']) / ds['std_time']
            axes['SPD'] = max(10, min(100, 50 - z * 10))
        else:
            axes['SPD'] = 50
    else:
        axes['SPD'] = 50

    odds = float(row['単勝オッズ_num']) if pd.notna(row.get('単勝オッズ_num')) else 0.0
    if 1 <= pop <= 5:
        mk = 100 - pop * 10
    elif 6 <= pop <= 10:
        mk = 50 - (pop - 5) * 5
    else:
        mk = max(10, 30 - (pop - 10))
    if team_type == 'I' and pop > 5:
        mk += (pop - 5) * 2
    elif team_type == 'O' and pop <= 3:
        mk += (4 - pop) * 5
    if odds > 0:
        for lo, hi, mult in odds_mk_table:
            if lo < odds <= hi:
                if mult != 1.0:
                    mk = 50 + (mk - 50) * mult
                break
    axes['MK'] = mk

    W = {'CF': 2.0, 'SI': 2.0, 'SPD': 2.0, 'JT': 2.0,
         'PD': 1.0, 'BL': 0.3, 'MK': 0.3}
    keys = list(axes.keys())
    vals = [axes[k] for k in keys]
    wts  = [W.get(k, 1.0) for k in keys]
    return float(np.average(vals, weights=wts))


def score_race_4teams(rdf):
    teams = ['I', 'O', 'U', 'S']
    team_scores = {t: {} for t in teams}
    for t in teams:
        for idx, row in rdf.iterrows():
            try:
                team_scores[t][idx] = score_horse(row, t)
            except Exception:
                team_scores[t][idx] = 50.0
    return {idx: float(np.mean([team_scores[t][idx] for t in teams]))
            for idx in rdf.index}


def score_to_win_prob(scores_dict, rdf):
    indices   = list(scores_dict.keys())
    score_arr = np.array([scores_dict[i] for i in indices])
    shifted       = score_arr - score_arr.max()
    softmax_probs = np.exp(shifted / TEMPERATURE)
    softmax_probs = softmax_probs / softmax_probs.sum()
    win_caps = []
    for idx in indices:
        horse_name = str(rdf.loc[idx, '馬名']).strip()
        pr = horse_place_rate.get(horse_name, None)
        cap = pr / 3.0 if pr is not None else 1.0
        win_caps.append(cap)
    win_caps = np.array(win_caps)
    capped = np.minimum(softmax_probs, win_caps)
    total  = capped.sum()
    if total < 1e-9:
        capped = softmax_probs
    else:
        capped = capped / total
    return {idx: float(p) for idx, p in zip(indices, capped)}


def estimate_umaren_odds(odds_a, odds_b):
    """馬連オッズ推定式（単勝オッズの積 ÷ 3.5）"""
    return max(1.0, (odds_a * odds_b) / 3.5)


# ============================================================
# バックテスト実行
# ============================================================
print("\n■ バックテスト実行中（検証データ 2024〜2026）...")
race_groups = test_df.groupby('race_key')
total_races = len(race_groups)
print(f"  対象レース数: {total_races}R")

# 結果格納
# A: 現行ルール（◎エッジ+0.06以上 → 単勝）
baseline_bets    = []
# B: 新ルール（◎エッジ未達 & ○以下エッジ+0.06以上 → 馬連◎×○）
new_rule_bets    = []
# C: 拡張ルール（◎エッジ+0.06以上 → 単勝 OR ◎未達&○以上 → 馬連）を合わせた全体
combined_bets    = []

for i, (race_key, rdf) in enumerate(race_groups):
    if i % 100 == 0:
        print(f"  進捗: {i}/{total_races}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3:
        continue
    if valid[valid['確定着順'] == 1].empty:
        continue

    year     = int(race_key.split('_')[0])
    grade_lbl = str(rdf.iloc[0]['grade'])
    dist_val  = int(valid.iloc[0]['距離']) if pd.notna(valid.iloc[0]['距離']) else 0
    venue     = str(valid.iloc[0]['場所']).strip()
    surface   = str(valid.iloc[0].get('芝・ダ', '')).strip()

    scores    = score_race_4teams(valid)
    win_probs = score_to_win_prob(scores, valid)

    # 全馬エッジ計算
    horse_data = []
    for idx, row in valid.iterrows():
        raw_odds = float(row['単勝オッズ_num'])
        if raw_odds <= 0:
            continue
        market_prob = (1.0 / raw_odds) * 0.80
        wp = win_probs.get(idx, 0.0)
        edge = wp - market_prob
        finish_pos = int(row['確定着順'])
        pop = int(row['人気順'])
        horse_data.append({
            'idx':        idx,
            'name':       str(row['馬名']).strip(),
            'score':      scores.get(idx, 50.0),
            'win_prob':   wp,
            'odds':       raw_odds,
            'market_prob': market_prob,
            'edge':       edge,
            'finish_pos': finish_pos,
            'pop':        pop,
        })

    if not horse_data:
        continue

    # スコア順でソート → ◎/○/▲ 割り当て
    sorted_horses = sorted(horse_data, key=lambda x: x['score'], reverse=True)
    if len(sorted_horses) < 2:
        continue

    honmei = sorted_horses[0]   # ◎
    circle = sorted_horses[1:5] # ○〜▲（上位2〜5位）

    # ── ベースライン判定（◎エッジ+0.06 → 単勝） ──
    if honmei['edge'] >= EDGE_THRESHOLD and dist_val < 2200:
        hit = (honmei['finish_pos'] == 1)
        returned = honmei['odds'] * BET_UNIT if hit else 0
        baseline_bets.append({
            'race_key':  race_key,
            'year':      year,
            'grade':     grade_lbl,
            'dist':      dist_val,
            'dist_band': dist_band(dist_val),
            'venue':     venue,
            'horse':     honmei['name'],
            'odds':      honmei['odds'],
            'edge':      honmei['edge'],
            'pop':       honmei['pop'],
            'finish':    honmei['finish_pos'],
            'hit':       hit,
            'invested':  BET_UNIT,
            'returned':  returned,
            'rule':      'baseline_tansho',
        })

    # ── 新ルール判定（◎エッジ未達 & ○以下エッジ+0.06 → 馬連） ──
    if honmei['edge'] < EDGE_THRESHOLD and dist_val < 2200:
        # ○以下で最もエッジが高い馬を探す
        edge_candidates = [h for h in circle if h['edge'] >= EDGE_THRESHOLD]
        if edge_candidates:
            best_circle = max(edge_candidates, key=lambda x: x['edge'])

            # 馬連的中判定：◎と○が1着2着（順不問）
            top2_names = {h['name'] for h in sorted_horses[:len(sorted_horses)]
                          if h['finish_pos'] <= 2}
            hit = (honmei['name'] in top2_names) and (best_circle['name'] in top2_names)

            est_umaren = estimate_umaren_odds(honmei['odds'], best_circle['odds'])
            returned = est_umaren * BET_UNIT if hit else 0

            new_rule_bets.append({
                'race_key':    race_key,
                'year':        year,
                'grade':       grade_lbl,
                'dist':        dist_val,
                'dist_band':   dist_band(dist_val),
                'venue':       venue,
                'honmei':      honmei['name'],
                'honmei_odds': honmei['odds'],
                'honmei_edge': honmei['edge'],
                'honmei_pop':  honmei['pop'],
                'circle':      best_circle['name'],
                'circle_odds': best_circle['odds'],
                'circle_edge': best_circle['edge'],
                'circle_pop':  best_circle['pop'],
                'est_umaren':  est_umaren,
                'hit':         hit,
                'invested':    BET_UNIT,
                'returned':    returned,
                'honmei_fin':  honmei['finish_pos'],
                'circle_fin':  best_circle['finish_pos'],
                'rule':        'circle_edge_umaren',
            })

print(f"\n  ベースライン該当: {len(baseline_bets)}R")
print(f"  新ルール該当:     {len(new_rule_bets)}R")


# ============================================================
# 集計
# ============================================================
def summarize(bets, label):
    if not bets:
        print(f"\n【{label}】--- 該当なし ---")
        return {}
    n     = len(bets)
    hits  = sum(1 for b in bets if b['hit'])
    inv   = sum(b['invested'] for b in bets)
    ret   = sum(b['returned'] for b in bets)
    roi   = ret / inv * 100 if inv > 0 else 0
    wr    = hits / n * 100
    print(f"\n【{label}】")
    print(f"  該当レース数: {n}R  的中: {hits}回  的中率: {wr:.1f}%")
    print(f"  投資: {inv:,}円  払戻: {ret:,.0f}円  回収率: {roi:.1f}%")
    return {'n': n, 'hits': hits, 'win_rate': wr, 'roi': roi, 'inv': inv, 'ret': ret}


b_stat = summarize(baseline_bets, "◎単勝エッジルール（現行・ベースライン）")
n_stat = summarize(new_rule_bets,  "◎未達×○馬連エッジルール（新ルール）")

# グレード別
print("\n■ グレード別（新ルール）")
for g in ['G1', 'G2', 'G3']:
    sub = [b for b in new_rule_bets if b['grade'] == g]
    if sub:
        hits = sum(1 for b in sub if b['hit'])
        inv  = sum(b['invested'] for b in sub)
        ret  = sum(b['returned'] for b in sub)
        roi  = ret / inv * 100 if inv > 0 else 0
        print(f"  {g}: {len(sub)}R  的中{hits}回  ROI={roi:.1f}%")

# 年別（新ルール）
print("\n■ 年別（新ルール）")
year_map = defaultdict(lambda: {'n':0,'hits':0,'inv':0,'ret':0})
for b in new_rule_bets:
    y = b['year']
    year_map[y]['n']    += 1
    year_map[y]['hits'] += int(b['hit'])
    year_map[y]['inv']  += b['invested']
    year_map[y]['ret']  += b['returned']
for y in sorted(year_map):
    d = year_map[y]
    roi = d['ret'] / d['inv'] * 100 if d['inv'] > 0 else 0
    print(f"  {y}年: {d['n']}R  的中{d['hits']}回  ROI={roi:.1f}%")

# 距離帯別（新ルール）
print("\n■ 距離帯別（新ルール）")
dist_map = defaultdict(lambda: {'n':0,'hits':0,'inv':0,'ret':0})
for b in new_rule_bets:
    k = b['dist_band']
    dist_map[k]['n']    += 1
    dist_map[k]['hits'] += int(b['hit'])
    dist_map[k]['inv']  += b['invested']
    dist_map[k]['ret']  += b['returned']
for k, d in dist_map.items():
    roi = d['ret'] / d['inv'] * 100 if d['inv'] > 0 else 0
    print(f"  {k}: {d['n']}R  的中{d['hits']}回  ROI={roi:.1f}%")

# 誤爆パターン分類
print("\n■ 誤爆パターン分類（新ルール・不的中）")
miss = [b for b in new_rule_bets if not b['hit']]
pattern = defaultdict(int)
for b in miss:
    h_fin = b['honmei_fin']
    c_fin = b['circle_fin']
    if h_fin == 1 and c_fin > 2:
        pat = "◎1着だが○が3着以下"
    elif c_fin == 1 and h_fin > 2:
        pat = "○1着だが◎が3着以下"
    elif h_fin <= 2 or c_fin <= 2:
        pat = "片方は2着以内だが組み合わせ違い"
    else:
        pat = "◎も○も3着以下"
    pattern[pat] += 1
total_miss = len(miss)
for pat, cnt in sorted(pattern.items(), key=lambda x: -x[1]):
    pct = cnt / total_miss * 100 if total_miss > 0 else 0
    print(f"  {pat}: {cnt}回 ({pct:.1f}%)")

# ◎人気帯別（新ルール）
print("\n■ ◎人気帯別（新ルール）")
pop_map = {'1〜3番人気':[],'4〜6番人気':[],'7番人気以上':[]}
for b in new_rule_bets:
    p = b['honmei_pop']
    if p <= 3:
        pop_map['1〜3番人気'].append(b)
    elif p <= 6:
        pop_map['4〜6番人気'].append(b)
    else:
        pop_map['7番人気以上'].append(b)
for k, lst in pop_map.items():
    if lst:
        hits = sum(1 for b in lst if b['hit'])
        inv  = sum(b['invested'] for b in lst)
        ret  = sum(b['returned'] for b in lst)
        roi  = ret / inv * 100 if inv > 0 else 0
        print(f"  {k}: {len(lst)}R  的中{hits}回  ROI={roi:.1f}%")

# ◎vs○ エッジ差が大きいケース（参考）
print("\n■ ○エッジ上位5件（参考）")
top5_circle = sorted(new_rule_bets, key=lambda x: x['circle_edge'], reverse=True)[:5]
for b in top5_circle:
    mark = "✅" if b['hit'] else "❌"
    print(f"  {mark} {b['grade']} {b['year']}年 ◎{b['honmei']}({b['honmei_pop']}人) "
          f"○{b['circle']}({b['circle_pop']}人/{b['circle_odds']}倍) "
          f"edge+{b['circle_edge']:.3f} → 推定馬連{b['est_umaren']:.0f}倍 "
          f"◎{b['honmei_fin']}着/○{b['circle_fin']}着")

# ============================================================
# 総合判断
# ============================================================
print("\n" + "="*60)
print("【総合判断】")
if b_stat and n_stat:
    print(f"  現行ルール（◎単勝）   : {b_stat['n']:3d}R  ROI {b_stat['roi']:6.1f}%")
    print(f"  新ルール（○馬連）     : {n_stat['n']:3d}R  ROI {n_stat['roi']:6.1f}%")
    print(f"  合計ベット数         : {b_stat['n'] + n_stat['n']:3d}R")

    if n_stat['roi'] >= 100:
        rec = "★採用推奨（回収率100%超）"
    elif n_stat['roi'] >= 80:
        rec = "△様子見（80〜100%・過学習チェック要）"
    else:
        rec = "✗不採用（回収率80%未満）"
    print(f"\n  推奨: {rec}")
    print("  ※馬連オッズは推定値（単勝オッズ積÷3.5）のため実際と異なる可能性あり")
print("="*60)
