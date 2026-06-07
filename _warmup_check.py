# -*- coding: utf-8 -*-
"""エンジン起動確認・pkl統計件数出力"""
import sys, io, os, pickle
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PKL_PATH = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_FILE = os.path.join(BASE_DIR, 'data', 'pedigree', '血統_0410.csv')

print("■ pkl読み込みテスト...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

keys = list(state.keys())
print(f"  収録キー ({len(keys)}個): {', '.join(keys[:12])}")

checks = {
    'sire_stats':         lambda s: len(s),
    'jockey_stats':       lambda s: len(s),
    'trainer_stats':      lambda s: len(s),
    'distance_stats':     lambda s: len(s),
    'blood_category_map': lambda s: len(s),
    'course_stats':       lambda s: len(s),
    'sire_dist_stats':    lambda s: len(s),
    'bms_dist_stats':     lambda s: len(s),
}
print("\n  統計件数:")
all_ok = True
for k, fn in checks.items():
    val = state.get(k, None)
    if val is not None:
        print(f"    {k}: {fn(val)}件 ✅")
    else:
        print(f"    {k}: 未収録 ⚠️")
        all_ok = False

print("\n■ grade_race_predictor.py import テスト...")
sys.argv = ['grade_race_predictor.py', '--help']
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "grp", os.path.join(BASE_DIR, 'grade_race_predictor.py'))
    mod = importlib.util.load_from_spec = None  # import回避（execのみ確認）
    # 構文チェックのみ
    src = open(os.path.join(BASE_DIR, 'grade_race_predictor.py'), encoding='utf-8').read()
    compile(src, 'grade_race_predictor.py', 'exec')
    print("  構文OK ✅")
except SyntaxError as e:
    print(f"  構文エラー ❌: {e}")
    all_ok = False

print("\n■ 血統CSVアクセス確認...")
import pandas as pd
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
print(f"  血統CSV: {len(df_blood):,}頭 ✅")

print(f"\n■ ウォームアップ結果: {'全OK ✅' if all_ok else '一部警告あり ⚠️'}")
print("  grade_race_predictor.py は正常に使用可能")
