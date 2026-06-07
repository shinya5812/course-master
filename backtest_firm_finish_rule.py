# -*- coding: utf-8 -*-
"""
堅め決着ルール バックテスト正式化
race_results（2015〜2026年）を使用

【制約事項】
- 降雨データは race_results に非搭載 → track_cond（良/稍/重/不）を代替指標として使用
- grade情報（G1/G2/G3）は非搭載 → race_no=11 + 条件で重賞近似
- 「前日20mm以上の降雨 × 当日良馬場」= 「良馬場かつ前週/前日が稍〜重だった日付」は
  track_cond変化がないため直接検証不可 → 良馬場限定×低オッズで代替
"""

import sqlite3
import os
import sys
import io
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'course_master.db')

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ── 全レース（人気×着順×オッズ×馬場×会場）を取得 ──────────────────────────
cur.execute("""
    SELECT race_date, venue, surface, distance, track_cond,
           race_no, finish_pos, popularity, tansho_odds
    FROM race_results
    WHERE popularity IS NOT NULL AND tansho_odds IS NOT NULL AND tansho_odds > 0
    ORDER BY race_date, venue, race_no
""")
rows = cur.fetchall()
conn.close()

print(f"総レコード数: {len(rows):,}件")

# レース単位に集約
# key = (race_date, venue, race_no)
# value = list of horses
races = defaultdict(list)
for race_date, venue, surface, distance, track_cond, race_no, finish_pos, popularity, odds in rows:
    key = (race_date, venue, race_no)
    races[key].append({
        'date': race_date,
        'venue': venue,
        'surface': surface,
        'distance': distance,
        'track_cond': track_cond,
        'finish_pos': finish_pos,
        'popularity': popularity,
        'odds': odds,
    })

print(f"レース数: {len(races):,}件")

# ── Step 1: 降雨データ確認 ────────────────────────────────────────────────────
print()
print("=" * 70)
print("【Step 1】race_results で利用可能な馬場・気象関連カラム")
print("=" * 70)
print("  ✅ track_cond（良/稍/重/不） → 馬場状態の代替指標として使用")
print("  ❌ 降雨データ（前日降水量 mm） → 非搭載。検証不可。")
print("  ❌ grade（G1/G2/G3）         → 非搭載。race_no=11+条件で近似。")
print()
print("  ▶ 代替方針:")
print("    1. 馬場状態（良 vs 稍重・重・不良）別の1番人気勝率を算出")
print("    2. 1番人気オッズ帯×良馬場 で「人気集中×良馬場」を疑似荒れ指数として使用")
print("    3. 重賞近似: race_no=11 AND surface=芝 AND distance>=1200 AND 頭数>=10")

# ── Step 2: 馬場状態別 1番人気勝率 ───────────────────────────────────────────
print()
print("=" * 70)
print("【Step 2】馬場状態別 1番人気勝率（2015〜2026年 全レース）")
print("=" * 70)

COND_LABELS = {'良': '良     ', '稍': '稍重   ', '重': '重     ', '不': '不良   '}
VENUES_MAIN = ['東京', '中山', '阪神', '京都', '中京', '福島', '新潟', '小倉', '函館', '札幌']

# 全体
cond_stats = defaultdict(lambda: {'bets': 0, 'hits': 0, 'payout': 0.0})
for key, horses in races.items():
    fav = next((h for h in horses if h['popularity'] == 1), None)
    if not fav:
        continue
    tc = fav['track_cond']
    cond_stats[tc]['bets'] += 1
    if fav['finish_pos'] == 1:
        cond_stats[tc]['hits'] += 1
        cond_stats[tc]['payout'] += fav['odds']

print(f"\n  {'馬場':8s} {'R数':>7s} {'1着数':>6s} {'勝率':>7s} {'単勝回収率':>10s}")
print("  " + "-" * 45)
for tc, label in [('良', '良'), ('稍', '稍重'), ('重', '重'), ('不', '不良')]:
    d = cond_stats[tc]
    wr = d['hits'] / d['bets'] * 100 if d['bets'] > 0 else 0
    rec = d['payout'] * 100 / d['bets'] if d['bets'] > 0 else 0
    print(f"  {label:8s} {d['bets']:>7,d} {d['hits']:>6,d} {wr:>6.1f}% {rec:>9.1f}%")

# 会場×馬場別（芝レース・1番人気）
print(f"\n  --- 会場×馬場別（芝 全レース 1番人気勝率）---")
print(f"  {'会場':6s} {'良':>10s} {'稍重':>10s} {'重':>10s} {'不良':>10s}")
print("  " + "-" * 50)
venue_cond = defaultdict(lambda: defaultdict(lambda: {'b': 0, 'h': 0}))
for key, horses in races.items():
    fav = next((h for h in horses if h['popularity'] == 1), None)
    if not fav or fav['surface'] != '芝':
        continue
    venue_cond[fav['venue']][fav['track_cond']]['b'] += 1
    if fav['finish_pos'] == 1:
        venue_cond[fav['venue']][fav['track_cond']]['h'] += 1

for v in VENUES_MAIN:
    d = venue_cond.get(v, {})
    def fmt(tc):
        dd = d.get(tc, {'b': 0, 'h': 0})
        if dd['b'] == 0:
            return '   —'
        return f"{dd['h']/dd['b']*100:4.1f}%({dd['b']:4d})"
    print(f"  {v:6s} {fmt('良'):>12s} {fmt('稍'):>12s} {fmt('重'):>12s} {fmt('不'):>12s}")

# ── Step 3: オッズ帯×良馬場 ──────────────────────────────────────────────────
print()
print("=" * 70)
print("【Step 3】荒れ指数代替：1番人気オッズ帯 × 良馬場 の勝率・回収率")
print("  （低オッズ=人気集中=荒れにくい、高オッズ=荒れやすい）")
print("=" * 70)

# オッズ帯定義
ODDS_BANDS = [
    ('〜2.9倍',  0,    2.9),
    ('3.0〜4.9', 3.0,  4.9),
    ('5.0〜7.9', 5.0,  7.9),
    ('8.0〜11.9',8.0, 11.9),
    ('12倍以上', 12.0, 999),
]

print(f"\n  --- 良馬場 ---")
print(f"  {'オッズ帯':12s} {'R数':>7s} {'勝率':>7s} {'回収率':>9s}  荒れ指数対応目安")
print("  " + "-" * 65)
for label, lo, hi in ODDS_BANDS:
    bets = hits = 0
    payout = 0.0
    for key, horses in races.items():
        fav = next((h for h in horses if h['popularity'] == 1), None)
        if not fav or fav['track_cond'] != '良':
            continue
        if lo <= fav['odds'] <= hi:
            bets += 1
            if fav['finish_pos'] == 1:
                hits += 1
                payout += fav['odds']
    wr = hits / bets * 100 if bets > 0 else 0
    rec = payout * 100 / bets if bets > 0 else 0
    # 荒れ指数対応
    chaos = '〜40（安定）' if hi <= 2.9 else '40〜55（やや安定）' if hi <= 4.9 else '55〜70（やや波乱）' if hi <= 7.9 else '70〜（波乱）'
    print(f"  {label:12s} {bets:>7,d} {wr:>6.1f}% {rec:>8.1f}%  {chaos}")

print(f"\n  --- 稍重・重・不良 ---")
print(f"  {'オッズ帯':12s} {'R数':>7s} {'勝率':>7s} {'回収率':>9s}")
print("  " + "-" * 45)
for label, lo, hi in ODDS_BANDS:
    bets = hits = 0
    payout = 0.0
    for key, horses in races.items():
        fav = next((h for h in horses if h['popularity'] == 1), None)
        if not fav or fav['track_cond'] == '良':
            continue
        if lo <= fav['odds'] <= hi:
            bets += 1
            if fav['finish_pos'] == 1:
                hits += 1
                payout += fav['odds']
    wr = hits / bets * 100 if bets > 0 else 0
    rec = payout * 100 / bets if bets > 0 else 0
    print(f"  {label:12s} {bets:>7,d} {wr:>6.1f}% {rec:>8.1f}%")

# ── Step 4: 重賞近似（race_no=11 & 芝 & distance>=1200 & 頭数>=12) ───────────
print()
print("=" * 70)
print("【Step 4】「良馬場 × 1番人気5倍以下」条件別の比較")
print("  重賞近似: race_no=11 AND 芝 AND 距離>=1200m AND 頭数>=12")
print("=" * 70)

GRADE_APPROX_VENUES = ['東京', '中山', '阪神', '京都', '中京', '新潟', '福島', '小倉', '函館', '札幌']

def is_grade_approx(key, horses):
    """重賞近似フィルター"""
    _, venue, race_no = key
    if race_no != 11:
        return False
    if not horses:
        return False
    h0 = horses[0]
    if h0['surface'] != '芝':
        return False
    if h0['distance'] < 1200:
        return False
    if len(horses) < 12:
        return False
    return True

# 重賞近似レース抽出
grade_approx = {k: v for k, v in races.items() if is_grade_approx(k, v)}
print(f"\n  重賞近似レース数: {len(grade_approx):,}件（全 {len(races):,}件中）")

# 条件別比較
CONDITIONS = [
    ('全レース（重賞近似）',            lambda tc, odds: True),
    ('良馬場',                         lambda tc, odds: tc == '良'),
    ('稍重・重・不良',                  lambda tc, odds: tc != '良'),
    ('良馬場 × オッズ5倍以下',         lambda tc, odds: tc == '良' and odds <= 5.0),
    ('良馬場 × オッズ5倍超',           lambda tc, odds: tc == '良' and odds > 5.0),
    ('稍重以下 × オッズ5倍以下',       lambda tc, odds: tc != '良' and odds <= 5.0),
]

print(f"\n  {'条件':28s} {'R数':>6s} {'1人勝率':>8s} {'1人回収率':>10s}")
print("  " + "-" * 60)
for label, cond_fn in CONDITIONS:
    bets = hits = 0
    payout = 0.0
    for key, horses in grade_approx.items():
        fav = next((h for h in horses if h['popularity'] == 1), None)
        if not fav:
            continue
        if not cond_fn(fav['track_cond'], fav['odds']):
            continue
        bets += 1
        if fav['finish_pos'] == 1:
            hits += 1
            payout += fav['odds']
    if bets == 0:
        continue
    wr = hits / bets * 100
    rec = payout * 100 / bets
    marker = " ◀ 堅め決着ルール対象" if '良馬場 × オッズ5倍以下' in label else ""
    print(f"  {label:28s} {bets:>6,d} {wr:>7.1f}% {rec:>9.1f}%{marker}")

# 年別安定性（良馬場 × オッズ5倍以下）
print(f"\n  --- 年別（良馬場 × オッズ5倍以下 重賞近似） ---")
yearly = defaultdict(lambda: {'b': 0, 'h': 0, 'p': 0.0})
for key, horses in grade_approx.items():
    fav = next((h for h in horses if h['popularity'] == 1), None)
    if not fav or fav['track_cond'] != '良' or fav['odds'] > 5.0:
        continue
    year = key[0][:4]
    yearly[year]['b'] += 1
    if fav['finish_pos'] == 1:
        yearly[year]['h'] += 1
        yearly[year]['p'] += fav['odds']

black = 0
for year in sorted(yearly.keys()):
    d = yearly[year]
    wr = d['h'] / d['b'] * 100
    rec = d['p'] * 100 / d['b']
    mk = '★' if rec >= 80 else ' '  # 回収率80%以上を"黒字近辺"として★
    if rec >= 80:
        black += 1
    print(f"    {year}: {d['b']:3d}R  勝率{wr:5.1f}%  回収率{rec:6.1f}% {mk}")
print(f"  回収率80%以上年: {black}/{len(yearly)}年")

# ── Step 5: エンジン◎ vs 1番人気（grade_race_evaluation の結果を再利用） ──────
print()
print("=" * 70)
print("【Step 5】結論：堅め決着ルール（1番人気優先）の統計的評価")
print("=" * 70)

# 重賞近似での良馬場 1番人気 総計
bets_y = hits_y = 0
payout_y = 0.0
bets_n = hits_n = 0
payout_n = 0.0
for key, horses in grade_approx.items():
    fav = next((h for h in horses if h['popularity'] == 1), None)
    if not fav:
        continue
    if fav['track_cond'] == '良':
        bets_y += 1
        if fav['finish_pos'] == 1:
            hits_y += 1
            payout_y += fav['odds']
    else:
        bets_n += 1
        if fav['finish_pos'] == 1:
            hits_n += 1
            payout_n += fav['odds']

wr_y  = hits_y  / bets_y  * 100 if bets_y  else 0
rec_y = payout_y  * 100 / bets_y  if bets_y  else 0
wr_n  = hits_n  / bets_n  * 100 if bets_n  else 0
rec_n = payout_n  * 100 / bets_n  if bets_n  else 0

print(f"""
  【重賞近似 × 1番人気 単勝】
  良馬場:         勝率{wr_y:5.1f}%  回収率{rec_y:6.1f}%  ({bets_y:,}R)
  稍重・重・不良: 勝率{wr_n:5.1f}%  回収率{rec_n:6.1f}%  ({bets_n:,}R)
  良馬場での勝率優位: {wr_y - wr_n:+.1f}%  回収率優位: {rec_y - rec_n:+.1f}%
""")

# 既存バックテスト数値（grade_race_evaluation.py で算出済み）
print("  【参照: grade_race_evaluation.py 重賞1,544R バックテスト済み数値】")
print("  エンジン◎ 全体:      勝率35.3%  回収率148.8%")
print("  1番人気 全体:         勝率29.5%  回収率  約80%（市場控除分）")
print("  エンジン◎ vs 1番人気: +5.8%優位")
print()

# 低オッズ帯での詳細
print("  【重賞近似 × 良馬場 × オッズ帯別 詳細】")
print(f"  {'オッズ帯':12s} {'R数':>6s} {'勝率':>7s} {'回収率':>9s}  参考：控除率後損益")
print("  " + "-" * 60)
for label, lo, hi in ODDS_BANDS:
    bets = hits = 0
    payout = 0.0
    for key, horses in grade_approx.items():
        fav = next((h for h in horses if h['popularity'] == 1), None)
        if not fav or fav['track_cond'] != '良':
            continue
        if lo <= fav['odds'] <= hi:
            bets += 1
            if fav['finish_pos'] == 1:
                hits += 1
                payout += fav['odds']
    if bets == 0:
        continue
    wr = hits / bets * 100
    rec = payout * 100 / bets
    profit_sign = "黒字" if rec >= 100 else "赤字"
    print(f"  {label:12s} {bets:>6,d} {wr:>6.1f}% {rec:>8.1f}%  {profit_sign}")

print()
print("  ━" * 35)
print("  【総合判断】")
