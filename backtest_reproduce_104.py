# -*- coding: utf-8 -*-
"""
104.7%バックテスト再現スクリプト
前回条件: 全会場 × 人気4以上 × blood_category距離適性一致 × course_win_rate存在
人気帯別に分解して104.7%が再現できるか検証する
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

def calc_recovery(wins, return_sum, total):
    if total == 0:
        return 0.0, 0.0
    hit_rate = wins / total * 100
    recovery = (return_sum or 0) * 100 / total
    return hit_rate, recovery

# 距離適性一致フィルター（SQLフラグメント）
DIST_CAT_MATCH = """
    (
        (rr.distance <= 1400 AND bc.category = '速力系')
        OR (rr.distance BETWEEN 1401 AND 1800 AND bc.category = 'マイラー系')
        OR (rr.distance BETWEEN 1801 AND 2100 AND bc.category = 'スタミナ系')
        OR (rr.distance >= 2101 AND bc.category = 'スタミナ系')
    )
"""

# course_win_rate存在確認フィルター
CWR_EXISTS = """
    EXISTS (
        SELECT 1 FROM course_win_rate cwr
        WHERE cwr.venue = rr.venue
          AND cwr.surface = rr.surface
          AND cwr.distance = rr.distance
          AND cwr.condition = rr.track_cond
    )
"""

print("=" * 80)
print("前回バックテスト(104.7%)再現確認")
print("条件: 全会場 × 血統距離適性一致 × course_win_rate存在")
print("[回収率] = SUM(tansho_odds when win) * 100 / total")
print("=" * 80)

# ---- A. 人気帯別（全会場） ----
print("\n【A. 人気帯別 - 全会場 × 血統距離適性一致 × course_win_rate存在】")
bands = [
    ("4〜6番人気",  "BETWEEN 4 AND 6"),
    ("7〜9番人気",  "BETWEEN 7 AND 9"),
    ("10番人気以下", ">= 10"),
    ("4番人気以下",  ">= 4"),  # 前回の「人気4番以下」全体
]
for label, pop_cond in bands:
    cur.execute(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
        FROM race_results rr
        INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
        WHERE rr.popularity {pop_cond}
          AND rr.tansho_odds > 0
          AND {DIST_CAT_MATCH}
          AND {CWR_EXISTS}
    """)
    r = cur.fetchone()
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {label:15s} | {r['total']:7,}R | 的中率 {hr:5.1f}% | 回収率 {rec:7.2f}%{mark}")

# ---- B. 比較: course_win_rate条件なし ----
print("\n【B. 比較: course_win_rate条件なし（全会場 × 血統距離適性一致のみ）】")
for label, pop_cond in bands:
    cur.execute(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
        FROM race_results rr
        INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
        WHERE rr.popularity {pop_cond}
          AND rr.tansho_odds > 0
          AND {DIST_CAT_MATCH}
    """)
    r = cur.fetchone()
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {label:15s} | {r['total']:7,}R | 的中率 {hr:5.1f}% | 回収率 {rec:7.2f}%{mark}")

# ---- C. 比較: 血統適性一致なし（course_win_rateのみ） ----
print("\n【C. 比較: 血統適性フィルターなし（全会場 × course_win_rate存在のみ）】")
for label, pop_cond in bands:
    cur.execute(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
        FROM race_results rr
        WHERE rr.popularity {pop_cond}
          AND rr.tansho_odds > 0
          AND {CWR_EXISTS}
    """)
    r = cur.fetchone()
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {label:15s} | {r['total']:7,}R | 的中率 {hr:5.1f}% | 回収率 {rec:7.2f}%{mark}")

# ---- D. 年別安定性（7〜9人気 × 全条件） ----
print("\n【D. 年別安定性 - 7〜9番人気 × 全会場 × 血統距離適性 × course_win_rate】")
cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.tansho_odds > 0
      AND {DIST_CAT_MATCH}
      AND {CWR_EXISTS}
    GROUP BY yr ORDER BY yr
""")
print(f"  {'年':^6} | {'R数':>7} | 的中率  | 回収率")
print("  " + "-" * 44)
for r in cur.fetchall():
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {r['yr']:^6} | {r['total']:7,} | {hr:5.1f}%  | {rec:7.2f}%{mark}")

# ---- E. 会場別（7〜9人気 × 全条件） ----
print("\n【E. 会場別 - 7〜9番人気 × 血統距離適性 × course_win_rate（回収率順）】")
cur.execute(f"""
    SELECT rr.venue,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.tansho_odds > 0
      AND {DIST_CAT_MATCH}
      AND {CWR_EXISTS}
    GROUP BY rr.venue
    HAVING total >= 100
    ORDER BY (COALESCE(return_sum,0)*100.0/total) DESC
""")
print(f"  {'会場':10s} | {'R数':>7} | 的中率  | 回収率")
print("  " + "-" * 44)
for r in cur.fetchall():
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {r['venue']:10s} | {r['total']:7,} | {hr:5.1f}%  | {rec:7.2f}%{mark}")

# ---- F. 別仮説: 前回はレース単位（1レース1ベット）で計算していた？ ----
print("\n【F. 別仮説: 1レース最高オッズ馬1頭のみベット（レース代表馬方式）】")
cur.execute(f"""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.tansho_odds > 0
      AND {DIST_CAT_MATCH}
      AND {CWR_EXISTS}
      AND rr.tansho_odds = (
          SELECT MAX(rr2.tansho_odds)
          FROM race_results rr2
          INNER JOIN blood_category bc2 ON rr2.sire_name = bc2.sire_name
          WHERE rr2.race_date = rr.race_date
            AND rr2.venue = rr.venue
            AND rr2.race_no = rr.race_no
            AND rr2.popularity BETWEEN 7 AND 9
            AND {DIST_CAT_MATCH.replace('rr.', 'rr2.').replace('bc.', 'bc2.')}
      )
""")
r = cur.fetchone()
hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
mark = " ★" if rec >= 100 else ""
print(f"  {'7-9人気×血統×CWR（最高オッズ1頭/レース）':38s} | {r['total']:7,}R | 的中率 {hr:5.1f}% | 回収率 {rec:7.2f}%{mark}")

conn.close()
print("\n=== 完了 ===")
