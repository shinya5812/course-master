"""
rebuild_pkl.py
build_statistics() → save() でpklを再生成するスクリプト
完了後、sire_dist_stats / bms_dist_stats の収録を確認する

[2026-04-10] CSVパスを data/race/ / data/pedigree/ に更新
"""
import os
import sys
import io
import pickle
import shutil
from datetime import datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
RACE_DIR  = os.path.join(BASE_DIR, 'data', 'race')
PED_DIR   = os.path.join(BASE_DIR, 'data', 'pedigree')

# ファイルパス設定
RESULT_FILES = [
    os.path.join(RACE_DIR, '2015_2016結果.csv'),
    os.path.join(RACE_DIR, '2017_2018結果.csv'),
    os.path.join(RACE_DIR, '2019_2020結果.csv'),
    os.path.join(RACE_DIR, '2021_2023結果.csv'),
    os.path.join(RACE_DIR, '2024_2026結果.csv'),
    os.path.join(RACE_DIR, '2026結果.csv'),
    os.path.join(RACE_DIR, '202602280331結果.csv'),
    os.path.join(RACE_DIR, '結果202603070405.csv'),
    os.path.join(RACE_DIR, '結果202604110419.csv'),
    os.path.join(RACE_DIR, '結果202604250510.csv'),
]
BLOOD_FILE  = os.path.join(PED_DIR, '血統_0513.csv')
PKL_PATH    = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BACKUP_PATH = os.path.join(BASE_DIR, f'course_master_v70_engine_backup_{datetime.now().strftime("%Y%m%d")}.pkl')

# ─── Step 1: 既存pklをバックアップ ───
print("=" * 60)
print("Step 1: 既存pklをバックアップ")
if os.path.exists(PKL_PATH):
    shutil.copy2(PKL_PATH, BACKUP_PATH)
    print(f"  [OK] backup: {os.path.basename(BACKUP_PATH)}")
else:
    print("  [NOTE] pkl not found (will create new)")

# ─── Step 2: エンジン初期化 & データ読み込み ───
print("\nStep 2: エンジン初期化 & データ読み込み")
from course_master_v73_engine import CourseMASTERv73
engine = CourseMASTERv73()
engine.load_data(RESULT_FILES, BLOOD_FILE)

# ─── Step 3: 統計構築 ───
print("\nStep 3: build_statistics() 実行")
engine.build_statistics()

# ─── Step 4: pkl保存 ───
print("\nStep 4: save() 実行")
engine.save(PKL_PATH)

# ─── Step 5: 収録確認 ───
print("\n" + "=" * 60)
print("Step 5: 収録確認（pklを再ロードして検証）")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

keys_check = ['sire_dist_stats', 'bms_dist_stats', 'blood_category_map', 'course_stats']
for key in keys_check:
    val = state.get(key, None)
    if val is None:
        print(f"  [NG] {key}: not found")
    else:
        print(f"  [OK] {key}: {len(val)} items")

# sire_dist_stats の中身サンプル確認
sds = state.get('sire_dist_stats', {})
if sds:
    sample_sire = next(iter(sds))
    print(f"\n  [sire_dist_stats サンプル] '{sample_sire}': {sds[sample_sire]}")

# bms_dist_stats の中身サンプル確認
bds = state.get('bms_dist_stats', {})
if bds:
    sample_bms = next(iter(bds))
    print(f"  [bms_dist_stats サンプル]  '{sample_bms}': {bds[sample_bms]}")

# 距離帯別キー充填率確認
dist_keys = ['sprint_wr', 'mile_wr', 'middle_wr', 'long_wr']
print(f"\n  [sire_dist_stats 距離帯別充填率]")
for dk in dist_keys:
    count = sum(1 for v in sds.values() if v.get(dk) is not None)
    print(f"    {dk}: {count}/{len(sds)} 件 ({count/len(sds)*100:.1f}%)" if sds else f"    {dk}: 0件")

print("\n" + "=" * 60)
print("pkl rebuild & verify: DONE")
print(f"   pkl: {PKL_PATH}")
print(f"   backup: {BACKUP_PATH}")
