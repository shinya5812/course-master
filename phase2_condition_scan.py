# -*- coding: utf-8 -*-
"""
Phase 2 条件スキャン
全会場×全芝ダ×全距離帯×全血統カテゴリ×人気帯の組み合わせをスキャンし、
有望条件（200R以上・単勝回収率110%以上・安定性60%以上）を抽出する。

安定性定義:
  対象年のうち「10R以上かつ回収率100%超」の年が60%以上であること。
  ※ 2015・2026は部分年のため対象年に含むが、10R未満は除外。
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

# ---- 定数 ----
MIN_SAMPLES   = 200    # 最低サンプル数
MIN_RECOVERY  = 110.0  # 最低回収率 (%)
STABILITY_PCT = 0.60   # 安定性: 有効年の何割が100%超か
MIN_YR_SAMPLE = 10     # 年別安定性チェックの最低サンプル数

# ベンチマーク（中京×ダ×マイル×マイラー系×7〜9番人気: 127.3%）
BENCHMARK_LABEL = "中京×ダ×mile×マイラー系×7〜9人気"
BENCHMARK_RATE  = 127.3

# 距離帯区分
DIST_CASE = """
    CASE
        WHEN rr.distance <= 1400           THEN 'sprint(〜1400)'
        WHEN rr.distance BETWEEN 1401 AND 1800 THEN 'mile(1401〜1800)'
        WHEN rr.distance BETWEEN 1801 AND 2100 THEN 'middle(1801〜2100)'
        ELSE                                    'long(2101〜)'
    END
"""

# 人気帯区分
POP_CASE = """
    CASE
        WHEN rr.popularity BETWEEN 4 AND 6 THEN '4〜6人気'
        WHEN rr.popularity BETWEEN 7 AND 9 THEN '7〜9人気'
        ELSE                                    '10人気以上'
    END
"""

def calc(wins, return_sum, total):
    if not total:
        return 0.0, 0.0
    return wins / total * 100, (return_sum or 0) * 100 / total

# =====================================================================
# Phase 1: 全組み合わせスキャン
# =====================================================================
print("スキャン中... (最大960組み合わせ)")

cur.execute(f"""
    SELECT
        rr.venue,
        rr.surface,
        {DIST_CASE}   AS dist_band,
        bc.category   AS sire_cat,
        {POP_CASE}    AS pop_band,
        COUNT(*)      AS total,
        SUM(CASE WHEN rr.finish_pos = 1 THEN 1 ELSE 0 END)           AS wins,
        SUM(CASE WHEN rr.finish_pos = 1 THEN rr.tansho_odds ELSE 0 END) AS return_sum
    FROM race_results rr
    INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
    WHERE rr.tansho_odds > 0
      AND rr.popularity >= 4
    GROUP BY rr.venue, rr.surface, dist_band, bc.category, pop_band
    HAVING total >= {MIN_SAMPLES}
    ORDER BY (COALESCE(return_sum, 0) * 100.0 / total) DESC
""")

candidates = cur.fetchall()
print(f"  → {len(candidates)}件が{MIN_SAMPLES}R以上")

# =====================================================================
# Phase 2: 回収率フィルター
# =====================================================================
over_110 = []
for r in candidates:
    hr, rec = calc(r['wins'], r['return_sum'], r['total'])
    if rec >= MIN_RECOVERY:
        over_110.append({
            'venue':    r['venue'],
            'surface':  r['surface'],
            'dist_band':r['dist_band'],
            'sire_cat': r['sire_cat'],
            'pop_band': r['pop_band'],
            'total':    r['total'],
            'wins':     r['wins'],
            'return_sum': r['return_sum'],
            'hit_rate': hr,
            'recovery': rec,
        })

print(f"  → {len(over_110)}件が回収率{MIN_RECOVERY}%以上")

# =====================================================================
# Phase 3: 年別安定性チェック
# =====================================================================
def yearly_stats(venue, surface, dist_band, sire_cat, pop_band):
    """指定条件の年別 (年, R数, 的中率, 回収率) を返す"""
    # dist_band → distance条件に逆変換
    if dist_band == 'sprint(〜1400)':
        dist_where = "rr.distance <= 1400"
    elif dist_band == 'mile(1401〜1800)':
        dist_where = "rr.distance BETWEEN 1401 AND 1800"
    elif dist_band == 'middle(1801〜2100)':
        dist_where = "rr.distance BETWEEN 1801 AND 2100"
    else:
        dist_where = "rr.distance >= 2101"

    # pop_band → popularity条件に逆変換
    if pop_band == '4〜6人気':
        pop_where = "rr.popularity BETWEEN 4 AND 6"
    elif pop_band == '7〜9人気':
        pop_where = "rr.popularity BETWEEN 7 AND 9"
    else:
        pop_where = "rr.popularity >= 10"

    cur.execute(f"""
        SELECT
            SUBSTR(rr.race_date, 1, 4) AS yr,
            COUNT(*) AS total,
            SUM(CASE WHEN rr.finish_pos = 1 THEN 1 ELSE 0 END)              AS wins,
            SUM(CASE WHEN rr.finish_pos = 1 THEN rr.tansho_odds ELSE 0 END) AS return_sum
        FROM race_results rr
        INNER JOIN blood_category bc ON rr.sire_name = bc.sire_name
        WHERE rr.venue    = ?
          AND rr.surface  = ?
          AND {dist_where}
          AND bc.category = ?
          AND {pop_where}
          AND rr.tansho_odds > 0
        GROUP BY yr
        ORDER BY yr
    """, (venue, surface, sire_cat))
    return cur.fetchall()

stable = []
for cond in over_110:
    rows = yearly_stats(
        cond['venue'], cond['surface'],
        cond['dist_band'], cond['sire_cat'], cond['pop_band']
    )
    # 有効年: MIN_YR_SAMPLE R 以上の年のみ
    valid_years = [(r['yr'], r['total'], r['wins'], r['return_sum'])
                   for r in rows if r['total'] >= MIN_YR_SAMPLE]
    total_valid = len(valid_years)
    if total_valid == 0:
        continue
    over100_yrs = [(yr, t, w, rs) for yr, t, w, rs in valid_years
                   if (rs or 0) * 100 / t >= 100.0]
    stability = len(over100_yrs) / total_valid

    cond['yearly']        = valid_years
    cond['valid_yrs']     = total_valid
    cond['over100_yrs']   = len(over100_yrs)
    cond['stability']     = stability

    if stability >= STABILITY_PCT:
        stable.append(cond)

print(f"  → {len(stable)}件が安定性{int(STABILITY_PCT*100)}%以上")

# =====================================================================
# Phase 4: 出力
# =====================================================================
print()
print("=" * 90)
print("【Phase 2 スキャン結果】有望条件一覧")
print(f"  抽出条件: {MIN_SAMPLES}R以上 / 回収率{MIN_RECOVERY}%以上 / "
      f"安定性{int(STABILITY_PCT*100)}%以上")
print(f"  ベンチマーク: {BENCHMARK_LABEL} = {BENCHMARK_RATE}%")
print("=" * 90)

if not stable:
    print("\n  該当条件なし（条件を緩めて再実行してください）")
else:
    # 回収率降順にソート
    stable.sort(key=lambda x: x['recovery'], reverse=True)

    for i, c in enumerate(stable, 1):
        above = c['recovery'] > BENCHMARK_RATE
        star  = " ★ベンチマーク超え" if above else ""
        label = f"{c['venue']}×{c['surface']}×{c['dist_band']}×{c['sire_cat']}×{c['pop_band']}"
        print(f"\n{i:>2}. {label}{star}")
        print(f"    サンプル: {c['total']:,}R  |  的中率: {c['hit_rate']:.1f}%  |  "
              f"回収率: {c['recovery']:.1f}%  |  "
              f"安定性: {c['over100_yrs']}/{c['valid_yrs']}年 ({c['stability']*100:.0f}%)")

        # 年別内訳
        print(f"    {'年':^6} {'R数':>5} {'的中率':>7} {'回収率':>8}")
        print(f"    {'─'*34}")
        for yr, total, wins, return_sum in c['yearly']:
            hr, rec = calc(wins, return_sum, total)
            flag = " ◎" if rec >= 100 else "  "
            print(f"    {yr:^6} {total:>5,} {hr:>6.1f}% {rec:>7.1f}%{flag}")

# =====================================================================
# Phase 5: サマリー（110%以上・安定性未達の条件も参考表示）
# =====================================================================
unstable = [c for c in over_110 if c not in stable]
if unstable:
    unstable.sort(key=lambda x: x['recovery'], reverse=True)
    print()
    print("=" * 90)
    print("【参考】回収率110%以上だが安定性未達の条件（不安定・過学習注意）")
    print("=" * 90)
    print(f"  {'会場×芝ダ×距離帯×血統×人気帯':<45} {'R数':>6}  {'的中率':>6}  {'回収率':>7}  {'安定性':>8}")
    print("  " + "─" * 82)
    for c in unstable[:20]:  # 上位20件のみ
        label = f"{c['venue']}×{c['surface']}×{c['dist_band']}×{c['sire_cat']}×{c['pop_band']}"
        stab  = c.get('stability', 0)
        ov    = c.get('over100_yrs', 0)
        vyr   = c.get('valid_yrs', 0)
        above = " ★" if c['recovery'] > BENCHMARK_RATE else ""
        print(f"  {label:<45} {c['total']:>6,}  {c['hit_rate']:>6.1f}%  "
              f"{c['recovery']:>7.1f}%  {ov}/{vyr}年{above}")

conn.close()
print("\n=== 完了 ===")
