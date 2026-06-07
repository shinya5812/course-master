# -*- coding: utf-8 -*-
"""
条件C（新潟×芝×2000m×スタミナ系×10番人気以上）
馬場状態別バックテスト

仮説: 5/10新潟5R「良馬場・堅決着・全外れ」を受け、
      良馬場 vs 稍重以上 で的中率・回収率に差があるか検証
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

BASE_WHERE = """
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.venue = '新潟'
      AND rr.surface = '芝'
      AND rr.distance BETWEEN 1801 AND 2100
      AND bc.category = 'スタミナ系'
      AND rr.popularity >= 10
      AND rr.tansho_odds > 0
"""

SEP  = "=" * 64
SEP2 = "─" * 56

def pct(a, b):
    return a / b * 100 if b else 0.0

print(SEP)
print("【条件C 馬場状態別バックテスト】")
print("  新潟×芝×2000m×スタミナ系×10番人気以上")
print(SEP)

# ──────────────────────────────────────────────
# 1. 全体サマリー
# ──────────────────────────────────────────────
cur.execute(f"""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN finish_pos=1 THEN tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
""")
overall = cur.fetchone()
print(f"\n■ 全体: {overall['total']}R / {overall['wins']}勝 / 的中率{pct(overall['wins'],overall['total']):.1f}% / 回収率{overall['rec']}%")

# ──────────────────────────────────────────────
# 2. 良 vs 稍重以上（2グループ比較）
# ──────────────────────────────────────────────
print(f"\n■ 良 vs 稍重以上（2グループ）")
print(f"  {'グループ':^8} {'R数':>5} {'勝':>3} {'的中率':>6} {'回収率':>8} {'1着平均Ods':>10}")
print("  " + SEP2)

two_groups = []
for label, cond in [("良", "rr.track_cond = '良'"),
                    ("稍重以上", "rr.track_cond IN ('稍','重','不')")]:
    cur.execute(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) as avg_win_odds,
               ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
        {BASE_WHERE} AND {cond}
    """)
    r = cur.fetchone()
    hit = pct(r['wins'], r['total'])
    wo  = f"{r['avg_win_odds']}倍" if r['avg_win_odds'] else "─"
    flag = " ★" if r['rec'] and r['rec'] >= 100 else ""
    print(f"  {label:^8} {r['total']:>5} {r['wins']:>3} {hit:>5.1f}% {r['rec']:>7.1f}%{flag}  {wo:>10}")
    two_groups.append({
        "group": label,
        "total": r['total'],
        "wins": r['wins'],
        "hit_rate": round(hit, 2),
        "roi": r['rec'],
        "avg_win_odds": r['avg_win_odds']
    })

# ──────────────────────────────────────────────
# 3. 4馬場状態別
# ──────────────────────────────────────────────
print(f"\n■ 馬場状態別（4区分）")
print(f"  {'馬場':^4} {'R数':>5} {'構成比':>6} {'勝':>3} {'的中率':>6} {'回収率':>8} {'1着平均Ods':>10}")
print("  " + SEP2)

by_cond = []
for cond in ['良', '稍', '重', '不']:
    cur.execute(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) as avg_win_odds,
               ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
        {BASE_WHERE} AND rr.track_cond = ?
    """, (cond,))
    r = cur.fetchone()
    hit  = pct(r['wins'], r['total'])
    cpct = pct(r['total'], overall['total'])
    wo   = f"{r['avg_win_odds']}倍" if r['avg_win_odds'] else "─"
    flag = " ★" if r['rec'] and r['rec'] >= 100 else (" ✕" if r['total'] >= 10 and (r['rec'] or 0) < 50 else "")
    print(f"  {cond:^4} {r['total']:>5} {cpct:>5.1f}%  {r['wins']:>3} {hit:>5.1f}% {r['rec']:>7.1f}%{flag}  {wo:>10}")
    by_cond.append({
        "track_cond": cond,
        "total": r['total'],
        "wins": r['wins'],
        "hit_rate": round(hit, 2),
        "roi": r['rec'],
        "avg_win_odds": r['avg_win_odds']
    })

# ──────────────────────────────────────────────
# 4. 良馬場・年別（重点分析）
# ──────────────────────────────────────────────
print(f"\n■ 良馬場の年別成績（2017〜）")
print(f"  {'年':^5} {'R数':>5} {'勝':>3} {'的中率':>6} {'回収率':>8}  判定")
print("  " + SEP2)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND rr.track_cond = '良'
      AND SUBSTR(rr.race_date,1,4) >= '2017'
    GROUP BY yr ORDER BY yr
""")
ryo_by_year = []
for r in cur.fetchall():
    hit   = pct(r['wins'], r['total'])
    judge = "◎" if (r['rec'] or 0) >= 150 else ("○" if (r['rec'] or 0) >= 100 else ("△" if (r['rec'] or 0) >= 70 else "✕"))
    print(f"  {r['yr']:^5} {r['total']:>5} {r['wins']:>3} {hit:>5.1f}% {r['rec']:>7.1f}%   {judge}")
    ryo_by_year.append({"year": r['yr'], "total": r['total'], "wins": r['wins'],
                        "hit_rate": round(hit, 2), "roi": r['rec']})

# ──────────────────────────────────────────────
# 5. 良馬場×月別
# ──────────────────────────────────────────────
print(f"\n■ 良馬場の月別成績")
print(f"  {'月':^5} {'R数':>5} {'勝':>3} {'的中率':>6} {'回収率':>8}")
print("  " + SEP2)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,6,2) as mon,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND rr.track_cond = '良'
    GROUP BY mon ORDER BY mon
""")
MONTH_MAP = {'04':'4月','05':'5月','07':'7月','08':'8月','09':'9月','10':'10月','11':'11月'}
ryo_by_month = []
for r in cur.fetchall():
    hit  = pct(r['wins'], r['total'])
    flag = " ★" if (r['rec'] or 0) >= 100 else (" ✕" if r['total'] >= 10 and (r['rec'] or 0) == 0 else "")
    print(f"  {MONTH_MAP.get(r['mon'], r['mon']):^5} {r['total']:>5} {r['wins']:>3} {hit:>5.1f}% {r['rec']:>7.1f}%{flag}")
    ryo_by_month.append({"month": MONTH_MAP.get(r['mon'], r['mon']), "total": r['total'],
                         "wins": r['wins'], "hit_rate": round(hit, 2), "roi": r['rec']})

# ──────────────────────────────────────────────
# 6. 考察（自動判定）
# ──────────────────────────────────────────────
ryo  = next(g for g in two_groups if g["group"] == "良")
saju = next(g for g in two_groups if g["group"] == "稍重以上")

print(f"\n{SEP}")
print("■ 考察")
print(SEP)

if ryo['roi'] and saju['roi'] and abs(ryo['roi'] - saju['roi']) >= 20:
    diff = saju['roi'] - ryo['roi']
    direction = "稍重以上が有利" if diff > 0 else "良が有利"
    print(f"  良({ryo['roi']}%) と 稍重以上({saju['roi']}%) で {abs(diff):.1f}pt差 → {direction}")
else:
    print(f"  良({ryo['roi']}%) と 稍重以上({saju['roi']}%) の差は小さい（明確な分離なし）")

# 良馬場の堅決着との関係
cur.execute(f"""
    SELECT ROUND(AVG(rr.popularity),1) as avg_pop_win
    {BASE_WHERE}
      AND rr.track_cond = '良'
      AND rr.finish_pos = 1
""")
ryo_win = cur.fetchone()
if ryo_win and ryo_win['avg_pop_win']:
    print(f"  良馬場1着馬の平均人気: {ryo_win['avg_pop_win']}番人気")
    if ryo_win['avg_pop_win'] < 13:
        print(f"  → 良馬場では10番人気以上の中でも比較的上位人気が来やすい傾向")
    else:
        print(f"  → 良馬場でも超穴馬（13番人気以上）が来るケースあり")

# ──────────────────────────────────────────────
# 7. JSON保存
# ──────────────────────────────────────────────
result = {
    "meta": {
        "script": "backtest_conditionC_track.py",
        "condition": "新潟×芝×1801-2100m×スタミナ系×10番人気以上",
        "purpose": "馬場状態（良 vs 稍重以上）で的中率・回収率の差を検証",
        "trigger": "2026-05-10新潟5R 良馬場で堅決着・全5頭外れ"
    },
    "overall": {
        "total": overall['total'],
        "wins": overall['wins'],
        "hit_rate": round(pct(overall['wins'], overall['total']), 2),
        "roi": overall['rec']
    },
    "two_groups": two_groups,
    "by_track_cond": by_cond,
    "ryo_by_year": ryo_by_year,
    "ryo_by_month": ryo_by_month
}

out_path = os.path.join(BASE_DIR, 'backtest_conditionC_track.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"\n保存先: {out_path}")
print("=== 完了 ===")

conn.close()
