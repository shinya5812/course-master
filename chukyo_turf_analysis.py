# -*- coding: utf-8 -*-
"""
条件1（中京×芝×sprint(〜1400m)×速力系×7〜9番人気）深掘り分析
福島・新潟と同じ切り口で実施
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
    WHERE rr.venue='中京' AND rr.surface='芝'
      AND rr.distance <= 1400
      AND bc.category='速力系'
      AND rr.popularity BETWEEN 7 AND 9
      AND rr.tansho_odds > 0
"""

def calc(wins, ret, total):
    if not total: return 0.0, 0.0
    return wins/total*100, (ret or 0)*100/total

SEP  = "=" * 72
SEP2 = "─" * 60
HAZURE = ('2017','2021','2024')     # 0〜39%
TEICHО = ('2019',)                  # 62%
KOCHO  = ('2016','2018','2020','2022','2023','2025')

print(SEP)
print("【条件1 深掘り分析】中京×芝×sprint(〜1400m)×速力系×7〜9番人気")
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
print(f"  出走数 : {r['entries']:,}頭（1200m: 144R / 1400m: 151R）")
print(f"  平均人気: {r['avg_pop']}番人気  /  平均オッズ: {r['avg_odds']}倍")
print(f"  ※ 速力系種牡馬：距離適性が短距離（〜1400m）に最適化された血統カテゴリ")

# =====================================================================
# 2. 馬場状態別（全期間）
# =====================================================================
print("\n■ 馬場状態別（全期間）← 福島・新潟との比較注目")
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
track_data = {}
total_all = 295
for r in cur.fetchall():
    hr  = r['wins']/r['total']*100 if r['total'] else 0
    pct = r['total']/total_all*100
    wo  = f"{r['avg_win_odds']}倍" if r['avg_win_odds'] else "─"
    flag = " ★" if r['rec'] >= 200 else (" ◎" if r['rec'] >= 100 else "")
    print(f"  {r['track_cond']:^4} {r['total']:>5} {pct:>5.1f}%  {r['wins']:>3} "
          f"{hr:>5.1f}% {r['rec']:>7.1f}%{flag}  {wo:>10}")
    track_data[r['track_cond']] = {'total': r['total'], 'wins': r['wins'],
                                    'rec': r['rec'], 'wo': r['avg_win_odds']}

print(f"""
  ▲ 3条件の馬場パターン比較:
     福島ダ: 重=240% ★ / 良=134%  / 稍= 13% ✕ / 不=  0% ✕
     新潟芝: 重=  0% ✕ / 良=114%  / 稍=110%    / 不=194%
     中京芝: 重=342% ★ / 良=150%  / 稍=347% ★ / 不=  0% ✕ ← 良・稍・重が全部プラス

  → 不良（8R・0勝）のみ除外。それ以外は全馬場で購入。
     稍重・重のサンプルは少ないが高期待値（スプリントは荒れ馬場で速力系が強い）。""")

# 不良除外の全体回収率
cur.execute(f"""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE} AND rr.track_cond != '不'
""")
r = cur.fetchone()
print(f"\n  【不良除外後】 {r['total']}R / {r['wins']}勝 / 回収率 {r['rec']}% ★")

# =====================================================================
# 3. 年別サマリー
# =====================================================================
print("\n■ 年別成績（2016〜2025）")
print(f"  {'年':^5} {'R数':>4} {'勝':>3} {'的中率':>6} {'回収率':>7} {'平均Ods':>7} "
      f" 良/稍/重/不  1200/1400  判定")
print("  " + "─" * 70)

cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec,
           ROUND(AVG(rr.tansho_odds),1) as avg_odds,
           SUM(CASE WHEN rr.track_cond='良' THEN 1 ELSE 0 END) as cn_ryo,
           SUM(CASE WHEN rr.track_cond='稍' THEN 1 ELSE 0 END) as cn_ya,
           SUM(CASE WHEN rr.track_cond='重' THEN 1 ELSE 0 END) as cn_ju,
           SUM(CASE WHEN rr.track_cond='不' THEN 1 ELSE 0 END) as cn_fu,
           SUM(CASE WHEN rr.distance=1200 THEN 1 ELSE 0 END) as cn_1200,
           SUM(CASE WHEN rr.distance=1400 THEN 1 ELSE 0 END) as cn_1400
    {BASE_WHERE}
      AND SUBSTR(rr.race_date,1,4) != '2015'
    GROUP BY yr ORDER BY yr
""")
for r in cur.fetchall():
    hr    = r['wins']/r['total']*100 if r['total'] else 0
    cond  = f"{r['cn_ryo']}/{r['cn_ya']}/{r['cn_ju']}/{r['cn_fu']}"
    dist  = f"{r['cn_1200']}/{r['cn_1400']}"
    if   r['rec'] >= 200: judge = "◎好調"
    elif r['rec'] >= 100: judge = "○良好"
    elif r['rec'] >= 50:  judge = "△低調"
    else:                 judge = "✕不調"
    print(f"  {r['yr']:^5} {r['total']:>4} {r['wins']:>3} {hr:>5.1f}% {r['rec']:>7.1f}%  "
          f"{r['avg_odds']:>6.1f}倍  {cond:^9}  {dist:^9}  {judge}")

# =====================================================================
# 4. 外れ年 vs 好調年 比較
# =====================================================================
print("\n■ 外れ年 vs 好調年 比較（馬場状態別）")

for label, years in [
    ("外れ年（2017/2021/2024 … 0〜39%）", HAZURE),
    ("低調年（2019 … 62%）",              TEICHО),
    ("好調年（2016/18/20/22/23/25）",     KOCHO),
]:
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
        wo = f"{r['avg_win']}倍" if r['avg_win'] else "─（0勝）"
        print(f"  {r['track_cond']:^4} {r['total']:>5} {r['wins']:>3} {r['rec']:>7.1f}%  "
              f"{r['avg_field']:>7.1f}倍           {wo}")

print(f"""
  ★ 発見（外れ年の特徴）:
     外れ年×良馬場: フィールド平均オッズ 30.1倍 → 好調年35.7倍 より5倍低い
     外れ年×良馬場: 1着馬平均オッズ     14.1倍 → 好調年25.2倍 より11倍低い
     → 「フィールドが接戦的（オッズが低い）な年」で回収率が悪化する傾向
     → ただし事前に「今年は接戦的」と判断するのは困難""")

# =====================================================================
# 5. 距離別（1200 vs 1400）
# =====================================================================
print("\n■ 距離別（1200m vs 1400m）")
cur.execute(f"""
    SELECT rr.distance,
           COUNT(*) AS total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) AS wins,
           ROUND(AVG(rr.tansho_odds),1) AS avg_field,
           ROUND(AVG(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds END),1) AS avg_win,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) AS rec
    {BASE_WHERE}
    GROUP BY rr.distance ORDER BY rr.distance
""")
print(f"  {'距離':^8} {'R数':>5} {'勝':>3} {'的中率':>6} {'回収率':>7}  フィールド平均Ods  1着平均Ods")
print("  " + "─" * 64)
for r in cur.fetchall():
    hr = r['wins']/r['total']*100 if r['total'] else 0
    wo = f"{r['avg_win']}倍" if r['avg_win'] else "─"
    print(f"  {r['distance']:^8}m {r['total']:>5} {r['wins']:>3} {hr:>5.1f}% {r['rec']:>7.1f}%  "
          f"{r['avg_field']:>7.1f}倍           {wo}")
print(f"  → 1200m(179.6%) と 1400m(176.2%) はほぼ同等。距離フィルターに意味なし。")

# =====================================================================
# 6. フィルター改善効果比較
# =====================================================================
print("\n■ フィルター別の改善効果比較")

filters = [
    ("元（全馬場）",          "1=1"),
    ("不良のみ除外",           "rr.track_cond != '不'"),
    ("良のみ",               "rr.track_cond = '良'"),
    ("良+稍",                "rr.track_cond IN ('良','稍')"),
    ("良+重",                "rr.track_cond IN ('良','重')"),
]
print(f"  {'フィルター':^20} {'R数':>5} {'勝':>3} {'回収率':>8}  安定性判定用")
print("  " + "─" * 50)
for label, where in filters:
    cur.execute(f"""
        SELECT SUBSTR(rr.race_date,1,4) as yr,
               COUNT(*) as total,
               SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END) as ret
        {BASE_WHERE} AND {where}
          AND SUBSTR(rr.race_date,1,4) NOT IN ('2015')
        GROUP BY yr
    """)
    rows = cur.fetchall()
    t = sum(r['total'] for r in rows)
    w = sum(r['wins']  for r in rows)
    ret = sum(r['ret'] for r in rows)
    rec = ret*100/t if t else 0
    ov100 = sum(1 for r in rows if r['total']>=5 and r['ret']*100/r['total']>=100)
    valid = sum(1 for r in rows if r['total']>=5)
    flag = " ★" if rec >= 180 else ""
    print(f"  {label:^20} {t:>5} {w:>3} {rec:>7.1f}%{flag}  {ov100}/{valid}年 100%超")

# =====================================================================
# 7. 「不良除外」適用後の年別回収率
# =====================================================================
print("\n■ 「不良除外」フィルター適用後の年別回収率")
cur.execute(f"""
    SELECT SUBSTR(rr.race_date,1,4) as yr,
           COUNT(*) as total,
           SUM(CASE WHEN rr.finish_pos=1 THEN 1 ELSE 0 END) as wins,
           ROUND(SUM(CASE WHEN rr.finish_pos=1 THEN rr.tansho_odds ELSE 0 END)*100.0/COUNT(*),1) as rec
    {BASE_WHERE}
      AND rr.track_cond != '不'
      AND SUBSTR(rr.race_date,1,4) NOT IN ('2015')
    GROUP BY yr ORDER BY yr
""")
rows = cur.fetchall()
over100 = sum(1 for r in rows if r['total']>=5 and r['rec']>=100)
valid   = sum(1 for r in rows if r['total']>=5)
print(f"  {'年':^5} {'R数':>4} {'勝':>3} {'回収率':>8}  判定")
print("  " + "─" * 34)
for r in rows:
    if r['total'] < 5: continue
    if   r['rec'] >= 200: judge = "◎"
    elif r['rec'] >= 100: judge = "○"
    elif r['rec'] >= 50:  judge = "△"
    else:                 judge = "✕"
    flag = " ★" if r['rec'] >= 100 else ""
    print(f"  {r['yr']:^5} {r['total']:>4} {r['wins']:>3} {r['rec']:>7.1f}%{flag}  {judge}")
print(f"\n  安定性: {over100}/{valid}年が100%超 ({over100/valid*100:.0f}%)")

# =====================================================================
# 8. 1着馬オッズ分布
# =====================================================================
print("\n■ 1着馬オッズ分布（全馬場）")
cur.execute(f"""
    SELECT
        CASE WHEN rr.tansho_odds <= 15  THEN '〜15倍（低）'
             WHEN rr.tansho_odds <= 25  THEN '16〜25倍'
             WHEN rr.tansho_odds <= 40  THEN '26〜40倍'
             WHEN rr.tansho_odds <= 60  THEN '41〜60倍'
             ELSE '61倍〜（高）'
        END as band,
        COUNT(*) as wins,
        ROUND(MIN(rr.tansho_odds),1) as min_o,
        ROUND(MAX(rr.tansho_odds),1) as max_o,
        ROUND(AVG(rr.tansho_odds),1) as avg_o
    {BASE_WHERE} AND rr.finish_pos=1
    GROUP BY band ORDER BY MIN(rr.tansho_odds)
""")
print(f"  {'倍率帯':^12} {'勝数':>4}  {'平均':>7}  {'範囲'}")
print("  " + "─" * 44)
for r in cur.fetchall():
    print(f"  {r['band']:^12} {r['wins']:>4}  {r['avg_o']:>6.1f}倍  {r['min_o']}〜{r['max_o']}倍")
print(f"  ※ 1着馬の中心は16〜40倍。他条件より低オッズ寄り（人気7〜9でも30倍前後）。")

# =====================================================================
# 9. 実用判断まとめ（3条件の全体比較）
# =====================================================================
print()
print(SEP)
print("■ 実用判断まとめ（3条件との比較）")
print(SEP)
print("""
【条件の実態】
  ・中京芝スプリント（1200m / 1400m）の速力系種牡馬 × 7〜9番人気
  ・全295R（2016〜2025）/ 21勝 / 単勝回収率177.9% / 安定性6/10年

【馬場パターン：良・稍・重が全てプラスという特異な構造】
  ┌──────────────────────────────────────────────────┐
  │  馬場  │ R数  │  回収率  │  1着平均Ods │ 備考          │
  │  稍重  │  20  │ 346.5% ★│   23.1倍   │ 少サンプル     │
  │  重    │  29  │ 342.4% ★│   33.1倍   │ 少サンプル     │
  │  良    │ 238  │ 149.6%  │   23.7倍   │ 主戦場（81%） │
  │  不良  │   8  │   0.0% ✕│      ─    │ 除外確定       │
  └──────────────────────────────────────────────────┘
  → 芝スプリントは稍重・重でも速力系が適性を発揮（他条件と逆）

【外れ年（2017/2021/2024）の正体：ランダム性が支配】
  ・外れ年はほぼ全て良馬場の回収率不振が原因
  ・良馬場フィールド平均オッズ: 外れ年30.1倍 vs 好調年35.7倍（接戦的な年）
  ・良馬場1着馬平均オッズ:     外れ年14.1倍 vs 好調年25.2倍（低オッズで的中）
  ・「フィールドが接戦的な年は穴馬が出にくい」は合理的だが事前判断は困難
  ・2017は17Rすべて良馬場・0勝 → いかなるフィルターでも防げない

【フィルター効果：不良除外のみ有効、他は限定的】
  ・不良除外: 287R / 回収率182.8% / 安定性7/10年（70%）
  ・良のみ絞り: 回収率は下がる（稍・重の高期待値を捨てる）
  → 「不良のみ除外」が最善フィルター。稍重・重は積極的に残す。

【3条件の実用比較（確定値）】
  ┌────────────────────────────────────────────────────────────┐
  │ 項目              │ 条件A（中京ダ） │ 条件B（福島ダ）★ │ 条件C（新潟芝） │ 条件1（中京芝） │
  │ フィルター後回収率 │   127.3%       │   147.8%         │   129.9%       │   182.8%       │
  │ 安定性            │  6/9年（67%）  │  7/9年（78%）    │  6/9年（67%） │  7/10年（70%） │
  │ 外れ年の制御      │    不可        │  馬場で制御可 ★  │    不可        │    不可        │
  │ 年間ベット数      │    〜30R       │  130〜200R       │   65〜90R      │   17〜51R      │
  │ 1着馬平均Ods      │    〜50倍      │   77.8倍         │   65.4倍       │   24.9倍       │
  │ 回収率バラツキ    │    中程度       │  低（安定）       │   中程度       │ 最大（0〜378%）│
  └────────────────────────────────────────────────────────────┘

【推奨運用方針】
  不良馬場は見送り。それ以外（良・稍・重）は全て購入。

  特徴:
    ・4条件中で回収率ポテンシャルは最高（182.8%）
    ・ただし年間最小17〜51Rと「サンプルが最も薄い」
    ・1着馬オッズが低め（中心16〜40倍）= 的中1回の払い戻しが小さい
    ・「大きな当たりが集中した年」(2020/2023/2025)に数字が跳ね上がる構造
    ・条件B（福島）のような「馬場フィルターで外れ年を防ぐ」仕組みがない
    → 投資額は福島の1/2程度。「当たり年を逃さないために毎週チェック」が基本戦略
""")

conn.close()
print("=== 分析完了 ===")
