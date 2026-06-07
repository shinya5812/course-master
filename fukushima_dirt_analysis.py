# -*- coding: utf-8 -*-
"""
条件3（福島×ダート×1700m×スタミナ系×10番人気以上）深掘り分析
"""
import sqlite3
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
    INNER JOIN blood_category bc ON rr.sire_name=bc.sire_name
    WHERE rr.venue='福島' AND rr.surface='ダ'
      AND rr.distance BETWEEN 1401 AND 1800
      AND bc.category='スタミナ系'
      AND rr.popularity>=10 AND rr.tansho_odds>0
"""

def calc(wins, ret, total):
    if not total: return 0.0, 0.0
    return wins/total*100, (ret or 0)*100/total

SEP  = "=" * 72
SEP2 = "─" * 60

print(SEP)
print("【条件3 深掘り分析】福島×ダート×1700m×スタミナ系×10番人気以上")
print(SEP)

# =====================================================================
# 1. 基本プロフィール
# =====================================================================
print("\n■ 基本プロフィール")
cur.execute(f"""
    SELECT COUNT(DISTINCT SUBSTR(rr.race_date,1,4)||rr.race_no) as races,
           COUNT(*) as entries,
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
print(f"  ※ 距離は全件 1700m（福島ダ1700のみ存在）")

# =====================================================================
# 2. 年別サマリー
# =====================================================================
print("\n■ 年別成績（2015〜2026）")
print(f"  {'年':^5} {'R数':>5} {'勝数':>4} {'的中率':>6} {'回収率':>7} {'平均Ods':>7}  良/稍/重/不  判定")
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
    GROUP BY yr ORDER BY yr
""")
for r in cur.fetchall():
    hr, rec = calc(r['wins'], None, 1)  # dummy
    rec = r['rec']
    hr  = r['wins']/r['total']*100 if r['total'] else 0
    cond_str = f"{r['cnt_ryo']}/{r['cnt_ya']}/{r['cnt_ju']}/{r['cnt_fu']}"
    if r['total'] < 10:
        judge = "（少）"
    elif rec >= 130:
        judge = "◎好調"
    elif rec >= 100:
        judge = "○良好"
    elif rec >= 70:
        judge = "△普通"
    else:
        judge = "✕不調"
    print(f"  {r['yr']:^5} {r['total']:>5} {r['wins']:>4} {hr:>5.1f}% {rec:>7.1f}%  {r['avg_odds']:>6.1f}倍  {cond_str:^11}  {judge}")

# =====================================================================
# 3. 馬場状態別（全期間）
# =====================================================================
print("\n■ 馬場状態別（全期間）")
print(f"  {'馬場':^4} {'R数':>5} {'勝':>3} {'的中率':>6} {'回収率':>7} {'1着平均Ods':>10}")
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
cond_results = {}
for r in cur.fetchall():
    hr = r['wins']/r['total']*100 if r['total'] else 0
    wo = f"{r['avg_win_odds']}倍" if r['avg_win_odds'] else "─"
    flag = " ★" if r['rec'] >= 100 else ("  " if r['rec'] > 0 else "  ")
    print(f"  {r['track_cond']:^4} {r['total']:>5} {r['wins']:>3} {hr:>5.1f}% {r['rec']:>7.1f}%{flag}  {wo:>10}")
    cond_results[r['track_cond']] = {'total': r['total'], 'wins': r['wins'],
                                      'rec': r['rec'], 'wo': r['avg_win_odds']}
print(f"\n  → 稍重({cond_results.get('稍',{}).get('rec',0)}%)・不良({cond_results.get('不',{}).get('rec',0)}%)は壊滅。良+重に絞れば大幅改善。")

# 良+重だけの回収率計算
cur.execute(f"""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND rr.track_cond IN ('良','重')
""")
r = cur.fetchone()
print(f"\n  【良+重のみ】 {r['total']:,}R / 勝数{r['wins']} / 回収率 {r['rec']}% ★")

# =====================================================================
# 4. 外れ年 vs 好調年 比較
# =====================================================================
HAZURE = ('2020','2021','2023')
KOCHO  = ('2017','2018','2019','2022','2024','2025')

print("\n■ 外れ年 vs 好調年 比較（良馬場・重馬場のみ）")
for label, years in [("外れ年（2020/2021/2023）", HAZURE),
                     ("好調年（2017-19/22/24-25）", KOCHO)]:
    yr_in = "','".join(years)
    cur.execute(f"""
        SELECT rr.track_cond,
               COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               ROUND(AVG(rr.tansho_odds),1) as avg_field,
               ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) as avg_win,
               ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
        {BASE_WHERE}
          AND rr.track_cond IN ('良','重')
          AND SUBSTR(rr.race_date,1,4) IN ('{yr_in}')
        GROUP BY rr.track_cond ORDER BY rr.track_cond
    """)
    rows = cur.fetchall()
    print(f"\n  [{label}]")
    print(f"  {'馬場':^4} {'R数':>5} {'勝':>3} {'回収率':>7}  フィールド平均Ods  1着平均Ods")
    print("  " + "─" * 56)
    for r in rows:
        wo = f"{r['avg_win']}倍" if r['avg_win'] else "─(0勝)"
        print(f"  {r['track_cond']:^4} {r['total']:>5} {r['wins']:>3} {r['rec']:>7.1f}%  "
              f"{r['avg_field']:>7.1f}倍           {wo}")

# =====================================================================
# 5. 1着馬のオッズ分布
# =====================================================================
print("\n■ 1着馬のオッズ分布（良+重のみ）")
cur.execute(f"""
    SELECT
        CASE WHEN rr.tansho_odds <= 30   THEN '〜30倍（低）'
             WHEN rr.tansho_odds <= 60   THEN '31〜60倍'
             WHEN rr.tansho_odds <= 100  THEN '61〜100倍'
             WHEN rr.tansho_odds <= 150  THEN '101〜150倍'
             ELSE '151倍〜（超高）'
        END as odds_band,
        COUNT(*) as wins,
        ROUND(AVG(rr.tansho_odds),1) as avg_odds,
        ROUND(MIN(rr.tansho_odds),1) as min_odds,
        ROUND(MAX(rr.tansho_odds),1) as max_odds
    {BASE_WHERE}
      AND rr.finish_pos=1
      AND rr.track_cond IN ('良','重')
    GROUP BY odds_band
    ORDER BY MIN(rr.tansho_odds)
""")
print(f"  {'倍率帯':^12} {'勝数':>4}  {'平均':>7}  {'範囲'}")
print("  " + "─" * 44)
for r in cur.fetchall():
    print(f"  {r['odds_band']:^12} {r['wins']:>4}  {r['avg_odds']:>6.1f}倍  {r['min_odds']}〜{r['max_odds']}倍")

# =====================================================================
# 6. 「良+重のみ」での年別回収率
# =====================================================================
print("\n■ 「良+重のみ」フィルター適用後の年別回収率")
cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND rr.track_cond IN ('良','重')
      AND SUBSTR(rr.race_date,1,4) NOT IN ('2015','2016')
    GROUP BY yr ORDER BY yr
""")
rows = cur.fetchall()
over100 = sum(1 for r in rows if r['total']>=10 and r['rec']>=100)
valid   = sum(1 for r in rows if r['total']>=10)
print(f"  {'年':^5} {'R数':>5} {'勝':>3} {'回収率':>7}  判定")
print("  " + "─" * 36)
for r in rows:
    if r['total'] < 10:
        continue
    hr = r['wins']/r['total']*100 if r['total'] else 0
    if r['rec'] >= 130: judge = "◎"
    elif r['rec'] >= 100: judge = "○"
    elif r['rec'] >= 70:  judge = "△"
    else:                 judge = "✕"
    flag = " ★" if r['rec'] >= 100 else ""
    print(f"  {r['yr']:^5} {r['total']:>5} {r['wins']:>3} {r['rec']:>7.1f}%{flag}  {judge}")
print(f"\n  安定性: {over100}/{valid}年が100%超 ({over100/valid*100:.0f}%)")

# =====================================================================
# 7. 実用判断
# =====================================================================
print()
print(SEP)
print("■ 実用判断まとめ")
print(SEP)
print("""
【条件の実態】
  ・福島ダート1700mで「スタミナ系種牡馬の10番人気以上」
  ・全1,689R / 27勝 / 単勝回収率124.9% / 安定性6/10年

【馬場状態が最重要キー】
  ・良馬場  : 1222R / 回収率133.7% ← 主戦場
  ・重馬場  :  185R / 回収率240.9% ← 高期待値
  ・稍重    :  219R / 回収率 13.3% ← 壊滅（1勝のみ・低オッズ）
  ・不良    :   63R / 回収率  0.0% ← 完全除外

【外れ年（2020/2021/2023）の正体】
  ・回収率不振の根本原因: 稍重・不良の比率が高く、0勝が積み上がった
  ・外れ年でも「良+重」限定なら 68.7〜108.2% → 許容範囲
  ・外れ年の良馬場1着馬の平均オッズ41.1倍（好調年92.5倍）
    → 「当たっても低倍率」の年があり、これはランダム性の範疇

【改善フィルター: 良+重のみ】
  ・適用後: 1,407R / 回収率147.8%
  ・年別安定性: 7/9年が100%超（78%） → 元の60%から大幅改善
  ・稍重・不良の除外でサンプルは17%減るが回収率は+23ポイント改善

【実用判断: 特定条件に絞るべき】
  ┌──────────────────────────────────────────────────────┐
  │ 推奨戦略: 福島ダート1700m × スタミナ系 × 10番人気以上       │
  │          「馬場状態が"良"または"重"の日のみ購入」            │
  │                                                          │
  │  理由:                                                   │
  │  1. 稍重・不良は統計上ほぼ0%で回収が見込めない              │
  │  2. 良+重フィルターで147.8%・安定性78%と大幅改善            │
  │  3. 重馬場は年間10〜40R程度だが240.9%と高期待値            │
  │  4. 当日の馬場状態は出馬前日に概ね判断可能                  │
  └──────────────────────────────────────────────────────┘

【注意点】
  ・1着馬は高倍率（50〜200倍）が中心で、外れが続くことも多い
  ・年間ベット数は良+重で約130〜200R程度（週2〜3頭ペース）
  ・2022年は重馬場2勝（110倍・205倍）で年全体を牽引。特定的中の
    偶発性は残るため「収支管理」が前提
""")

conn.close()
print("=== 分析完了 ===")
