# -*- coding: utf-8 -*-
"""
scripts/agent_result_checker.py - 結果照合エージェント

candidates_{date}.json と condition_bet_history を照合して
日次 P&L を算出し pnl_{date}.json を生成する。
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import date as dt_date, datetime

# Windows環境での日本語出力
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')

BET_UNIT = 100


def main():
    parser = argparse.ArgumentParser(description='結果照合エージェント')
    parser.add_argument('--date', default=dt_date.today().isoformat(),
                        help='対象日（YYYY-MM-DD）')
    args = parser.parse_args()
    target_date = args.date

    date_nodash     = target_date.replace('-', '')
    candidates_path = os.path.join(BASE_DIR, f'candidates_{date_nodash}.json')
    output_path     = os.path.join(BASE_DIR, f'pnl_{date_nodash}.json')

    print(f'[result_checker] 開始 date={target_date}')

    if not os.path.exists(candidates_path):
        result = {'date': target_date, 'error': 'candidates not found', 'bets': [], 'summary': {}}
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'[result_checker] candidates が見つかりません: {candidates_path}')
        sys.exit(0)

    with open(candidates_path, encoding='utf-8') as f:
        cands = json.load(f)

    venue      = cands.get('venue', '')
    candidates = cands.get('candidates', [])

    if not candidates:
        output = {
            'date': target_date, 'venue': venue, 'bets': [],
            'summary': {'total_bets': 0, 'total_invested': 0, 'total_returned': 0,
                        'net_pnl': 0, 'roi': 0.0, 'win_count': 0},
            'generated_at': datetime.now().isoformat(timespec='seconds'),
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print('[result_checker] 購入候補ゼロ → 空レポート生成')
        return

    # condition_bet_history から対象日・会場を取得
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("""
        SELECT race_no, horse_no, horse_name, condition_type, tansho_odds, result
        FROM condition_bet_history
        WHERE race_date = ? AND venue = ?
    """, (target_date, venue))
    db_rows = {(r['race_no'], r['horse_name']): dict(r) for r in cur.fetchall()}
    con.close()

    bets = []
    for c in candidates:
        race_no, horse_no, horse_name, condition, est_odds = c
        key = (race_no, horse_name)
        db_rec = db_rows.get(key)

        if db_rec:
            result    = db_rec['result']
            act_odds  = db_rec['tansho_odds']
            returned  = int(act_odds * BET_UNIT) if result == '的中' else 0
        else:
            result   = '未照合'
            act_odds = est_odds
            returned = 0

        bets.append({
            'race_no':   race_no,
            'horse_no':  horse_no,
            'horse_name': horse_name,
            'condition': condition,
            'est_odds':  est_odds,
            'act_odds':  act_odds,
            'result':    result,
            'returned':  returned,
            'pnl':       returned - BET_UNIT,
        })

    total_invested = len(bets) * BET_UNIT
    total_returned = sum(b['returned'] for b in bets)
    win_count      = sum(1 for b in bets if b['result'] == '的中')
    roi            = round(total_returned / total_invested * 100, 1) if total_invested > 0 else 0.0

    output = {
        'date':    target_date,
        'venue':   venue,
        'bets':    bets,
        'summary': {
            'total_bets':     len(bets),
            'total_invested': total_invested,
            'total_returned': total_returned,
            'net_pnl':        total_returned - total_invested,
            'roi':            roi,
            'win_count':      win_count,
        },
        'generated_at': datetime.now().isoformat(timespec='seconds'),
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[result_checker] 完了 → {output_path}')
    print(f'  投資: {total_invested}円 / 払戻: {total_returned}円 / ROI: {roi}% / 的中: {win_count}件')


if __name__ == '__main__':
    main()
