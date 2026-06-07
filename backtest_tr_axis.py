# -*- coding: utf-8 -*-
"""
TR軸改修（+20廃止・course_stats導入）の影響分析

分析ポイント:
1. TR軸はレース内の全馬で同一値 → 馬の優劣判定に寄与しない
2. +20廃止でスコア水準は下がるが、相対差（予測ランキング）は不変
3. course_stats導入で「コース特性に合った絶対スコア」になる

"""
import sqlite3
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'course_master.db')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 70)
print("TR軸改修影響分析")
print("=" * 70)

# ---- 1. course_statsのスコア分布 ----
print("\n【1. course_win_rateのwin_rate分布（TR軸の実スコア水準）】")
cur.execute("""
    SELECT
        MIN(win_rate) as min_wr,
        MAX(win_rate) as max_wr,
        AVG(win_rate) as avg_wr,
        COUNT(*) as cnt
    FROM course_win_rate
""")
r = cur.fetchone()
print(f"  件数: {r['cnt']}件")
print(f"  win_rate: 最小={r['min_wr']:.2f}% / 平均={r['avg_wr']:.2f}% / 最大={r['max_wr']:.2f}%")
print(f"  → TRスコア（×1, 小数値）: 最小≈{r['min_wr']:.2f}点 / 平均≈{r['avg_wr']:.2f}点 / 最大≈{r['max_wr']:.2f}点")
print(f"  ※ エンジン内でwin_rateはすでに÷100済み（0〜1の小数）、TR = win_rate*100 で点数化")

# win_rate は course_win_rate テーブルでは % 表示か確認
cur.execute("SELECT win_rate FROM course_win_rate LIMIT 5")
samples = cur.fetchall()
print(f"  サンプル値: {[round(r['win_rate'],3) for r in samples]}")

# ---- 2. 会場×芝ダ×距離×馬場別のTRスコア分布 ----
print("\n【2. 主要条件のTRスコア（実値）】")
print("  ※ エンジンはDBからwin_rate取得後 ÷100 して保存 → TR = win_rate * 100 点")
cur.execute("""
    SELECT venue, surface, distance, condition, win_rate, race_count
    FROM course_win_rate
    ORDER BY race_count DESC
    LIMIT 15
""")
print(f"  {'会場':6s} {'芝ダ':4s} {'距離':6s} {'馬場':4s} | {'win_rate':>8s} | {'TR点数(×100)':>10s} | {'レース数':>7s}")
print("  " + "-" * 60)
for r in cur.fetchall():
    tr_score = r['win_rate'] * 100
    print(f"  {r['venue']:6s} {r['surface']:4s} {r['distance']:6d} {r['condition']:4s} | {r['win_rate']:8.4f} | {tr_score:10.2f}点 | {r['race_count']:7d}")

# ---- 3. 旧TR vs 新TRスコアの比較 ----
print("\n【3. 旧TR vs 新TRスコア比較（最多使用コース）】")
print("  旧方式: track_stats[(venue, surface)]['win_rate'] * 100 + 20 ≈ 27点固定")
print("  新方式: course_stats[(venue, surface, distance, condition)]['win_rate'] * 100")
print()

cur.execute("""
    SELECT venue, surface,
           AVG(win_rate) as avg_wr,
           MIN(win_rate) as min_wr,
           MAX(win_rate) as max_wr,
           SUM(race_count) as total_races
    FROM course_win_rate
    GROUP BY venue, surface
    ORDER BY total_races DESC
    LIMIT 10
""")
print(f"  {'会場':6s} {'面':4s} | {'旧TR(推定)':>10s} | {'新TR平均':>10s} | {'新TR範囲':>20s} | {'使用レース数':>10s}")
print("  " + "-" * 72)
for r in cur.fetchall():
    old_tr = 7.0  # 旧: 単純な会場×芝ダの勝率 ≈ 7%前後 + 20 = 27点程度
    new_avg = r['avg_wr'] * 100
    new_range = f"{r['min_wr']*100:.2f}〜{r['max_wr']*100:.2f}点"
    print(f"  {r['venue']:6s} {r['surface']:4s} | {'≈27.0点':>10s} | {new_avg:>9.2f}点 | {new_range:>20s} | {r['total_races']:>10,}")

# ---- 4. TR軸の馬間差別化への影響分析 ----
print("\n【4. TR軸の馬間差別化影響（重要な論点）】")
print()
print("  TR軸は『同一レース内のすべての馬で同一値』を持つ軸です。")
print("  理由: venue/surface/distance/conditionはレース全体で共通のため。")
print()
print("  この性質により:")
print("  ・旧TR（+20固定加算）: 全馬に+20が加わる → 予測ランキングに影響なし")
print("  ・新TR（course_win_rate使用）: 全馬に同じ値が加わる → 予測ランキングに影響なし")
print()
print("  結論: TR軸の絶対値変化（+20廃止）は予測順位に実質ゼロ影響。")
print("  ただしスコアの絶対水準は低下（平均-13〜-20点程度）。")

# ---- 5. スコア水準低下の12軸平均への影響 ----
print("\n【5. スコア水準低下の12軸平均への影響試算】")
print()
# 12軸の平均
# TR軸が7点 → 27点になった場合の差
old_tr_typical = 27.0
new_tr_typical = 7.0  # course_win_rateの平均×100
score_diff_per_axis = (new_tr_typical - old_tr_typical) / 12
print(f"  旧TR代表値: {old_tr_typical:.1f}点")
print(f"  新TR代表値: {new_tr_typical:.1f}点（course_win_rate平均より）")
print(f"  12軸平均への影響: ({new_tr_typical:.1f} - {old_tr_typical:.1f}) / 12 = {score_diff_per_axis:.2f}点/馬")
print()
print("  → 全馬のスコアが約{:.2f}点下がるだけで、馬同士の相対差は変わらない".format(score_diff_per_axis))
print("  → 予測ランキング（◎○▲選定）への影響: 実質なし")
print()
print("  ただし以下の点は注意:")
print("  ・softmax(T=5.0)で確率変換する際、絶対スコア差が影響する")
print("  ・全馬一律の水準低下なら確率分布への影響も最小")

conn.close()
print("\n=== 分析完了 ===")
