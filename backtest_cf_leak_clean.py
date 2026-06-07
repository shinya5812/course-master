# -*- coding: utf-8 -*-
"""
backtest_cf_leak_clean.py
CF軸リーク排除（アプローチC）効果測定

3条件を比較出力する:
  条件A: 全期間・リーク込み     (PKL全期間統計 + blood_dict CF)
  条件B: JT/SPD分離済み         (時系列分離統計 + blood_dict CF)
  条件C: CF軸も分離             (時系列分離統計 + horse_stats CF)

テスト期間: 2022〜2026年 Grade (G1/G2/G3) 10頭以上
"""

import sys
import io
import os
import re
import pickle

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RACE_DIR   = os.path.join(BASE_DIR, 'data', 'race')
PED_DIR    = os.path.join(BASE_DIR, 'data', 'pedigree')
PKL_PATH   = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_FILE = os.path.join(PED_DIR, '20260217血統.csv')

CSV_FILES = [
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

GRADE_PATTERN = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')

sys.path.insert(0, BASE_DIR)
from backtest_utils import get_stats_for_race, score_horse_v73


def detect_grade(race_name):
    if not race_name:
        return None
    m = GRADE_PATTERN.search(str(race_name))
    if not m:
        return None
    g = m.group()
    if g[-1] in ('Ⅰ', '1', '１'):
        return 'G1'
    if g[-1] in ('Ⅱ', '2', '２'):
        return 'G2'
    if g[-1] in ('Ⅲ', '3', '３'):
        return 'G3'
    return None


# ============================================================
# 1. データ読み込み
# ============================================================
print("■ CSVデータ読み込み中...")
dfs = []
for f in CSV_FILES:
    if os.path.exists(f):
        df = pd.read_csv(f, encoding='cp932', low_memory=False)
        dfs.append(df)
df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}件")

df_all['確定着順']           = pd.to_numeric(df_all['確定着順'], errors='coerce').fillna(0).astype(int)
df_all['人気順']             = pd.to_numeric(df_all['人気順'], errors='coerce').fillna(0).astype(int)
df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'], errors='coerce')
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'], errors='coerce').fillna(0)
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
df_all['距離']               = pd.to_numeric(df_all['距離'], errors='coerce').fillna(0).astype(int)
df_all['年']                 = pd.to_numeric(df_all['年'], errors='coerce').fillna(0).astype(int)
df_all['年4']                = df_all['年'].apply(lambda y: 2000 + y if 0 < y < 100 else y)
for col in ['通過順1', '通過順2', '通過順3', '通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

print("\n■ 血統データ読み込み中...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)

blood_dict = {}
for _, brow in df_blood.iterrows():
    name = str(brow.get('馬名', '') or '').strip()
    if not name:
        continue
    total_r = int(brow['全成績1着数'] + brow['全成績2着数'] +
                  brow['全成績3着数'] + brow['全成績着外数'])
    total_w = int(brow['全成績1着数'])
    blood_dict[name] = (total_r, total_w)
print(f"  血統CSV馬名辞書: {len(blood_dict):,}件")

# ============================================================
# 2. PKL（条件A用）統計をロード
# ============================================================
print("\n■ PKL 読み込み中（条件A用・全期間統計）...")
pkl_stats = None
if os.path.exists(PKL_PATH):
    with open(PKL_PATH, 'rb') as f:
        pkl = pickle.load(f)
    pkl_stats = {
        'jockey_stats':   pkl.get('jockey_stats', {}),
        'distance_stats': pkl.get('distance_stats', {}),
    }
    print(f"  PKL 騎手件数: {len(pkl_stats['jockey_stats'])} "
          f"距離件数: {len(pkl_stats['distance_stats'])}")
else:
    print("  ⚠ PKL が見つかりません → 条件A比較をスキップします")

# ============================================================
# 3. テスト対象絞り込み
# ============================================================
df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None
)
test_df = df_all[(df_all['年4'] >= 2022) & (df_all['grade'].notna())].copy()
test_df['race_key'] = (
    test_df['年4'].astype(str) + '_' +
    test_df['月'].astype(str).str.zfill(2) + '_' +
    test_df['日'].astype(str).str.zfill(2) + '_' +
    test_df['場所'].astype(str) + '_' +
    test_df['日次'].astype(str) + '_' +
    test_df['レース番号'].astype(str).str.zfill(2)
)
test_df = test_df.drop_duplicates(subset=['race_key', '馬名'])
print(f"\n■ テスト対象: {len(test_df.groupby('race_key'))}R (2022-2026 Grade, 10頭フィルター前)")

# ============================================================
# 4. バックテスト（3条件）
# ============================================================
print("■ バックテスト実行中...")

results = []
race_groups = list(test_df.groupby('race_key'))
total_rg    = len(race_groups)

for i, (rk, rdf) in enumerate(race_groups):
    if i % 200 == 0:
        print(f"  進捗: {i}/{total_rg}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 10:
        continue

    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_1st  = str(winner_rows.iloc[0]['馬名']).strip()
    actual_top3 = {str(h).strip() for h in valid[valid['確定着順'] <= 3]['馬名']}

    pop1_rows  = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None

    meta      = valid.iloc[0]
    year4     = int(meta['年4'])
    month     = int(meta['月'])
    day       = int(meta['日'])
    grade     = str(meta['grade'])
    race_date = f"{year4:04d}-{month:02d}-{day:02d}"

    # 時系列分離済み統計（条件B / 条件C 共通）
    sep_stats = get_stats_for_race(race_date)

    scores_a, scores_b, scores_c = {}, {}, {}
    for idx, row in valid.iterrows():
        try:
            # 条件A: PKL全期間統計 + blood_dict CF
            if pkl_stats:
                scores_a[idx] = score_horse_v73(row, pkl_stats, blood_dict, use_horse_stats=False)
            # 条件B: 時系列分離統計 + blood_dict CF
            scores_b[idx] = score_horse_v73(row, sep_stats, blood_dict, use_horse_stats=False)
            # 条件C: 時系列分離統計 + horse_stats CF
            scores_c[idx] = score_horse_v73(row, sep_stats, blood_dict, use_horse_stats=True)
        except Exception:
            scores_a[idx] = 50.0
            scores_b[idx] = 50.0
            scores_c[idx] = 50.0

    if not scores_c:
        continue

    def best_horse(scores, valid_df):
        if not scores:
            return '', 0.0
        idx = max(scores, key=scores.get)
        return str(valid_df.loc[idx, '馬名']).strip(), float(valid_df.loc[idx, '単勝オッズ_num'] or 0)

    pred_a, odds_a = best_horse(scores_a, valid)
    pred_b, odds_b = best_horse(scores_b, valid)
    pred_c, odds_c = best_horse(scores_c, valid)

    results.append({
        'race_key':   rk,
        'grade':      grade,
        'year':       year4,
        'n_horses':   len(valid),
        'actual_1st': actual_1st,
        'pop1_horse': pop1_horse,
        # 条件A
        'pred_a':    pred_a,
        'hit_a':     pred_a == actual_1st,
        'place_a':   pred_a in actual_top3,
        'odds_a':    odds_a,
        # 条件B
        'pred_b':    pred_b,
        'hit_b':     pred_b == actual_1st,
        'place_b':   pred_b in actual_top3,
        'odds_b':    odds_b,
        # 条件C
        'pred_c':    pred_c,
        'hit_c':     pred_c == actual_1st,
        'place_c':   pred_c in actual_top3,
        'odds_c':    odds_c,
        # 1番人気
        'pop1_hit': pop1_horse == actual_1st if pop1_horse else False,
    })

print(f"  完了: 有効レース数 {len(results)}R (10頭以上)")

# ============================================================
# 5. 集計・比較表出力
# ============================================================
df_res  = pd.DataFrame(results)
total_R = len(df_res)


def calc_roi(df_sub, hit_col, odds_col):
    n = len(df_sub)
    if n == 0:
        return 0.0
    paid_out = (df_sub[hit_col] * df_sub[odds_col] * 100).sum()
    return float(paid_out / (n * 100) * 100)


pop1_hit = int(df_res['pop1_hit'].sum())

print("\n" + "=" * 80)
print("  重賞バックテスト 3条件比較（backtest_cf_leak_clean.py）")
print("=" * 80)
print(f"  テスト期間: 2022〜2026年 / 対象レース: {total_R}R（10頭以上 Grade）")
print(f"  条件A: PKL全期間統計 + blood_dict CF（全リーク込み）")
print(f"  条件B: 時系列分離統計 + blood_dict CF（JT/SPD分離・CF未分離）")
print(f"  条件C: 時系列分離統計 + horse_stats CF（全軸リーク排除）")
print()

ha = int(df_res['hit_a'].sum())
hb = int(df_res['hit_b'].sum())
hc = int(df_res['hit_c'].sum())
pa = int(df_res['place_a'].sum())
pb = int(df_res['place_b'].sum())
pc = int(df_res['place_c'].sum())
roi_a = calc_roi(df_res, 'hit_a', 'odds_a')
roi_b = calc_roi(df_res, 'hit_b', 'odds_b')
roi_c = calc_roi(df_res, 'hit_c', 'odds_c')

print(f"  {'指標':<22} {'条件A（全リーク）':>14} {'条件B（JT/SPD分離）':>16} {'条件C（全軸分離）':>14} {'B→C差':>8}")
print(f"  {'─' * 78}")
print(f"  {'◎的中率（単勝）':<22} {ha/total_R*100:>12.2f}%  {hb/total_R*100:>14.2f}%  {hc/total_R*100:>12.2f}%  {(hb-hc)/total_R*100:>+6.2f}%")
print(f"  {'◎複勝率（3着以内）':<22} {pa/total_R*100:>12.2f}%  {pb/total_R*100:>14.2f}%  {pc/total_R*100:>12.2f}%  {(pb-pc)/total_R*100:>+6.2f}%")
print(f"  {'単勝ROI（100円）':<22} {roi_a:>12.1f}%  {roi_b:>14.1f}%  {roi_c:>12.1f}%  {roi_b-roi_c:>+6.1f}%")
print(f"  {'1番人気的中率':<22} {pop1_hit/total_R*100:>12.2f}%  {'（基準）':>14}  {'（基準）':>12}  {'—':>8}")

print(f"\n  ─ グレード別（条件C）─")
print(f"  {'G':<4} {'R':>5} {'A的中%':>8} {'B的中%':>8} {'C的中%':>8} {'B→C差':>7} {'A ROI%':>8} {'B ROI%':>8} {'C ROI%':>8}")
for g in ['G1', 'G2', 'G3']:
    sub = df_res[df_res['grade'] == g]
    n   = len(sub)
    if n == 0:
        continue
    ha_ = sub['hit_a'].sum()
    hb_ = sub['hit_b'].sum()
    hc_ = sub['hit_c'].sum()
    ra  = calc_roi(sub, 'hit_a', 'odds_a')
    rb  = calc_roi(sub, 'hit_b', 'odds_b')
    rc  = calc_roi(sub, 'hit_c', 'odds_c')
    print(f"  {g:<4} {n:>5} {ha_/n*100:>7.1f}% {hb_/n*100:>7.1f}% {hc_/n*100:>7.1f}% "
          f"{(hb_-hc_)/n*100:>+6.1f}% {ra:>7.1f}% {rb:>7.1f}% {rc:>7.1f}%")

print(f"\n  ─ 年別（条件C）─")
print(f"  {'年':>5} {'R':>5} {'A的中%':>8} {'B的中%':>8} {'C的中%':>8} {'B→C差':>7} {'使用cutoff':>10}")
for yr in sorted(df_res['year'].unique()):
    sub    = df_res[df_res['year'] == yr]
    n      = len(sub)
    ha_    = sub['hit_a'].sum()
    hb_    = sub['hit_b'].sum()
    hc_    = sub['hit_c'].sum()
    cutoff = {2022: 2021, 2023: 2022, 2024: 2023}.get(yr, 2024)
    print(f"  {yr:>5} {n:>5} {ha_/n*100:>7.1f}% {hb_/n*100:>7.1f}% {hc_/n*100:>7.1f}% "
          f"{(hb_-hc_)/n*100:>+6.1f}%    ≤{cutoff}")

# 条件B vs 条件C で ◎選出が変わったレースの内訳
diff_bc = df_res[df_res['pred_b'] != df_res['pred_c']]
if len(diff_bc) > 0:
    hit_b_only = int((diff_bc['hit_b'] & ~diff_bc['hit_c']).sum())
    hit_c_only = int((~diff_bc['hit_b'] & diff_bc['hit_c']).sum())
    hit_both   = int((diff_bc['hit_b'] & diff_bc['hit_c']).sum())
    print(f"\n  ─ 条件B vs 条件Cで◎選出が異なるレース ({len(diff_bc)}R) ─")
    print(f"    B的中・C外れ: {hit_b_only}R / "
          f"C的中・B外れ: {hit_c_only}R / "
          f"両方外れ: {len(diff_bc)-hit_b_only-hit_c_only-hit_both}R")

print()
print("  [解釈のポイント]")
print("  ・A→B差: JT/SPD軸のリーク量（統計的過大評価）")
print("  ・B→C差: CF軸のリーク量（血統CSVスナップショット由来）")
print("  ・条件CのROI > 100% → CF軸リーク排除後も実質プラスエッジが残存")
print("  ・条件Cの数値が真のバックテスト精度の推定値（最保守的）")

print("\n■ 完了")
