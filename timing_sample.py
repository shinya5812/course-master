# -*- coding: utf-8 -*-
"""
処理時間見積もりスクリプト
血統分類スコア＋回収率の再計算処理を100件サンプル実行し、
196,000件全体の推定所要時間を算出する。
"""
import sqlite3
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur  = conn.cursor()

# =====================================================================
# 事前情報: レース件数・JOIN可能件数の確認
# =====================================================================
print("=" * 60)
print("【事前情報】")

cur.execute("SELECT COUNT(*) FROM race_results")
total_rr = cur.fetchone()[0]
print(f"  race_results 総件数         : {total_rr:>10,} 件")

cur.execute("""
    SELECT COUNT(*) FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
""")
joined = cur.fetchone()[0]
print(f"  blood_category JOIN可能件数  : {joined:>10,} 件")

cur.execute("""
    SELECT COUNT(*) FROM race_results
    WHERE tansho_odds > 0
""")
with_odds = cur.fetchone()[0]
print(f"  単勝オッズあり件数           : {with_odds:>10,} 件")

TARGET = 196000
print(f"  想定処理対象                 : {TARGET:>10,} 件")
print()

# =====================================================================
# 計測1: SQLバッチ処理（一括集計クエリ）
# =====================================================================
print("=" * 60)
print("【計測1】SQLバッチ処理（一括集計クエリ）")
print("  → 全件を一度にSQLで集計する方式")

# 100件制限版クエリ（LIMITで打ち切り）
t0 = time.perf_counter()
cur.execute("""
    SELECT
        rr.venue,
        rr.surface,
        rr.distance,
        rr.track_cond,
        rr.horse_name,
        rr.sire_name,
        bc.category AS sire_cat,
        rr.finish_pos,
        rr.popularity,
        rr.tansho_odds,
        CASE WHEN rr.finish_pos = 1 THEN rr.tansho_odds ELSE 0 END AS win_return
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.tansho_odds > 0
    LIMIT 100
""")
rows_100 = cur.fetchall()
t1 = time.perf_counter()

time_100_sql = t1 - t0
print(f"  100件取得時間 : {time_100_sql*1000:.2f} ms")
print(f"  1件あたり     : {time_100_sql/100*1000:.4f} ms")

# 全件クエリ（全体の推定）
t0 = time.perf_counter()
cur.execute("""
    SELECT COUNT(*),
           SUM(CASE WHEN rr.finish_pos = 1 THEN 1 ELSE 0 END),
           SUM(CASE WHEN rr.finish_pos = 1 THEN rr.tansho_odds ELSE 0 END)
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.tansho_odds > 0
""")
result = cur.fetchone()
t1 = time.perf_counter()
time_full_sql = t1 - t0
print(f"\n  ▶ 全件一括集計（{result[0]:,}件）実測: {time_full_sql:.3f} 秒")
print(f"    → 的中数: {result[1]:,} / 回収率: {(result[2] or 0)*100/result[0]:.1f}%")

# =====================================================================
# 計測2: Python行単位処理（100件ループ）
# =====================================================================
print()
print("=" * 60)
print("【計測2】Python行単位処理（100件ループ）")
print("  → 1件ずつPythonで処理する方式（将来の個別スコア付与を想定）")

# blood_category を辞書化（ルックアップ高速化）
cur.execute("SELECT sire_name, category FROM blood_category")
bc_map = {r['sire_name']: r['category'] for r in cur.fetchall()}

# course_win_rate を辞書化
cur.execute("SELECT venue, surface, distance, condition, win_rate FROM course_win_rate")
cwr_map = {}
for r in cur.fetchall():
    cwr_map[(r['venue'], r['surface'], r['distance'], r['condition'])] = r['win_rate']

# サンプル100件取得（ランダム）
cur.execute("""
    SELECT rr.venue, rr.surface, rr.distance, rr.track_cond,
           rr.horse_name, rr.sire_name, rr.finish_pos,
           rr.popularity, rr.tansho_odds
    FROM race_results rr
    WHERE rr.tansho_odds > 0 AND rr.sire_name IS NOT NULL
    ORDER BY RANDOM()
    LIMIT 100
""")
sample = cur.fetchall()

t0 = time.perf_counter()

results = []
for row in sample:
    # 血統カテゴリ参照
    sire_cat = bc_map.get(row['sire_name'], '未分類')

    # コース勝率参照
    cwr_key  = (row['venue'], row['surface'], row['distance'], row['track_cond'])
    cwr      = cwr_map.get(cwr_key, None)

    # 血統スコア計算（カテゴリ×コース一致ボーナス）
    cat_score = {'マイラー系': 60, '速力系': 55, 'スタミナ系': 50, '未分類': 45}.get(sire_cat, 45)

    # コース適性補正
    if cwr is not None:
        course_bonus = (cwr - 0.08) * 100   # 平均8%を基準にした乖離
    else:
        course_bonus = 0.0

    blood_score = cat_score + course_bonus

    # 回収率計算
    win_flag   = (row['finish_pos'] == 1)
    win_return = row['tansho_odds'] if win_flag else 0.0

    results.append({
        'horse'       : row['horse_name'],
        'sire_cat'    : sire_cat,
        'blood_score' : blood_score,
        'win'         : win_flag,
        'win_return'  : win_return,
    })

t1 = time.perf_counter()
time_100_py = t1 - t0

wins       = sum(1 for r in results if r['win'])
ret_sum    = sum(r['win_return'] for r in results)
per_item   = time_100_py / 100

print(f"  100件処理時間 : {time_100_py*1000:.2f} ms")
print(f"  1件あたり     : {per_item*1000:.4f} ms")
print(f"  サンプル結果  : 的中 {wins}/100 / 回収率 {ret_sum:.1f}%")

# =====================================================================
# 推定所要時間
# =====================================================================
print()
print("=" * 60)
print("【推定所要時間】")
print(f"  対象件数: {TARGET:,} 件")
print()

# SQL方式
est_sql = time_full_sql  # すでに全件実測済み
print(f"  SQLバッチ方式（推奨）")
print(f"    実測（全JOIN済み）: {est_sql:.3f} 秒")
print(f"    → 処理完了まで: ≈ {est_sql:.1f} 秒  ★最速")

# Python行単位方式
est_py_target  = per_item * TARGET
est_py_joined  = per_item * joined
print()
print(f"  Python行単位方式")
print(f"    1件あたり          : {per_item*1000:.4f} ms")
print(f"    {TARGET:,}件の推定  : {est_py_target:.1f} 秒  ({est_py_target/60:.1f} 分)")
print(f"    JOIN済{joined:,}件  : {est_py_joined:.1f} 秒  ({est_py_joined/60:.1f} 分)")

print()
print("=" * 60)
print("【まとめ】")
print(f"  ・SQLバッチ処理  : {est_sql:.2f} 秒（現実的な全件集計方式）")
print(f"  ・Python行単位   : {est_py_target/60:.1f} 分（{TARGET:,}件）")
print(f"  → 本番実行推奨方式: SQLバッチ（{est_sql:.1f}秒で完了）")

conn.close()
print("\n=== 完了 ===")
