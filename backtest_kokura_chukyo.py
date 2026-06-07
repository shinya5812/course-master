# -*- coding: utf-8 -*-
"""
バックテスト: 小倉または中京 × 7〜9番人気 × 血統適性上位
サンプル数と回収率のトレードオフ確認 + 年別安定性チェック
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
    """
    回収率計算
    tansho_odds は実数（例: 48.6 → 48.6倍）
    100円馬券で的中時の払い戻し = tansho_odds * 100円
    回収率% = SUM(tansho_odds when win) * 100 / total
    """
    if total == 0:
        return 0.0, 0.0
    hit_rate = wins / total * 100
    recovery = (return_sum or 0) * 100 / total
    return hit_rate, recovery

def run_query(where_extra="", params=()):
    sql = f"""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN rr.finish_pos = 1 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN rr.finish_pos = 1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.venue IN ('小倉', '中京')
      AND rr.tansho_odds > 0
      {where_extra}
    """
    cur.execute(sql, params)
    r = cur.fetchone()
    return r['total'], r['wins'], r['return_sum']

def backtest(label, where_extra="", params=()):
    total, wins, return_sum = run_query(where_extra, params)
    hr, rec = calc_recovery(wins, return_sum, total)
    mark = " ★" if rec >= 100 else ""
    print(f"  {label:35s} | {total:6,}R | 的中率 {hr:5.1f}% | 回収率 {rec:6.1f}%{mark}")
    return total, wins, return_sum

print("=" * 75)
print("バックテスト: 小倉または中京 × 7〜9番人気 × 血統適性上位")
print("[回収率計算] 100円投資 / 払い戻し = tansho_odds * 100円")
print("=" * 75)

# ---- A. 全体 ----
print("\n【A. 全体】")
backtest("小倉+中京 × 7-9人気 × 血統適性上位（全体）")

# 比較: 血統フィルターなし（ベースライン）
cur.execute("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN finish_pos=1 THEN tansho_odds ELSE 0 END) as return_sum
    FROM race_results
    WHERE popularity BETWEEN 7 AND 9
      AND venue IN ('小倉','中京')
      AND tansho_odds > 0
""")
r = cur.fetchone()
hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
print(f"  {'[比較] 血統フィルターなし（全馬）':35s} | {r['total']:6,}R | 的中率 {hr:5.1f}% | 回収率 {rec:6.1f}%")

# ---- B. 会場別 ----
print("\n【B. 会場別】")
backtest("小倉のみ", "AND rr.venue = '小倉'")
backtest("中京のみ", "AND rr.venue = '中京'")

# ---- C. 芝・ダート別 ----
print("\n【C. 芝・ダート別】")
backtest("芝のみ",   "AND rr.surface = '芝'")
backtest("ダートのみ", "AND rr.surface = 'ダ'")

# ---- D. 距離帯別 ----
print("\n【D. 距離帯別】")
backtest("〜1400m（sprint）",     "AND rr.distance <= 1400")
backtest("1401〜1800m（mile）",   "AND rr.distance BETWEEN 1401 AND 1800")
backtest("1801〜2100m（middle）", "AND rr.distance BETWEEN 1801 AND 2100")
backtest("2101m〜（long）",       "AND rr.distance >= 2101")

# ---- E. 会場×芝ダ クロス集計 ----
print("\n【E. 会場×芝ダ クロス集計（100R以上）】")
cur.execute("""
    SELECT rr.venue, rr.surface,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.venue IN ('小倉','中京')
      AND rr.tansho_odds > 0
    GROUP BY rr.venue, rr.surface
    HAVING total >= 100
    ORDER BY (COALESCE(return_sum,0)*100.0/total) DESC
""")
for r in cur.fetchall():
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    label = f"{r['venue']} × {r['surface']}"
    mark = " ★" if rec >= 100 else ""
    print(f"  {label:35s} | {r['total']:6,}R | 的中率 {hr:5.1f}% | 回収率 {rec:6.1f}%{mark}")

# ---- F. 年別安定性チェック ----
print("\n【F. 年別安定性チェック（全体条件）】")
cur.execute("""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.venue IN ('小倉','中京')
      AND rr.tansho_odds > 0
    GROUP BY yr ORDER BY yr
""")
print(f"  {'年':^6} | {'R数':>6} | 的中率  | 回収率")
print("  " + "-" * 42)
for r in cur.fetchall():
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {r['yr']:^6} | {r['total']:6,} | {hr:5.1f}%  | {rec:6.1f}%{mark}")

# ---- G. 血統カテゴリ別 ----
print("\n【G. 血統カテゴリ別（小倉+中京 × 7-9人気）】")
cur.execute("""
    SELECT bc.category,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.venue IN ('小倉','中京')
      AND rr.tansho_odds > 0
    GROUP BY bc.category
    ORDER BY (COALESCE(return_sum,0)*100.0/total) DESC
""")
print(f"  {'カテゴリ':15s} | {'R数':>6} | 的中率  | 回収率")
print("  " + "-" * 48)
for r in cur.fetchall():
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {r['category']:15s} | {r['total']:6,} | {hr:5.1f}%  | {rec:6.1f}%{mark}")

# ---- H. 距離カテゴリ一致フィルター ----
print("\n【H. 距離カテゴリ一致フィルター（厳密な血統適性）】")
dist_cat_sql = """
    (rr.distance <= 1400 AND bc.category = '速力系')
    OR (rr.distance BETWEEN 1401 AND 1800 AND bc.category = 'マイラー系')
    OR (rr.distance BETWEEN 1801 AND 2100 AND bc.category = 'スタミナ系')
    OR (rr.distance >= 2101 AND bc.category = 'スタミナ系')
"""
for match, label in [("AND ("+dist_cat_sql+")", "距離カテゴリ一致あり"),
                     ("AND NOT ("+dist_cat_sql+")", "距離カテゴリ不一致")]:
    total, wins, return_sum = run_query(match)
    hr, rec = calc_recovery(wins, return_sum, total)
    mark = " ★" if rec >= 100 else ""
    print(f"  {label:20s} | {total:6,}R | 的中率 {hr:5.1f}% | 回収率 {rec:6.1f}%{mark}")

# ---- I. 年別 × 距離カテゴリ一致 ----
print("\n【I. 年別安定性（距離カテゴリ一致フィルター）】")
cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.venue IN ('小倉','中京')
      AND rr.tansho_odds > 0
      AND ({dist_cat_sql})
    GROUP BY yr ORDER BY yr
""")
print(f"  {'年':^6} | {'R数':>6} | 的中率  | 回収率")
print("  " + "-" * 42)
for r in cur.fetchall():
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {r['yr']:^6} | {r['total']:6,} | {hr:5.1f}%  | {rec:6.1f}%{mark}")

# ---- J. 推奨フィルター候補（100R以上、回収率順） ----
print("\n【J. 細分化フィルター候補（会場×芝ダ×距離帯×血統カテゴリ、100R以上）】")
cur.execute("""
    SELECT
        rr.venue, rr.surface,
        CASE
            WHEN rr.distance <= 1400 THEN 'sprint(〜1400)'
            WHEN rr.distance <= 1800 THEN 'mile(〜1800)'
            WHEN rr.distance <= 2100 THEN 'middle(〜2100)'
            ELSE 'long(2101〜)'
        END as dist_band,
        bc.category as sire_cat,
        COUNT(*) as total,
        SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.venue IN ('小倉','中京')
      AND rr.tansho_odds > 0
    GROUP BY rr.venue, rr.surface, dist_band, bc.category
    HAVING total >= 100
    ORDER BY (COALESCE(return_sum,0)*100.0/total) DESC
    LIMIT 15
""")
print(f"  {'会場×芝ダ×距離帯×血統':42s} | {'R数':>5} | 的中率  | 回収率")
print("  " + "-" * 70)
for r in cur.fetchall():
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    label = f"{r['venue']} × {r['surface']} × {r['dist_band']} × {r['sire_cat']}"
    mark = " ★" if rec >= 100 else ""
    print(f"  {label:42s} | {r['total']:5,} | {hr:5.1f}%  | {rec:6.1f}%{mark}")

# ---- K. 最良条件を絞り込んだ年別チェック ----
# J で最も良さそうな: 中京×芝×sprint×速力系 (295R, 回収率が高ければ)
# 検証用に年別に確認
print("\n【K. 年別詳細（注目条件: 中京×芝×sprint(〜1400)×速力系）】")
cur.execute("""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.popularity BETWEEN 7 AND 9
      AND rr.venue = '中京'
      AND rr.surface = '芝'
      AND rr.distance <= 1400
      AND bc.category = '速力系'
      AND rr.tansho_odds > 0
    GROUP BY yr ORDER BY yr
""")
rows = cur.fetchall()
print(f"  {'年':^6} | {'R数':>6} | 的中率  | 回収率")
print("  " + "-" * 42)
for r in rows:
    hr, rec = calc_recovery(r['wins'], r['return_sum'], r['total'])
    mark = " ★" if rec >= 100 else ""
    print(f"  {r['yr']:^6} | {r['total']:6,} | {hr:5.1f}%  | {rec:6.1f}%{mark}")

# ---- L. 前回バックテストの再現確認（course_win_rate一致条件つき） ----
print("\n【L. 前回比較: course_win_rate一致条件を追加】")
total, wins, return_sum = run_query("""
    AND EXISTS (
        SELECT 1 FROM course_win_rate cwr
        WHERE cwr.venue = rr.venue
          AND cwr.surface = rr.surface
          AND cwr.distance = rr.distance
          AND cwr.condition = rr.track_cond
    )
""")
hr, rec = calc_recovery(wins, return_sum, total)
mark = " ★" if rec >= 100 else ""
print(f"  {'小倉+中京×7-9人気×血統×course_win_rate一致':35s} | {total:6,}R | 的中率 {hr:5.1f}% | 回収率 {rec:6.1f}%{mark}")

conn.close()
print("\n=== 完了 ===")
