# -*- coding: utf-8 -*-
"""
_test_g2_longdist.py
G2×2201m以上ベット保留ルールの verify テスト

ケース1: G2 × 2400m → ⚠G2長距離保留 が表示されること
ケース2: G1 × 2400m → 通常判定のまま（⚠は表示されない）
ケース3: G3 × 2400m → 通常判定のまま（⚠は表示されない）
ケース4: G2 × 2000m → 通常判定のまま（⚠は表示されない）
"""

import sys
import io
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from grade_race_predictor import detect_grade, calc_chaos_index, print_result

# 共通の馬データ（シンプル・12頭）
def make_horses(n=12):
    return [
        {'horse_no': i+1, 'horse_name': f'テスト馬{i+1:02d}', 'jockey': '武豊',
         'sire': 'ディープインパクト', 'dam_sire': 'キングカメハメハ',
         'age': 5, 'weight': 57.0,
         'popularity': i+1, 'odds': round(2.0 * (i+1), 1)}
        for i in range(n)
    ]

CASES = [
    {'race_name': '目黒記念 GⅡ', 'venue': '東京', 'surface': '芝',
     'distance': 2500, 'track_cond': '良', 'class_code': 800,
     'expected_warning': True,  'label': 'ケース1: G2×2500m → ⚠保留'},
    {'race_name': '天皇賞（春） GⅠ', 'venue': '京都', 'surface': '芝',
     'distance': 3200, 'track_cond': '良', 'class_code': 800,
     'expected_warning': False, 'label': 'ケース2: G1×3200m → 通常'},
    {'race_name': '新潟大賞典 GⅢ', 'venue': '新潟', 'surface': '芝',
     'distance': 2000, 'track_cond': '良', 'class_code': 800,
     'expected_warning': False, 'label': 'ケース3: G3×2000m → 通常'},
    {'race_name': '毎日杯 GⅡ', 'venue': '阪神', 'surface': '芝',
     'distance': 1800, 'track_cond': '良', 'class_code': 800,
     'expected_warning': False, 'label': 'ケース4: G2×1800m → 通常'},
    {'race_name': '目黒記念 GⅡ', 'venue': '東京', 'surface': '芝',
     'distance': 2201, 'track_cond': '良', 'class_code': 800,
     'expected_warning': True,  'label': 'ケース5: G2×2201m（境界）→ ⚠保留'},
    {'race_name': '目黒記念 GⅡ', 'venue': '東京', 'surface': '芝',
     'distance': 2200, 'track_cond': '良', 'class_code': 800,
     'expected_warning': False, 'label': 'ケース6: G2×2200m（境界未満）→ 通常'},
]


def fake_prediction(n=12):
    """print_result に渡せる最小の prediction dict"""
    entries = []
    for i in range(n):
        entries.append((i, f'テスト馬{i+1:02d}', 60.0 - i, 0.10 - i*0.005, +0.08 - i*0.01))
    result = {
        'all': entries,
        '◎': [(e[1], e[2], e[3], e[0], e[4]) for e in entries[:1]],
        '○': [(e[1], e[2], e[3], e[0], e[4]) for e in entries[1:4]],
        '▲': [(e[1], e[2], e[3], e[0], e[4]) for e in entries[4:9]],
    }
    return result


print("=" * 70)
print("  G2×2201m以上ベット保留ルール verify テスト")
print("=" * 70)

all_pass = True
for case in CASES:
    race = dict(case)
    expected = race.pop('expected_warning')
    label    = race.pop('label')
    race['horses'] = make_horses(12)

    grade    = detect_grade(race['race_name']) or '重賞'
    distance = int(race.get('distance', 0))
    is_g2_ld = (grade == 'G2') and (distance >= 2201)

    # 出力をキャプチャ
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        chaos = calc_chaos_index(race)
        pred  = fake_prediction(12)
        print_result(race, pred, chaos)
    except Exception as e:
        sys.stdout = old_stdout
        print(f"  {label}")
        print(f"    ERROR: {e}")
        all_pass = False
        continue
    sys.stdout = old_stdout
    output = buf.getvalue()

    # 判定
    has_warning    = '⚠G2長距離保留' in output or 'G2長距離・ベット保留' in output
    passed         = has_warning == expected
    all_pass       = all_pass and passed
    status         = '✓ PASS' if passed else '✗ FAIL'

    print(f"  {status}  {label}")
    print(f"         grade={grade}  dist={distance}m  is_g2_ld={is_g2_ld}")
    print(f"         ⚠表示: {has_warning}  期待値: {expected}")
    print()

print("=" * 70)
print(f"  結果: {'全PASS ✓' if all_pass else '一部FAIL ✗ ← 要修正'}")
print("=" * 70)
sys.exit(0 if all_pass else 1)
