# -*- coding: utf-8 -*-
"""
build_jockey_course_stats.py
jockey_specialtyテーブルから騎手×場所×距離帯の相性係数JSONを生成する。

出力: output/jockey_course_stats.json
キー形式: "{騎手名}|{場所}|{芝/ダ}|{dist_cat}"
係数: lift（該当勝率 / 全体平均勝率）を 0.5〜2.0 にクリップ
条件: rides >= 20 かつ venue・dist_cat が not null のみ採用
"""

import os
import sys
import io
import json
import sqlite3

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')
OUT_DIR  = os.path.join(BASE_DIR, 'output')
OUT_PATH = os.path.join(OUT_DIR, 'jockey_course_stats.json')

MIN_RIDES    = 20
LIFT_MIN     = 0.5
LIFT_MAX     = 2.0

os.makedirs(OUT_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    SELECT
        jockey,
        json_extract(keys_json, '$.venue')     AS venue,
        json_extract(keys_json, '$.surface')   AS surface,
        json_extract(keys_json, '$.dist_cat')  AS dist_cat,
        lift,
        win_rate,
        rides
    FROM jockey_specialty
    WHERE rides >= ?
      AND json_extract(keys_json, '$.dist_cat') IS NOT NULL
      AND json_extract(keys_json, '$.venue')    IS NOT NULL
""", (MIN_RIDES,))

rows = cursor.fetchall()
conn.close()

stats = {}
skipped = 0
for jockey, venue, surface, dist_cat, lift, win_rate, rides in rows:
    if not jockey or not venue or not surface or not dist_cat:
        skipped += 1
        continue
    clipped = max(LIFT_MIN, min(LIFT_MAX, lift))
    key = f"{jockey}|{venue}|{surface}|{dist_cat}"
    stats[key] = {
        'lift':     clipped,
        'raw_lift': round(lift, 4),
        'win_rate': round(win_rate, 2),
        'rides':    rides,
    }

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)

print(f"jockey_course_stats.json 生成完了")
print(f"  有効エントリー: {len(stats):,}件 (rides>={MIN_RIDES}, lift={LIFT_MIN}〜{LIFT_MAX})")
print(f"  スキップ      : {skipped}件")
print(f"  保存先        : {OUT_PATH}")

# 集計サマリー
lift_vals = [v['raw_lift'] for v in stats.values()]
import statistics
print(f"\n  lift 統計: min={min(lift_vals):.3f} max={max(lift_vals):.3f} "
      f"mean={statistics.mean(lift_vals):.3f} median={statistics.median(lift_vals):.3f}")
clipped_count = sum(1 for v in lift_vals if v < LIFT_MIN or v > LIFT_MAX)
print(f"  クリップ適用: {clipped_count}件 (上限2.0超 or 下限0.5未満)")

dist_cnt = {}
for k in stats:
    dc = k.split('|')[3]
    dist_cnt[dc] = dist_cnt.get(dc, 0) + 1
print(f"  距離帯別件数: {dist_cnt}")
