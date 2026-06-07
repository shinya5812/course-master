# -*- coding: utf-8 -*-
"""
scripts/agent_analyst.py - 分析エージェント

condition_bet_history テーブルから期間・条件種別ごとの
ROI・的中率・収支を集計して analysis_{date}.json を生成する。
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import date as dt_date, datetime, timedelta
from collections import defaultdict

# Windows環境での日本語出力
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')

BET_UNIT = 100  # 1頭あたりのベット金額（円）


def aggregate(rows):
    """行リストから bets/wins/invested/returned/roi/win_rate を集計する。"""
    bets     = len(rows)
    wins     = sum(1 for r in rows if r['result'] == '的中')
    invested = bets * BET_UNIT
    returned = sum(int(r['tansho_odds'] * BET_UNIT) for r in rows if r['result'] == '的中')
    roi      = round(returned / invested * 100, 1) if invested > 0 else 0.0
    win_rate = round(wins / bets, 4) if bets > 0 else 0.0
    net_pnl  = returned - invested
    return {
        'bets':     bets,
        'wins':     wins,
        'invested': invested,
        'returned': returned,
        'net_pnl':  net_pnl,
        'roi':      roi,
        'win_rate': win_rate,
    }


def main():
    parser = argparse.ArgumentParser(description='分析エージェント')
    parser.add_argument('--date', default=dt_date.today().isoformat(),
                        help='基準日（YYYY-MM-DD）')
    parser.add_argument('--period', type=int, default=0,
                        help='遡り日数（0=全期間）')
    parser.add_argument('--grade', default='ALL',
                        help='対象条件種別（A/B/C/D/ALL）')
    args = parser.parse_args()

    target_date = args.date
    output_path = os.path.join(BASE_DIR, f'analysis_{target_date}.json')

    print(f'[analyst] 開始 date={target_date} period={args.period}日 grade={args.grade}')

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # 期間フィルター
    if args.period > 0:
        since = (datetime.fromisoformat(target_date) - timedelta(days=args.period)).date().isoformat()
        cur.execute("""
            SELECT race_date, venue, race_no, horse_name, condition_type,
                   tansho_odds, result
            FROM condition_bet_history
            WHERE race_date >= ? AND race_date <= ?
        """, (since, target_date))
        period_label = f'直近{args.period}日'
    else:
        cur.execute("""
            SELECT race_date, venue, race_no, horse_name, condition_type,
                   tansho_odds, result
            FROM condition_bet_history
            WHERE race_date <= ?
        """, (target_date,))
        period_label = '全期間'

    all_rows = [dict(r) for r in cur.fetchall()]
    con.close()

    if args.grade != 'ALL':
        all_rows = [r for r in all_rows if r['condition_type'] == args.grade]

    print(f'[analyst] 対象レコード数: {len(all_rows)}件')

    # 全体集計
    total = aggregate(all_rows)

    # 条件種別ごと集計
    by_cond = defaultdict(list)
    for r in all_rows:
        by_cond[r['condition_type']].append(r)

    by_condition = {}
    for cond in sorted(by_cond.keys()):
        by_condition[cond] = aggregate(by_cond[cond])

    # 月次集計
    by_month = defaultdict(list)
    for r in all_rows:
        month_key = r['race_date'][:7]  # YYYY-MM
        by_month[month_key].append(r)

    monthly = []
    for month in sorted(by_month.keys()):
        m = aggregate(by_month[month])
        m['month'] = month
        monthly.append(m)

    # 会場別集計
    by_venue = defaultdict(list)
    for r in all_rows:
        by_venue[r['venue']].append(r)

    by_venue_out = {}
    for v in sorted(by_venue.keys()):
        by_venue_out[v] = aggregate(by_venue[v])

    # 直近5回の結果（最新順）
    recent = sorted(all_rows, key=lambda r: (r['race_date'], r['race_no']), reverse=True)[:5]
    recent_out = [
        {
            'race_date':      r['race_date'],
            'venue':          r['venue'],
            'race_no':        r['race_no'],
            'horse_name':     r['horse_name'],
            'condition_type': r['condition_type'],
            'tansho_odds':    r['tansho_odds'],
            'result':         r['result'],
        }
        for r in recent
    ]

    output = {
        'date':         target_date,
        'period':       period_label,
        'grade_filter': args.grade,
        'total':        total,
        'by_condition': by_condition,
        'monthly':      monthly,
        'by_venue':     by_venue_out,
        'recent':       recent_out,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[analyst] 完了 → {output_path}')
    print(f'  総ベット: {total["bets"]}件 / 的中: {total["wins"]}件 / ROI: {total["roi"]}%')


if __name__ == '__main__':
    main()
