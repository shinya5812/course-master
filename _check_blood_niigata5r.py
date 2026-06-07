# -*- coding: utf-8 -*-
import pickle, os, sys
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
pkl_path = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')

with open(pkl_path, 'rb') as f:
    data = pickle.load(f)

bc_map = data.get('blood_category_map', {})

# 新潟5R 10番人気以上の父馬リスト
sires_to_check = {
    1:  ('ウインブリザード', 'ゴールドシップ', 11, 24.1),
    3:  ('ゼータレティクル', 'ビーチパトロール', 10, 21.4),
    5:  ('ショウナンパステル', 'ショウナンバッハ', 16, 102.5),
    6:  ('マイネルアルゴー', 'スクリーンヒーロー', 14, 46.8),
    8:  ('ヴォンサクレ', 'アルアイン', 13, 38.1),
    9:  ('ジージージェット', 'モズアスコット', 12, 26.2),
    11: ('ミョンソクコムドリ', 'ストーミーシー', 15, 92.9),
}

print("=== 新潟5R 条件Cフィルター（10番人気以上） ===")
print(f"{'馬番':4} {'馬名':18} {'父馬':16} {'人気':4} {'オッズ':7} {'血統カテゴリ':12} {'対象'}")
print("-"*70)

candidates = []
for bnum, (horse, sire, pop, odds) in sorted(sires_to_check.items()):
    cat = bc_map.get(sire, 'unknown')
    is_target = (cat == 'スタミナ系')
    mark = '★購入' if is_target else '-'
    print(f"{bnum:4} {horse:18} {sire:16} {pop:4} {odds:7.1f} {cat:12} {mark}")
    if is_target:
        candidates.append((bnum, horse, sire, pop, odds))

print()
print(f"=== スタミナ系該当馬: {len(candidates)}頭 ===")
for bnum, horse, sire, pop, odds in candidates:
    print(f"  馬番{bnum} {horse} (父:{sire}) {pop}人気 {odds}倍")
