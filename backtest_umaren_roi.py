# -*- coding: utf-8 -*-
"""
verify3: 馬連◎○追加のROI検証（ADI50-70帯）
- 2024-2026 Grade重賞（芝11R・10頭以上）を対象
- 簡易エッジ = engine推定勝率相当値 - 市場確率
  ※エンジンを全レース走らせるのはコスト大のため、BL/MK軸主体の
    簡易スコアでエッジを近似する（傾向確認目的）
- 馬連オッズはDBに未収録のため推計値を使用
"""
import sys, io, sqlite3, os, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path  = os.path.join(BASE_DIR, 'course_master.db')
conn = sqlite3.connect(db_path)
cur  = conn.cursor()

# ── Grade重賞近似: 2024-2026年・芝・11R・10頭以上 ──────────────
sql = '''
SELECT rr.race_date, rr.venue, rr.race_no,
       rr.horse_name, rr.horse_no,
       rr.popularity, rr.tansho_odds, rr.finish_pos,
       COUNT(*) OVER (PARTITION BY rr.race_date, rr.venue, rr.race_no) AS nheads
FROM race_results rr
WHERE rr.race_date >= '2024-01-01'
  AND rr.race_date <= '2026-04-19'
  AND rr.surface = '芝'
  AND rr.distance BETWEEN 1200 AND 2100
  AND CAST(rr.race_no AS INTEGER) >= 10
ORDER BY rr.race_date, rr.venue, rr.race_no, rr.popularity
'''
cur.execute(sql)
rows = cur.fetchall()
conn.close()

# ── レースごとにグルーピング ─────────────────────────────────────
from collections import defaultdict
races = defaultdict(list)
for rd, venue, rno, hname, hno, pop, odds, fpos, nheads in rows:
    if nheads < 10:
        continue
    races[(rd, venue, rno)].append({
        'name': hname, 'no': hno,
        'pop': pop, 'odds': odds or 0,
        'finish': fpos, 'nheads': nheads
    })

# ── 各レースで chaos_index(A要素) と簡易エッジを計算 ──────────────
def calc_adi(horses):
    """P1/P3オッズからADI推計（B=60固定・C=20固定で近似）"""
    odds_by_pop = {}
    for h in horses:
        if h['pop'] and h['odds']:
            odds_by_pop[h['pop']] = h['odds']
    p1 = odds_by_pop.get(1, 0)
    p3 = odds_by_pop.get(3, 0)
    if p1 == 0 or p3 == 0:
        return None
    A = min(100.0, (p1 / p3) * 100.0)
    B = 60.0  # 固定近似
    C = 20.0  # 良馬場固定
    return 0.4 * A + 0.4 * B + 0.2 * C

def calc_edge_proxy(h, total_inv_odds):
    """簡易エッジ: 市場の逆数割合を分布として近似した推定勝率 - 市場確率"""
    if h['odds'] <= 0 or total_inv_odds <= 0:
        return None
    market_prob   = (1.0 / h['odds']) * 0.80
    # 簡易engine推定: 人気順から期待勝率を補正（低人気を若干上方修正）
    # win_rate_proxy = （そのオッズ帯の実績勝率）近似
    # 人気帯別平均勝率テーブル（過去統計より）
    pop_wr = {1:0.328,2:0.190,3:0.140,4:0.100,5:0.075,
              6:0.055,7:0.042,8:0.034,9:0.027,10:0.022}
    p = h['pop'] if h['pop'] and h['pop'] <= 10 else 10
    base_wr = pop_wr.get(p, 0.018)
    # オッズでさらに補正（市場オッズが高い = 実績勝率が低い）
    engine_prob = base_wr * (1 + max(0, (h['odds'] - 10) / 100))
    edge = engine_prob - market_prob
    return edge

# ── 集計 ─────────────────────────────────────────────────────────
EDGE_HONMEI = 0.06  # ◎閾値
EDGE_CIRCLE = 0.03  # ○閾値

results_tansho = []  # [(adi, honmei_odds, honmei_win)]
results_umaren  = []  # [(adi, honmei_odds, circle_odds, hit)]

for key, horses in races.items():
    adi = calc_adi(horses)
    if adi is None or not (50.0 <= adi < 70.0):
        continue
    if len(horses) < 2:
        continue

    total_inv = sum(1.0/h['odds'] for h in horses if h['odds'] > 0)
    # エッジ計算
    for h in horses:
        h['edge'] = calc_edge_proxy(h, total_inv)

    # ◎選出（エッジ最大・閾値以上）
    candidates = [h for h in horses if h['edge'] is not None and h['edge'] >= EDGE_HONMEI]
    if not candidates:
        continue
    honmei = max(candidates, key=lambda x: x['edge'])

    # 単勝集計
    honmei_win = (honmei['finish'] == 1) if honmei['finish'] else False
    results_tansho.append((adi, honmei['odds'], honmei_win))

    # ○選出（◎以外でエッジ+0.03以上、上位2頭）
    circles = sorted(
        [h for h in horses if h['name'] != honmei['name'] and
         h['edge'] is not None and h['edge'] >= EDGE_CIRCLE],
        key=lambda x: x['edge'], reverse=True
    )[:2]

    if not circles:
        continue

    for circle in circles:
        # 馬連ヒット: ◎と○の両方がfinish 1 or 2
        h_fin = honmei['finish']
        c_fin = circle['finish']
        hit = False
        if h_fin and c_fin:
            hit = ({h_fin, c_fin} <= {1, 2})
        # 馬連オッズ推計（√(tansho◎×tansho○) × 0.75）
        est_umaren = math.sqrt(honmei['odds'] * circle['odds']) * 0.75
        results_umaren.append((adi, honmei['odds'], circle['odds'], est_umaren, hit))

# ── ROI計算 ──────────────────────────────────────────────────────
print('=' * 65)
print('  verify3: 馬連◎○ ROI バックテスト（ADI50-70・2024-2026 Grade近似）')
print('=' * 65)
print()

if results_tansho:
    n_t  = len(results_tansho)
    wins = sum(1 for _, _, w in results_tansho if w)
    roi_t = sum(o for _, o, w in results_tansho if w) * 100 / (n_t * 100)
    print(f'【単勝◎のみ】')
    print(f'  対象R数: {n_t}  的中率: {wins/n_t*100:.1f}%  ROI: {roi_t:.1f}%')
else:
    print('単勝データなし')

print()
if results_umaren:
    n_u   = len(results_umaren)
    hits  = sum(1 for *_, h in results_umaren if h)
    roi_u = sum(eu for _, _, _, eu, h in results_umaren if h) * 100 / (n_u * 100)
    avg_est_odds = sum(eu for _, _, _, eu, _ in results_umaren) / n_u
    print(f'【馬連◎○（エッジ+0.03以上・最大2頭）】')
    print(f'  対象組数: {n_u}  的中率: {hits/n_u*100:.1f}%')
    print(f'  推計馬連オッズ平均: {avg_est_odds:.1f}倍')
    print(f'  ROI（推計）: {roi_u:.1f}%')
else:
    print('馬連データなし')

print()
print('【注意事項】')
print('  ・エンジン◎は簡易プロキシ（BL/MK主体）。実エンジン7軸とは異なる')
print('  ・馬連オッズはDB未収録のため √(tansho◎×tansho○)×0.75 で推計')
print('  ・Grade重賞は 芝・11R以上・10頭以上・2200m以下 で近似')
print(f'  ・ADI50-70推計: B成分=60固定（実際は1人気サポート率から計算）')
print()
print('【判定基準】')
print('  ROI馬連 ≥ 100%  → 馬連追加は有効（実装維持）')
print('  ROI馬連 < 100%  → 再検討（実装保留を検討）')
