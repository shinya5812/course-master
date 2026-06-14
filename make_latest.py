# -*- coding: utf-8 -*-
"""
make_latest.py - output/latest_data.json を生成するスクリプト

predictions_*.json から以下のセクションを含む JSON を生成する:
  - 後方互換フィールド（Hero コンポーネント用・12フィールド）
  - races[]        : 直近14日の重賞予測一覧
  - stats{}        : 累計◎的中率（actual_result 記録済み R ベース）
  - edge_ranking[] : 直近レースのエッジ上位 TOP_N 頭
"""

import glob, json, os, sys, re
from datetime import date, datetime, timedelta

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE    = os.path.dirname(os.path.abspath(__file__))
TOP_N   = 5   # edge_ranking の件数
WINDOW  = 14  # 直近何日を "今週/今月" とするか


# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────
def grade_from_name(race_name: str) -> str:
    if 'G1' in race_name or 'GⅠ' in race_name:
        return 'G1'
    if 'G2' in race_name or 'GⅡ' in race_name:
        return 'G2'
    if 'G3' in race_name or 'GⅢ' in race_name:
        return 'G3'
    return '重賞'


def derive_verdict(honmei: dict) -> str:
    """strategy.verdict がない旧フォーマット向けにエッジから判定ラベルを再導出する。"""
    edge = honmei.get('edge', 0)
    is_anaba = honmei.get('popularity', 99) >= 4
    edge_ok  = edge >= 0.06
    if is_anaba and edge_ok:
        return '🟢🟢 強推奨'
    if edge_ok:
        return '🟢 推奨'
    if edge > 0:
        return '🟡 様子見'
    return '🔴 見送り'


# ──────────────────────────────────────────────
# ファイル読み込み・正規化
# ──────────────────────────────────────────────
def load_all() -> list[dict]:
    """
    predictions_*.json を全件読み込み、正規化した辞書リストを返す。
    旧フォーマット（generated/race/top_horses）と新フォーマット（date/race_name/prediction）両対応。
    """
    files = sorted(glob.glob(os.path.join(BASE, 'predictions_*.json')))
    results = []
    for f in files:
        try:
            with open(f, encoding='utf-8') as fh:
                raw = json.load(fh)
            raw['_src'] = os.path.basename(f)
            results.append(normalize(raw))
        except Exception as e:
            print(f'[WARN] {f}: {e}', file=sys.stderr)
    return results


def normalize(raw: dict) -> dict:
    """新旧フォーマットの差異を吸収し、共通スキーマの辞書を返す。"""
    is_new = 'prediction' in raw and isinstance(raw['prediction'].get('◎'), dict)

    # ── レース基本情報 ──
    race_name  = raw.get('race_name') or raw.get('race', '')
    race_date  = raw.get('race_date') or raw.get('date') or raw.get('generated', '')
    venue      = raw.get('venue', '')
    surface    = raw.get('surface', '')
    distance   = raw.get('distance', 0)
    track_cond = raw.get('track_cond', '')
    heads      = raw.get('heads') or raw.get('n_horses', 0)
    adi        = raw.get('chaos_index', 0)
    adi_label  = raw.get('chaos_label', '')

    # ── ◎ 情報 ──
    if is_new:
        honmei_dict = raw['prediction']['◎']
        renpuku     = raw['prediction'].get('○', [])
        santen      = raw['prediction'].get('▲', [])
    else:
        # 旧フォーマット: top_horses[0] が ◎
        top = raw.get('top_horses', [])
        honmei_horse = next((h for h in top if h.get('mark') == '◎'), top[0] if top else {})
        honmei_dict = {
            'horse_no':   honmei_horse.get('horse_no', 0),
            'horse_name': honmei_horse.get('name', raw.get('honmei', '')),
            'popularity': honmei_horse.get('popularity') or 0,
            'odds':       honmei_horse.get('odds') or 0,
            'edge':       honmei_horse.get('edge', raw.get('honmei_edge', 0)),
        }
        renpuku = [
            {'horse_no': h.get('horse_no', 0), 'horse_name': h.get('name', ''),
             'popularity': h.get('popularity') or 0, 'odds': h.get('odds') or 0,
             'edge': h.get('edge', 0)}
            for h in top if h.get('mark') == '○'
        ]
        santen = [
            {'horse_no': h.get('horse_no', 0), 'horse_name': h.get('name', ''),
             'popularity': h.get('popularity') or 0, 'odds': h.get('odds') or 0,
             'edge': h.get('edge', 0)}
            for h in top if h.get('mark') == '▲'
        ]

    # ── 戦略・判定 ──
    strategy = raw.get('strategy', {})
    verdict       = strategy.get('verdict') or derive_verdict(honmei_dict)
    verdict_detail = strategy.get('verdict_detail', raw.get('honmei_judgment', ''))
    anaba_flag    = strategy.get('anaba_apply', False)

    # ── 実績 ──
    actual = raw.get('actual_result')

    return {
        'race_name':     race_name,
        'race_date':     race_date,
        'venue':         venue,
        'surface':       surface,
        'distance':      distance,
        'grade':         grade_from_name(race_name),
        'heads':         heads,
        'track_cond':    track_cond,
        'adi':           adi,
        'adi_label':     adi_label,
        'anaba_flag':    anaba_flag,
        'verdict':       verdict,
        'verdict_detail': verdict_detail,
        'prediction': {
            'honmei':   honmei_dict,
            'renpuku':  renpuku,
            'santen':   santen,
        },
        'actual_result': actual,
        '_src':          raw.get('_src', ''),
        '_is_new_fmt':   is_new,
    }


# ──────────────────────────────────────────────
# races[] ： 直近 WINDOW 日の予測（重複排除）
# ──────────────────────────────────────────────
def build_races(all_preds: list[dict]) -> list[dict]:
    """
    直近 WINDOW 日以内の race_date を持つ予測を返す。
    同一 race_name が複数ある場合は actual_result を持つもの優先、
    次に race_date が新しいものを選択。
    """
    if not all_preds:
        return []

    latest_date = max(
        (p['race_date'] for p in all_preds if p['race_date']),
        default=str(date.today())
    )
    try:
        cutoff = datetime.strptime(latest_date, '%Y-%m-%d').date() - timedelta(days=WINDOW)
    except ValueError:
        cutoff = date.min

    in_window = [p for p in all_preds if p['race_date'] >= str(cutoff)]

    # 重複排除: race_name 単位で最良版を選択
    best: dict[str, dict] = {}
    for p in in_window:
        key = p['race_name']
        if key not in best:
            best[key] = p
        else:
            prev = best[key]
            # actual_result ありを優先
            if p['actual_result'] is not None and prev['actual_result'] is None:
                best[key] = p
            # 同じ actual_result 状況なら race_date が新しい方
            elif (p['actual_result'] is None) == (prev['actual_result'] is None):
                if p['race_date'] >= prev['race_date']:
                    best[key] = p

    races = sorted(best.values(), key=lambda p: p['race_date'])

    # 出力フィールドだけに絞り込む（_src/_is_new_fmt は除去）
    return [_strip_internal(r) for r in races]


def _strip_internal(p: dict) -> dict:
    return {k: v for k, v in p.items() if not k.startswith('_')}


# ──────────────────────────────────────────────
# stats{} ： actual_result 記録済み R から累計集計
# ──────────────────────────────────────────────
def build_stats(all_preds: list[dict]) -> dict:
    total, wins, top3 = 0, 0, 0
    invested, returned_total = 0, 0

    for p in all_preds:
        ar = p.get('actual_result')
        if not ar:
            continue
        hf = ar.get('honmei_finish')
        if hf is None:
            continue
        total += 1
        if hf == 1:
            wins += 1
        if hf <= 3:
            top3 += 1

        # 単勝回収率 (hypothetical 100円ベース)
        pnl = ar.get('pnl', {})
        invested       += pnl.get('invested', 0)
        returned_total += pnl.get('returned', 0)

    # 公開開始日: 最古 race_date
    dates = [p['race_date'] for p in all_preds if p['race_date']]
    start = min(dates) if dates else ''

    roi = round(returned_total / invested * 100, 1) if invested > 0 else None

    return {
        'total_races':       total,
        'honmei_wins':       wins,
        'honmei_win_rate':   round(wins / total, 3) if total > 0 else 0.0,
        'honmei_place_rate': round(top3 / total, 3) if total > 0 else 0.0,
        'tansho_roi':        roi,
        'public_start_date': start,
        'last_updated':      str(date.today()),
        'note':              f'◎的中 {wins}/{total}R（実績記録済み）',
    }


# ──────────────────────────────────────────────
# edge_ranking[] ： 直近 races のエッジ上位 TOP_N 頭
# ──────────────────────────────────────────────
def build_edge_ranking(races: list[dict]) -> list[dict]:
    """
    races[] の全馬（◎○▲）からエッジ > 0 の馬をランキング化して TOP_N 件を返す。
    est_win_prob / mkt_win_prob は市場オッズから逆算。
    """
    horses = []
    for race in races:
        race_name = race['race_name']
        race_date = race['race_date']
        pred = race.get('prediction', {})

        entries: list[tuple[str, dict]] = []
        if pred.get('honmei'):
            entries.append(('◎', pred['honmei']))
        for h in pred.get('renpuku', []):
            entries.append(('○', h))
        for h in pred.get('santen', []):
            entries.append(('▲', h))

        for mark, h in entries:
            edge = h.get('edge', 0)
            if edge <= 0:
                continue
            odds = h.get('odds') or 0
            mkt  = round(1 / odds, 4) if odds > 0 else None
            est  = round(mkt + edge, 4) if mkt is not None else None

            horses.append({
                'horse_no':    h.get('horse_no', 0),
                'horse_name':  h.get('horse_name', ''),
                'race_name':   race_name,
                'race_date':   race_date,
                'mark':        mark,
                'popularity':  h.get('popularity', 0),
                'odds':        odds,
                'edge':        edge,
                'est_win_prob': f'{est * 100:.1f}%' if est is not None else '-',
                'mkt_win_prob': f'{mkt * 100:.1f}%' if mkt is not None else '-',
            })

    horses.sort(key=lambda h: h['edge'], reverse=True)
    for i, h in enumerate(horses[:TOP_N], 1):
        h['rank'] = i
    return horses[:TOP_N]


# ──────────────────────────────────────────────
# メイン
# ──────────────────────────────────────────────
def main():
    all_preds = load_all()
    if not all_preds:
        print('predictions_*.json not found', file=sys.stderr)
        sys.exit(1)

    # 新フォーマットのみを対象に最新を選ぶ（後方互換フィールド用）
    new_fmt = [p for p in all_preds if p['_is_new_fmt']]
    if not new_fmt:
        # 新フォーマットがなければ全体から最新
        new_fmt = all_preds
    latest = max(new_fmt, key=lambda p: (p['race_date'], p['_src']))

    honmei  = latest['prediction']['honmei']
    edge    = honmei.get('edge', 0)
    verdict = latest['verdict']

    races        = build_races(all_preds)
    stats        = build_stats(all_preds)
    edge_ranking = build_edge_ranking(races)

    output = {
        # ── 後方互換フィールド（Hero コンポーネント用）──
        'race_name':  latest['race_name'],
        'race_date':  latest['race_date'],
        'venue':      latest['venue'],
        'surface':    latest['surface'],
        'distance':   latest['distance'],
        'horse_name': honmei.get('horse_name', ''),
        'popularity': honmei.get('popularity', 0),
        'odds':       honmei.get('odds', 0),
        'edge':       edge,
        'verdict':    verdict,
        'adi':        latest['adi'],
        'adi_label':  latest['adi_label'],
        # ── 新規セクション ──
        'races':        races,
        'stats':        stats,
        'edge_ranking': edge_ranking,
    }

    os.makedirs(os.path.join(BASE, 'output'), exist_ok=True)
    out_path = os.path.join(BASE, 'output', 'latest_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'latest_data.json 生成完了')
    print(f'  後方互換: {output["race_name"]} ◎{output["horse_name"]} edge={edge:+.3f} {verdict}')
    print(f'  races[]:  {len(races)}件（直近{WINDOW}日）')
    print(f'  stats:    ◎的中率 {stats["honmei_win_rate"]:.1%} / 検証{stats["total_races"]}R')
    print(f'  edge_ranking[]: {len(edge_ranking)}件')


if __name__ == '__main__':
    main()
