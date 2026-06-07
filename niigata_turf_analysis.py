# -*- coding: utf-8 -*-
"""
条件4（新潟×芝×2000m×スタミナ系×10番人気以上）深掘り分析
福島ダート分析と同じ切り口で実施
"""
import sqlite3, os, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur  = conn.cursor()

BASE_WHERE = """
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name=bc.sire_name
    WHERE rr.venue='新潟' AND rr.surface='芝'
      AND rr.distance BETWEEN 1801 AND 2100
      AND bc.category='スタミナ系'
      AND rr.popularity>=10 AND rr.tansho_odds>0
"""

def calc(wins, ret, total):
    if not total: return 0.0, 0.0
    return wins/total*100, (ret or 0)*100/total

SEP  = "=" * 72
SEP2 = "─" * 60
HAZURE = ('2019','2020','2022')
KOCHO  = ('2017','2018','2021','2023','2024','2025')

print(SEP)
print("【条件4 深掘り分析】新潟×芝×2000m×スタミナ系×10番人気以上")
print(SEP)

# =====================================================================
# 1. 基本プロフィール
# =====================================================================
print("\n■ 基本プロフィール")
cur.execute(f"""
    SELECT COUNT(*) as entries,
           ROUND(AVG(rr.tansho_odds),1) as avg_odds,
           ROUND(AVG(rr.popularity),1) as avg_pop,
           MIN(rr.race_date) as first_date,
           MAX(rr.race_date) as last_date
    {BASE_WHERE}
""")
r = cur.fetchone()
print(f"  期間   : {r['first_date']} 〜 {r['last_date']}")
print(f"  出走数 : {r['entries']:,}頭")
print(f"  平均人気: {r['avg_pop']}番人気  /  平均オッズ: {r['avg_odds']}倍")
print(f"  ※ 距離は全件 2000m（新潟芝2000のみ存在）")

# =====================================================================
# 2. 年別サマリー
# =====================================================================
print("\n■ 年別成績（2017〜2025）")
print(f"  {'年':^5} {'R数':>5} {'勝':>3} {'的中率':>6} {'回収率':>7} {'平均Ods':>7}  良/稍/重/不  判定")
print("  " + SEP2)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec,
           ROUND(AVG(rr.tansho_odds),1) as avg_odds,
           SUM(CASE WHEN rr.track_cond='良' THEN 1 ELSE 0 END) as cnt_ryo,
           SUM(CASE WHEN rr.track_cond='稍' THEN 1 ELSE 0 END) as cnt_ya,
           SUM(CASE WHEN rr.track_cond='重' THEN 1 ELSE 0 END) as cnt_ju,
           SUM(CASE WHEN rr.track_cond='不' THEN 1 ELSE 0 END) as cnt_fu
    {BASE_WHERE}
      AND SUBSTR(rr.race_date,1,4) NOT IN ('2016')
    GROUP BY yr ORDER BY yr
""")
for r in cur.fetchall():
    hr  = r['wins']/r['total']*100 if r['total'] else 0
    rec = r['rec']
    cond_str = f"{r['cnt_ryo']}/{r['cnt_ya']}/{r['cnt_ju']}/{r['cnt_fu']}"
    if   rec >= 150: judge = "◎好調"
    elif rec >= 100: judge = "○良好"
    elif rec >= 70:  judge = "△普通"
    else:            judge = "✕不調"
    print(f"  {r['yr']:^5} {r['total']:>5} {r['wins']:>3} {hr:>5.1f}% {rec:>7.1f}%  "
          f"{r['avg_odds']:>6.1f}倍  {cond_str:^11}  {judge}")

# =====================================================================
# 3. 馬場状態別（全期間）
# =====================================================================
print("\n■ 馬場状態別（全期間）← 福島との比較注目")
print(f"  {'馬場':^4} {'R数':>5} {'構成比':>6} {'勝':>3} {'的中率':>6} {'回収率':>7} {'1着平均Ods':>10}")
print("  " + SEP2)

cur.execute(f"""
    SELECT rr.track_cond,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) as avg_win_odds,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
    GROUP BY rr.track_cond ORDER BY rec DESC
""")
rows = cur.fetchall()
for r in rows:
    hr  = r['wins']/r['total']*100 if r['total'] else 0
    pct = r['total']/765*100
    wo  = f"{r['avg_win_odds']}倍" if r['avg_win_odds'] else "─"
    flag = " ★" if r['rec'] >= 100 else ""
    print(f"  {r['track_cond']:^4} {r['total']:>5} {pct:>5.1f}%  {r['wins']:>3} "
          f"{hr:>5.1f}% {r['rec']:>7.1f}%{flag}  {wo:>10}")

print(f"\n  ▲ 福島との逆転パターン:")
print(f"     福島: 重=240.9% ★ / 稍=13.3% ✕")
print(f"     新潟: 重=  0.0% ✕ / 稍=110.0% ★  ← 同じ「重・稍」でも真逆")
print(f"\n  → 重馬場（20R・0勝）は除外確定。ただし稍重は110%で「残す」判断。")

# =====================================================================
# 4. 月別分布
# =====================================================================
print("\n■ 月別成績（新潟は開催が集中）")
print(f"  {'月':^5} {'R数':>5} {'勝':>3} {'的中率':>6} {'回収率':>7} {'平均Ods':>7}")
print("  " + SEP2)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,6,2) AS month,
           COUNT(*) AS total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) AS wins,
           ROUND(AVG(rr.tansho_odds),1) AS avg_odds,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) AS rec
    {BASE_WHERE}
    GROUP BY month ORDER BY month
""")
month_map = {'04':'4月','05':'5月','07':'7月','08':'8月','09':'9月','10':'10月'}
for r in cur.fetchall():
    hr   = r['wins']/r['total']*100 if r['total'] else 0
    flag = " ★" if r['rec'] >= 100 else (" ✕" if r['rec'] == 0 and r['total'] >= 20 else "")
    print(f"  {month_map.get(r['month'], r['month']):^5} {r['total']:>5} {r['wins']:>3} "
          f"{hr:>5.1f}% {r['rec']:>7.1f}%{flag}  {r['avg_odds']:>6.1f}倍")
print(f"\n  → 4月（0%・39R）・7月（0%・39R）は0勝。開幕週の特性か、除外候補。")

# =====================================================================
# 5. 外れ年 vs 好調年 比較（馬場別）
# =====================================================================
print("\n■ 外れ年 vs 好調年 比較（馬場状態別）")

for label, years in [("外れ年（2019/2020/2022）", HAZURE),
                     ("好調年（2017/18/21/23/24/25）", KOCHO)]:
    yr_in = "','".join(years)
    cur.execute(f"""
        SELECT rr.track_cond,
               COUNT(*) AS total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) AS wins,
               ROUND(AVG(rr.tansho_odds),1) AS avg_field,
               ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) AS avg_win,
               ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) AS rec
        {BASE_WHERE}
          AND SUBSTR(rr.race_date,1,4) IN ('{yr_in}')
        GROUP BY rr.track_cond ORDER BY rec DESC
    """)
    rows = cur.fetchall()
    print(f"\n  [{label}]")
    print(f"  {'馬場':^4} {'R数':>5} {'勝':>3} {'回収率':>7}  フィールド平均Ods  1着平均Ods")
    print("  " + "─" * 58)
    for r in rows:
        wo = f"{r['avg_win']}倍" if r['avg_win'] else "─(0勝)"
        print(f"  {r['track_cond']:^4} {r['total']:>5} {r['wins']:>3} {r['rec']:>7.1f}%  "
              f"{r['avg_field']:>7.1f}倍           {wo}")

print(f"\n  ★ 発見: 外れ年の良馬場1着馬平均オッズ = 32.0倍")
print(f"         好調年の良馬場1着馬平均オッズ = 73.8倍")
print(f"         フィールド平均も外れ年128倍 < 好調年151.7倍")
print(f"  → 福島と同じく「当たっても低倍率」が外れ年の本質。")
print(f"     ただし馬場状態では説明できない（外れ年に重はほぼ存在しない）。")

# =====================================================================
# 6. 馬場フィルター改善効果
# =====================================================================
print("\n■ フィルター別の改善効果比較")

filters = [
    ("元（全馬場）",          "1=1"),
    ("重を除外",              "rr.track_cond != '重'"),
    ("良+稍のみ（重・不除外）", "rr.track_cond IN ('良','稍')"),
    ("良のみ",               "rr.track_cond = '良'"),
]

print(f"  {'フィルター':^22} {'R数':>5} {'勝':>3} {'回収率':>8}")
print("  " + "─" * 46)
for label, where in filters:
    cur.execute(f"""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
        {BASE_WHERE} AND {where}
    """)
    r = cur.fetchone()
    flag = " ★" if r['rec'] >= 120 else ""
    print(f"  {label:^22} {r['total']:>5} {r['wins']:>3} {r['rec']:>7.1f}%{flag}")

# =====================================================================
# 7. 重除外＋4月7月除外での年別安定性
# =====================================================================
print("\n■ 「重を除外・4月7月を除外」フィルター適用後の年別回収率")
cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND rr.track_cond != '重'
      AND SUBSTR(rr.race_date,6,2) NOT IN ('04','07')
      AND SUBSTR(rr.race_date,1,4) NOT IN ('2016')
    GROUP BY yr ORDER BY yr
""")
rows = cur.fetchall()
over100 = sum(1 for r in rows if r['total']>=10 and r['rec']>=100)
valid   = sum(1 for r in rows if r['total']>=10)
total_r = sum(r['total'] for r in rows)
total_w = sum(r['wins']  for r in rows)
total_ret = sum(r['wins'] * 0 for r in rows)  # placeholder

print(f"  {'年':^5} {'R数':>5} {'勝':>3} {'回収率':>8}  判定")
print("  " + "─" * 38)
for r in rows:
    if r['total'] < 10: continue
    if   r['rec'] >= 150: judge = "◎"
    elif r['rec'] >= 100: judge = "○"
    elif r['rec'] >= 70:  judge = "△"
    else:                 judge = "✕"
    flag = " ★" if r['rec'] >= 100 else ""
    print(f"  {r['yr']:^5} {r['total']:>5} {r['wins']:>3} {r['rec']:>7.1f}%{flag}  {judge}")

# 回収率計算
cur.execute(f"""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND rr.track_cond != '重'
      AND SUBSTR(rr.race_date,6,2) NOT IN ('04','07')
      AND SUBSTR(rr.race_date,1,4) NOT IN ('2016')
""")
r = cur.fetchone()
print(f"\n  合計: {r['total']}R / {r['wins']}勝 / 回収率 {r['rec']}%")
print(f"  安定性: {over100}/{valid}年が100%超 ({over100/valid*100:.0f}%)")

# =====================================================================
# 8. 1着馬オッズ分布
# =====================================================================
print("\n■ 1着馬オッズ分布（全馬場）")
cur.execute(f"""
    SELECT
        CASE WHEN rr.tansho_odds <= 30  THEN '〜30倍（低）'
             WHEN rr.tansho_odds <= 60  THEN '31〜60倍'
             WHEN rr.tansho_odds <= 100 THEN '61〜100倍'
             WHEN rr.tansho_odds <= 150 THEN '101〜150倍'
             ELSE '151倍〜（超高）'
        END as band,
        COUNT(*) as wins,
        ROUND(MIN(rr.tansho_odds),1) as min_o,
        ROUND(MAX(rr.tansho_odds),1) as max_o,
        ROUND(AVG(rr.tansho_odds),1) as avg_o
    {BASE_WHERE} AND rr.finish_pos=1
    GROUP BY band ORDER BY MIN(rr.tansho_odds)
""")
print(f"  {'倍率帯':^14} {'勝数':>4}  {'平均':>7}  {'範囲'}")
print("  " + "─" * 44)
for r in cur.fetchall():
    print(f"  {r['band']:^14} {r['wins']:>4}  {r['avg_o']:>6.1f}倍  {r['min_o']}〜{r['max_o']}倍")

# =====================================================================
# 9. 実用判断まとめ（福島と対比）
# =====================================================================
print()
print(SEP)
print("■ 実用判断まとめ（福島ダートとの対比）")
print(SEP)
print("""
【条件の実態】
  ・新潟芝2000m、スタミナ系種牡馬の10番人気以上
  ・全765R / 14勝 / 単勝回収率112.6% / 安定性6/9年（67%）

【福島との決定的な違い：馬場パターンが逆転】
  ┌──────────────────────────────────────────────────┐
  │       │ 福島ダート1700m │ 新潟芝2000m              │
  │  重   │   240.9% ★強   │     0.0% ✕壊滅           │
  │  良   │   133.7% ★     │   113.8% ★               │
  │  稍   │    13.3% ✕壊滅  │   110.0% ★               │
  │  不   │     0.0% ✕      │   193.8% ★（少）         │
  └──────────────────────────────────────────────────┘
  → 重馬場のみ除外。稍重は良好なので残す（福島とは逆）。

【外れ年（2019/2020/2022）の正体：馬場では説明できない】
  ・外れ年に重馬場はほぼ存在しない → 重除外では改善しない
  ・外れ年の良馬場1着馬オッズ：32.0倍（好調年73.8倍）
  ・フィールド平均オッズも外れ年(128倍) < 好調年(151.7倍)
  ・根本原因：「当たっても低倍率」または「0勝」のランダム性
  ・馬場フィルターで外れ年を排除する手段が存在しない

【フィルター改善効果の比較】
  ・重除外のみ       : 745R → 回収率115.6%（わずかな改善）
  ・良+稍のみ        : 721R → 回収率112.6%（不良を除くと逆に下がる）
  ・重+4月+7月除外   : 687R → 安定性67%（元と同水準）
  → どのフィルターを試しても外れ年の本質的な改善はできない

【実用判断: 条件3（福島）より不確実性が高い】
  ┌──────────────────────────────────────────────────┐
  │                    福島ダート        新潟芝         │
  │  回収率            147.8%           115.6%         │
  │  安定性            7/9年（78%）     6/9年（67%）   │
  │  外れ年の原因      馬場状態（明確）  ランダム性     │
  │  フィルター効果    大（+23pt改善）  小（+3pt止まり）│
  │  年間ベット数      130〜200R        60〜90R        │
  └──────────────────────────────────────────────────┘

【推奨運用方針】
  採用はするが「サブ条件」として位置づける

  購入ルール:
    重馬場の日は見送り（0勝・20R）
    4月・7月は見送り（0勝、各39R）
    5月・8月・9月・10月の良/稍/不の日のみ購入

  注意:
    ・年間約65〜90Rで1〜3勝というペース
    ・1勝もできない年（2019・2020残り）が存在し
      これはフィルターで防げない
    ・2018年の1勝（130.1倍）のような高オッズ的中が
      年全体を牽引する構造なので「収支は年単位で見る」
    ・福島ダートほど確度が高くないため投資額は福島の半額以下が無難
""")

conn.close()
print("=== 分析完了 ===")
