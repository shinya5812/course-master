# -*- coding: utf-8 -*-
"""
条件A〜D ウォークフォワード検証（年別成績集計）
"""
import sqlite3
import os
import sys

# エンコード設定
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'course_master.db')

# 各条件の定義
CONDITIONS = [
    {
        'label': '条件A: 中京×ダ×1401〜1800m×マイラー系×7〜9人気',
        'key': 'A',
        'venue': '中京',
        'surface': 'ダ',
        'dist_min': 1401,
        'dist_max': 1800,
        'category': 'マイラー系',
        'pop_min': 7,
        'pop_max': 9,
        'exclude_cond': [],   # 見送り馬場なし
    },
    {
        'label': '条件B: 福島×ダ×1600〜1800m×スタミナ系×10人気以上',
        'key': 'B',
        'venue': '福島',
        'surface': 'ダ',
        'dist_min': 1600,
        'dist_max': 1800,
        'category': 'スタミナ系',
        'pop_min': 10,
        'pop_max': 999,
        'exclude_cond': ['稍重', '不良'],
    },
    {
        'label': '条件C: 新潟×芝×1801〜2100m×スタミナ系×10人気以上',
        'key': 'C',
        'venue': '新潟',
        'surface': '芝',
        'dist_min': 1801,
        'dist_max': 2100,
        'category': 'スタミナ系',
        'pop_min': 10,
        'pop_max': 999,
        'exclude_cond': ['重'],
    },
    {
        'label': '条件D: 中京×芝×1200〜1400m×速力系×7〜9人気',
        'key': 'D',
        'venue': '中京',
        'surface': '芝',
        'dist_min': 1200,
        'dist_max': 1400,
        'category': '速力系',
        'pop_min': 7,
        'pop_max': 9,
        'exclude_cond': ['不良'],
    },
]

def run_condition(conn, cond):
    """1条件の年別集計を返す"""
    where_cond = ""
    if cond['exclude_cond']:
        placeholders = ','.join(['?' for _ in cond['exclude_cond']])
        where_cond = f"AND r.track_cond NOT IN ({placeholders})"

    sql = f"""
    SELECT
        SUBSTR(r.race_date, 1, 4) AS year,
        COUNT(*) AS bets,
        SUM(CASE WHEN r.finish_pos = 1 THEN 1 ELSE 0 END) AS wins,
        ROUND(SUM(CASE WHEN r.finish_pos = 1 THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) AS win_rate,
        ROUND(
            SUM(CASE WHEN r.finish_pos = 1 THEN r.tansho_odds * 100.0 ELSE 0 END) / COUNT(*),
            1
        ) AS recovery
    FROM race_results r
    JOIN blood_category bc ON r.sire_name = bc.sire_name
    WHERE r.venue = ?
      AND r.surface = ?
      AND r.distance >= ?
      AND r.distance <= ?
      AND bc.category = ?
      AND r.popularity >= ?
      AND r.popularity <= ?
      {where_cond}
      AND r.tansho_odds IS NOT NULL
      AND r.tansho_odds > 0
      AND r.finish_pos IS NOT NULL
      AND r.finish_pos > 0
    GROUP BY year
    ORDER BY year
    """

    params = [
        cond['venue'],
        cond['surface'],
        cond['dist_min'],
        cond['dist_max'],
        cond['category'],
        cond['pop_min'],
        cond['pop_max'],
    ] + cond['exclude_cond']

    rows = conn.execute(sql, params).fetchall()
    return rows


def run_condition_total(conn, cond):
    """1条件の全体集計"""
    where_cond = ""
    if cond['exclude_cond']:
        placeholders = ','.join(['?' for _ in cond['exclude_cond']])
        where_cond = f"AND r.track_cond NOT IN ({placeholders})"

    sql = f"""
    SELECT
        COUNT(*) AS bets,
        SUM(CASE WHEN r.finish_pos = 1 THEN 1 ELSE 0 END) AS wins,
        ROUND(SUM(CASE WHEN r.finish_pos = 1 THEN 1.0 ELSE 0 END) / COUNT(*) * 100, 1) AS win_rate,
        ROUND(
            SUM(CASE WHEN r.finish_pos = 1 THEN r.tansho_odds * 100.0 ELSE 0 END) / COUNT(*),
            1
        ) AS recovery
    FROM race_results r
    JOIN blood_category bc ON r.sire_name = bc.sire_name
    WHERE r.venue = ?
      AND r.surface = ?
      AND r.distance >= ?
      AND r.distance <= ?
      AND bc.category = ?
      AND r.popularity >= ?
      AND r.popularity <= ?
      {where_cond}
      AND r.tansho_odds IS NOT NULL
      AND r.tansho_odds > 0
      AND r.finish_pos IS NOT NULL
      AND r.finish_pos > 0
    """

    params = [
        cond['venue'],
        cond['surface'],
        cond['dist_min'],
        cond['dist_max'],
        cond['category'],
        cond['pop_min'],
        cond['pop_max'],
    ] + cond['exclude_cond']

    row = conn.execute(sql, params).fetchone()
    return row


def main():
    conn = sqlite3.connect(DB_PATH)

    summary = []

    for cond in CONDITIONS:
        print(f"\n{'='*70}")
        print(f"【{cond['label']}】")
        if cond['exclude_cond']:
            print(f"  見送り馬場: {', '.join(cond['exclude_cond'])}")
        print(f"{'='*70}")
        print(f"{'年':<6} | {'ベット数':>8} | {'的中数':>6} | {'的中率':>7} | {'単勝回収率':>10}")
        print(f"{'-'*6}-+-{'-'*8}-+-{'-'*6}-+-{'-'*7}-+-{'-'*10}")

        rows = run_condition(conn, cond)

        black_years = 0
        total_years = 0

        for row in rows:
            year, bets, wins, win_rate, recovery = row
            marker = " ★" if recovery >= 100 else ""
            print(f"{year:<6} | {bets:>8,} | {wins:>6,} | {win_rate:>6.1f}% | {recovery:>9.1f}%{marker}")
            if recovery >= 100:
                black_years += 1
            total_years += 1

        total = run_condition_total(conn, cond)
        bets_t, wins_t, win_rate_t, recovery_t = total
        print(f"{'-'*6}-+-{'-'*8}-+-{'-'*6}-+-{'-'*7}-+-{'-'*10}")
        print(f"{'合計':<6} | {bets_t:>8,} | {wins_t:>6,} | {win_rate_t:>6.1f}% | {recovery_t:>9.1f}%")
        print(f"  黒字年: {black_years}/{total_years}年（{round(black_years/total_years*100) if total_years else 0}%）")

        summary.append({
            'key': cond['key'],
            'label': cond['label'],
            'bets': bets_t,
            'wins': wins_t,
            'win_rate': win_rate_t,
            'recovery': recovery_t,
            'black': black_years,
            'total': total_years,
        })

    # 総合サマリー
    print(f"\n\n{'='*80}")
    print("【総合サマリー】")
    print(f"{'='*80}")
    print(f"{'条件':<4} | {'全体ベット数':>12} | {'全体的中率':>10} | {'全体回収率':>10} | {'黒字年/全年'}")
    print(f"{'-'*4}-+-{'-'*12}-+-{'-'*10}-+-{'-'*10}-+-{'-'*12}")
    for s in summary:
        stability = f"{s['black']}/{s['total']}年（{round(s['black']/s['total']*100) if s['total'] else 0}%）"
        print(f"  {s['key']}  | {s['bets']:>12,} | {s['win_rate']:>9.1f}% | {s['recovery']:>9.1f}% | {stability}")

    conn.close()
    print("\n処理完了")


if __name__ == '__main__':
    main()
