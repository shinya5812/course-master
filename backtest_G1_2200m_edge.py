# -*- coding: utf-8 -*-
"""
backtest_G1_2200m_edge.py
G1 × 2201m以上 × エッジ値別 ベット解禁検証

前回バックテスト結果（output/backtest_2200m_over_2021_2023.csv）から
G1データを抽出し、エッジ値3グループ別に集計。
G1解禁ルールの採否判定を出力する。

採否基準: 以下を全て満たす場合のみ「解禁推奨」
  - サンプル10R以上
  - 単勝回収率110%以上
  - ◎的中率30%以上
"""
import sys
import io
import os
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUT_DIR    = os.path.join(BASE_DIR, 'output')
INPUT_CSV  = os.path.join(OUT_DIR, 'backtest_2200m_over_2021_2023.csv')
OUTPUT_CSV = os.path.join(OUT_DIR, 'backtest_G1_2200m_edge_2021_2023.csv')

ADOPT_MIN_N   = 10
ADOPT_MIN_ROI = 110.0
ADOPT_MIN_WR  = 0.30


def calc_group(df_sub, label):
    n = len(df_sub)
    if n == 0:
        return {'グループ': label, 'R数': 0, '的中率': None, '複勝率': None, '単勝回収率': None, '採否': '判定不可'}
    wins   = df_sub['hit_win'].sum()
    places = df_sub['hit_place'].sum()
    wr     = wins / n
    pr     = places / n
    # 単勝回収率（オッズ不明ゼロを除外）
    valid  = df_sub[df_sub['pred_odds'] > 0]
    roi = (valid['hit_win'] * valid['pred_odds']).sum() / len(valid) * 100 if len(valid) > 0 else 0.0
    return {
        'グループ': label,
        'R数': n,
        '的中率': round(wr * 100, 1),
        '複勝率': round(pr * 100, 1),
        '単勝回収率': round(roi, 1),
        '採否': None,
    }


# ============================================================
# 1. データ読み込み・G1フィルタ
# ============================================================
print("■ データ読み込み")
df = pd.read_csv(INPUT_CSV, encoding='utf-8-sig')
g1 = df[(df['grade'] == 'G1')].copy()
print(f"  全体: {len(df)}R → G1: {len(g1)}R")

# ============================================================
# 2. Step 1: レース一覧表示
# ============================================================
print("\n■ Step 1: G1×2201m以上 レース一覧 (2021〜2023)")
print("-" * 100)
for _, row in g1.iterrows():
    e = f'{row["edge"]:+.4f}' if pd.notna(row['edge']) else '  N/A '
    print(f"  {row['race_date']}  {row['race_name']:16s}  {row['distance']}m  "
          f"◎{row['pred_horse']:16s}  {int(row['pred_pop'])}人気  "
          f"オッズ{row['pred_odds']:.1f}倍  エッジ{e}  "
          f"{'的中' if row['hit_win'] else '外れ'}({int(row['actual_finish'])}着)")
print(f"\n  合計: {len(g1)}R")

# ============================================================
# 3. Step 2-3: エッジ3グループ集計
# ============================================================
ga = g1[g1['edge'] >= 0.06].copy()
gb = g1[(g1['edge'] >= 0) & (g1['edge'] < 0.06)].copy()
gc = g1[g1['edge'] < 0].copy()
# エッジ不明（NaN）は除外済みと仮定

print("\n■ Step 2-3: エッジ値グループ別集計")
print("=" * 70)

rows_summary = []
for df_sub, label in [(ga, 'A: +0.06以上（解禁候補）'),
                       (gb, 'B: 0〜+0.06（様子見）'),
                       (gc, 'C: マイナス（見送り）')]:
    r = calc_group(df_sub, label)
    rows_summary.append(r)

for r in rows_summary:
    print(f"\n  グループ {r['グループ']}")
    print(f"    R数      : {r['R数']}")
    print(f"    的中率    : {r['的中率']}%")
    print(f"    複勝率    : {r['複勝率']}%")
    print(f"    単勝回収率: {r['単勝回収率']}%")

# ============================================================
# 4. Step 6: 採否判定（グループA対象）
# ============================================================
print("\n" + "=" * 70)
print("■ Step 6: 採否判定（G1×2201m以上・エッジ+0.06以上）")
print("=" * 70)

ra = rows_summary[0]
n_ok  = (ra['R数']     >= ADOPT_MIN_N)
roi_ok = (ra['単勝回収率'] >= ADOPT_MIN_ROI)
wr_ok  = (ra['的中率']   >= ADOPT_MIN_WR * 100)

print(f"\n  採否基準:")
print(f"    ① サンプル10R以上  : {ra['R数']:3d}R  {'✓' if n_ok  else '✗ 未達'}")
print(f"    ② 単勝回収率110%以上: {ra['単勝回収率']:6.1f}%  {'✓' if roi_ok else '✗ 未達'}")
print(f"    ③ ◎的中率30%以上   : {ra['的中率']:5.1f}%  {'✓' if wr_ok  else '✗ 未達'}")

if n_ok and roi_ok and wr_ok:
    verdict = "✅ 解禁推奨"
    verdict_reason = "全3条件クリア"
else:
    failed = []
    if not n_ok:   failed.append(f"サンプル不足({ra['R数']}R<10R)")
    if not roi_ok: failed.append(f"ROI不足({ra['単勝回収率']}%<110%)")
    if not wr_ok:  failed.append(f"的中率不足({ra['的中率']}%<30%)")
    verdict = "❌ 解禁否決"
    verdict_reason = "・".join(failed)

print(f"\n  【採否判定】{verdict}")
print(f"  理由: {verdict_reason}")

# ============================================================
# 5. Step 4: G1解禁 vs 現行ルール比較
# ============================================================
print("\n" + "=" * 70)
print("■ Step 4: G1解禁 vs 現行ルール（全保留）比較シミュレーション")
print("=" * 70)

# 現行: G1/G2 2201m以上は全保留 → ベット0
# 提案: G1 エッジ+0.06以上のみ解禁

total_g1 = len(g1)
g1_edge_ok = ga

# 現行ルール
current_cost   = 0
current_return = 0

# 提案ルール（G1×エッジ+0.06以上のみ）
propose_cost   = len(g1_edge_ok) * 100
valid_prop = g1_edge_ok[g1_edge_ok['pred_odds'] > 0]
propose_return = int((valid_prop['hit_win'] * valid_prop['pred_odds'] * 100).sum())
propose_pnl    = propose_return - propose_cost
propose_roi    = propose_return / propose_cost * 100 if propose_cost > 0 else 0

print(f"\n  【現行ルール（全保留）】")
print(f"    投資: {current_cost}円  払戻: {current_return}円  収支: 0円")

print(f"\n  【提案ルール（G1×エッジ+0.06以上のみ解禁）】")
print(f"    対象: {len(g1_edge_ok)}R")
print(f"    投資: {propose_cost}円  払戻: {propose_return}円  収支: {propose_pnl:+d}円")
print(f"    回収率: {propose_roi:.1f}%")
print(f"    {'→ 現行より優位' if propose_pnl > 0 else '→ 現行（全保留）より劣位'}")

# ============================================================
# 6. Step 5: CSV保存
# ============================================================
# G1データに採否フラグを付けて保存
g1_out = g1.copy()
g1_out['edge_group'] = g1_out['edge'].apply(
    lambda e: 'A:+0.06以上' if pd.notna(e) and e >= 0.06
    else ('B:0〜+0.06' if pd.notna(e) and e >= 0 else 'C:マイナス')
)
g1_out['adopt_target'] = g1_out['edge'] >= 0.06
g1_out['verdict'] = verdict

g1_out.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
print(f"\n■ CSV保存: {OUTPUT_CSV}  ({len(g1_out)}件)")

print("\n" + "=" * 70)
print("完了")
print("=" * 70)

# ============================================================
# 7. サマリーJSON（CLAUDE.md追記用）
# ============================================================
print("\n【CLAUDE.md追記用サマリー】")
print(f"G1×2201m以上 エッジ別バックテスト（2021〜2023）: {total_g1}R")
print(f"  グループA(+0.06以上): {ra['R数']}R / 的中{ra['的中率']}% / 複勝{ra['複勝率']}% / ROI{ra['単勝回収率']}%")
print(f"  採否判定: {verdict}")
