# -*- coding: utf-8 -*-
"""
add_horse_stats_to_cutoffs.py
CF軸リーク排除（アプローチC）—— horse_stats フィールドを stats_cutoff_*.json に追加する

各カットオフ時点（2021/2022/2023/2024年末）での馬別キャリア統計を
race_results テーブルから集計して stats_cutoff_*.json に追記する。

追加フィールド:
  {
    "horse_stats": {
      "馬名": {
        "total_races": X,
        "total_wins":  X,
        "win_rate":    X.XXXX,
        "place_rate":  X.XXXX
      },
      ...
    }
  }

注意:
  - 既存の PKL / cm_stats_v72.json は一切上書きしない
  - 本番予測（prediction_app.py）には影響を与えない
"""

import sys
import io
import os
import json
import sqlite3

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, 'course_master.db')
STATS_DIR = os.path.join(BASE_DIR, 'stats')

CUTOFF_YEARS = [2021, 2022, 2023, 2024]

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

for cy in CUTOFF_YEARS:
    cutoff_date = f'{cy}-12-31'
    stats_path  = os.path.join(STATS_DIR, f'stats_cutoff_{cy}.json')

    if not os.path.exists(stats_path):
        print(f'  ⚠ {stats_path} が見つかりません → スキップ')
        continue

    print(f'\n■ カットオフ {cy}年末 ({cutoff_date}) を集計中...')

    cur.execute('''
        SELECT TRIM(horse_name)                                          AS horse,
               COUNT(*)                                                  AS total_races,
               SUM(CASE WHEN finish_pos = 1 THEN 1 ELSE 0 END)         AS total_wins,
               SUM(CASE WHEN finish_pos <= 3 THEN 1 ELSE 0 END)        AS total_top3
        FROM   race_results
        WHERE  race_date <= ?
          AND  finish_pos > 0
        GROUP  BY TRIM(horse_name)
    ''', (cutoff_date,))

    horse_stats = {}
    for horse, total_races, total_wins, total_top3 in cur.fetchall():
        if not horse or total_races == 0:
            continue
        horse_stats[horse] = {
            'total_races': int(total_races),
            'total_wins':  int(total_wins),
            'win_rate':    round(total_wins  / total_races, 4),
            'place_rate':  round(total_top3  / total_races, 4),
        }

    print(f'  集計件数: {len(horse_stats):,}頭')

    with open(stats_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    data['horse_stats'] = horse_stats

    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f'  → {stats_path} に horse_stats ({len(horse_stats):,}頭) を追加しました')

conn.close()
print('\n■ 全カットオフの horse_stats 追加完了')
