# -*- coding: utf-8 -*-
"""
条件C（新潟×芝×2000m×スタミナ系×10番人気以上）
良馬場に限定した月別バックテスト

前回発見: 良馬場×5月が222.9%と突出。
目的: 5月が統計的特異値か、他月との比較で検証する。
"""
import sqlite3
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur  = conn.cursor()

MONTH_NAMES = {
    '01':'1月','02':'2月','03':'3月','04':'4月',
    '05':'5月','06':'6月','07':'7月','08':'8月',
    '09':'9月','10':'10月','11':'11月','12':'12月'
}

BASE_WHERE = """
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.venue = '新潟'
      AND rr.surface = '芝'
      AND rr.distance BETWEEN 1801 AND 2100
      AND bc.category = 'スタミナ系'
      AND rr.popularity >= 10
      AND rr.tansho_odds > 0
      AND rr.track_cond = '良'
"""

SEP  = "=" * 64
SEP2 = "─" * 56

def pct(a, b):
    return a / b * 100 if b else 0.0

print(SEP)
print("【条件C 良馬場×月別バックテスト】")
print("  新潟×芝×2000m×スタミナ系×10番人気以上×良馬場")
print(SEP)

# ──────────────────────────────────────────────
# 1. 全体サマリー（良馬場のみ）
# ──────────────────────────────────────────────
cur.execute(f"""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(AVG(rr.tansho_odds),1) as avg_odds,
           ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) as avg_win_odds,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec,
           MIN(rr.race_date) as first_date,
           MAX(rr.race_date) as last_date
    {BASE_WHERE}
""")
overall = cur.fetchone()
print(f"\n■ 全体（良馬場のみ）")
print(f"  期間   : {overall['first_date']} 〜 {overall['last_date']}")
print(f"  R数    : {overall['total']}R / {overall['wins']}勝")
print(f"  的中率 : {pct(overall['wins'], overall['total']):.2f}%")
print(f"  回収率 : {overall['rec']}%")
print(f"  1着平均Ods: {overall['avg_win_odds']}倍 / 全馬平均Ods: {overall['avg_odds']}倍")

# ──────────────────────────────────────────────
# 2. 月別集計（メイン）
# ──────────────────────────────────────────────
print(f"\n■ 月別成績（良馬場）")
print(f"  {'月':^5} {'R数':>5} {'構成比':>6} {'勝':>3} {'的中率':>7} {'回収率':>8} {'1着平均Ods':>10}  判定")
print("  " + SEP2)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,6,2) as mon,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) as avg_win_odds,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
    GROUP BY mon ORDER BY mon
""")
monthly_rows = cur.fetchall()

monthly_data = []
for r in monthly_rows:
    hit   = pct(r['wins'], r['total'])
    cpct  = pct(r['total'], overall['total'])
    wo    = f"{r['avg_win_odds']}倍" if r['avg_win_odds'] else "─"
    rec   = r['rec'] or 0.0
    if   rec >= 200: judge = "◎◎特優"
    elif rec >= 150: judge = "◎優秀"
    elif rec >= 100: judge = "○黒字"
    elif rec >= 70:  judge = "△普通"
    elif r['wins'] == 0 and r['total'] >= 10: judge = "✕0勝"
    else:            judge = "─"

    flag = " ★" if rec >= 100 else (" ✕" if rec == 0 and r['total'] >= 10 else "")
    name = MONTH_NAMES.get(r['mon'], r['mon'])
    print(f"  {name:^5} {r['total']:>5} {cpct:>5.1f}%  {r['wins']:>3} {hit:>6.2f}% {rec:>7.1f}%{flag}  {wo:>10}  {judge}")

    monthly_data.append({
        "month": r['mon'],
        "month_name": name,
        "total": r['total'],
        "wins": r['wins'],
        "hit_rate": round(hit, 3),
        "roi": rec,
        "avg_win_odds": r['avg_win_odds']
    })

# ──────────────────────────────────────────────
# 3. 年別×月別のクロス（5月の特異性確認）
# ──────────────────────────────────────────────
print(f"\n■ 年別×月別 クロス集計（良馬場・主要月のみ）")
print(f"  {'年':^5} {'5月':>8} {'8月':>8} {'9月':>8} {'10月':>9} {'年計':>8}")
print("  " + "─" * 50)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           SUBSTR(rr.race_date,6,2) as mon,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND SUBSTR(rr.race_date,1,4) >= '2017'
    GROUP BY yr, mon ORDER BY yr, mon
""")

from collections import defaultdict
cross = defaultdict(dict)
for r in cur.fetchall():
    cross[r['yr']][r['mon']] = {'total': r['total'], 'wins': r['wins'], 'rec': r['rec'] or 0.0}

cross_by_year = []
for yr in sorted(cross.keys()):
    def cell(mon):
        d = cross[yr].get(mon)
        if not d: return "  ─  "
        rec = d['rec']
        mark = "★" if rec >= 100 else ("✕" if rec == 0 and d['total'] >= 5 else " ")
        return f"{rec:5.0f}%{mark}"

    # 年計
    yr_total = sum(d['total'] for d in cross[yr].values())
    yr_wins  = sum(d['wins']  for d in cross[yr].values())
    yr_rec   = sum(d['wins'] * 0 for d in cross[yr].values())  # 後で計算
    cur.execute(f"""
        SELECT ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
        {BASE_WHERE}
          AND SUBSTR(rr.race_date,1,4) = ?
    """, (yr,))
    yr_rec_r = cur.fetchone()['rec'] or 0.0

    print(f"  {yr:^5} {cell('05'):>8} {cell('08'):>8} {cell('09'):>8} {cell('10'):>9} {yr_rec_r:>6.0f}%")
    cross_by_year.append({"year": yr, "months": dict(cross[yr]), "year_roi": yr_rec_r})

# ──────────────────────────────────────────────
# 4. 5月の詳細（年別）
# ──────────────────────────────────────────────
print(f"\n■ 5月の詳細（良馬場・年別）")
print(f"  {'年':^5} {'R数':>5} {'勝':>3} {'回収率':>8}  判定")
print("  " + "─" * 38)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND SUBSTR(rr.race_date,6,2) = '05'
    GROUP BY yr ORDER BY yr
""")
may_by_year = []
for r in cur.fetchall():
    rec = r['rec'] or 0.0
    judge = "◎" if rec >= 150 else ("○" if rec >= 100 else ("△" if rec >= 70 else "✕"))
    flag  = " ★" if rec >= 100 else ""
    print(f"  {r['yr']:^5} {r['total']:>5} {r['wins']:>3} {rec:>7.1f}%{flag}   {judge}")
    may_by_year.append({"year": r['yr'], "total": r['total'], "wins": r['wins'], "roi": rec})

# ──────────────────────────────────────────────
# 5. 考察（自動判定）
# ──────────────────────────────────────────────
print(f"\n{SEP}")
print("■ 考察")
print(SEP)

# 5月が突出しているか
may_data  = next((d for d in monthly_data if d['month'] == '05'), None)
aug_data  = next((d for d in monthly_data if d['month'] == '08'), None)
zero_months = [d for d in monthly_data if d['wins'] == 0 and d['total'] >= 10]

if may_data:
    print(f"  5月回収率: {may_data['roi']}%（{may_data['total']}R・{may_data['wins']}勝）")
if aug_data:
    print(f"  8月回収率: {aug_data['roi']}%（{aug_data['total']}R・{aug_data['wins']}勝）")
if zero_months:
    names = '・'.join(d['month_name'] for d in zero_months)
    print(f"  0勝月（10R以上）: {names} → 見送り候補")

may_black = sum(1 for d in may_by_year if d['roi'] >= 100)
may_valid = sum(1 for d in may_by_year if d['total'] >= 5)
if may_valid:
    print(f"  5月の安定性: {may_black}/{may_valid}年が100%超（{may_black/may_valid*100:.0f}%）")

# ──────────────────────────────────────────────
# 6. JSON保存
# ──────────────────────────────────────────────
result = {
    "meta": {
        "script": "backtest_conditionC_monthly.py",
        "condition": "新潟×芝×1801-2100m×スタミナ系×10番人気以上×良馬場",
        "purpose": "5月が統計的特異値か検証。前回発見: 良馬場×5月=222.9%"
    },
    "overall": {
        "total": overall['total'],
        "wins": overall['wins'],
        "hit_rate": round(pct(overall['wins'], overall['total']), 3),
        "roi": overall['rec'],
        "period": f"{overall['first_date']} 〜 {overall['last_date']}"
    },
    "monthly": monthly_data,
    "cross_by_year": cross_by_year,
    "may_by_year": may_by_year
}

out_path = os.path.join(BASE_DIR, 'backtest_conditionC_monthly.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n保存先: {out_path}")
print("=== 完了 ===")

conn.close()
