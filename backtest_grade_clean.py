# -*- coding: utf-8 -*-
"""
backtest_grade_clean.py
時系列分離統計を用いた重賞バックテスト（修正版）

backtest_grade_races.py を改良し、get_stats_for_race() で
レース年に応じた統計を選択することで未来データ混入を排除する。

テスト期間: 2022〜2026年 Grade (G1/G2/G3) 10頭以上
  2022年 → stats_cutoff_2021（訓練:〜2021）
  2023年 → stats_cutoff_2022（訓練:〜2022）
  2024年 → stats_cutoff_2023（訓練:〜2023）
  2025年以降 → stats_cutoff_2024（訓練:〜2024）

出力: 修正前（PKL 全期間統計）vs 修正後（時系列分離統計）の比較表
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

# backtest_utils から ルーター・スコア計算をインポート
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

# 数値化
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

# 血統CSV lookup 辞書（CF 軸用・両条件共通）
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
# 2. PKL（修正前）の統計をロード
# ============================================================
print("\n■ PKL 読み込み中（修正前・全期間統計）...")
before_stats = None
if os.path.exists(PKL_PATH):
    with open(PKL_PATH, 'rb') as f:
        pkl = pickle.load(f)
    before_stats = {
        'jockey_stats':   pkl.get('jockey_stats', {}),
        'distance_stats': pkl.get('distance_stats', {}),
    }
    print(f"  PKL 騎手件数: {len(before_stats['jockey_stats'])} "
          f"距離件数: {len(before_stats['distance_stats'])}")
else:
    print("  ⚠ PKL が見つかりません → 修正前比較をスキップします")

# ============================================================
# 3. グレード列追加 + テスト対象絞り込み（2022〜2026）
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
# 4. レース単位でバックテスト（修正前 vs 修正後）
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

    meta   = valid.iloc[0]
    year4  = int(meta['年4'])
    month  = int(meta['月'])
    day    = int(meta['日'])
    grade  = str(meta['grade'])
    race_date = f"{year4:04d}-{month:02d}-{day:02d}"

    # 修正後の統計（時系列分離）
    after_stats = get_stats_for_race(race_date)

    scores_before, scores_after = {}, {}
    for idx, row in valid.iterrows():
        try:
            if before_stats:
                scores_before[idx] = score_horse_v73(row, before_stats, blood_dict)
            scores_after[idx] = score_horse_v73(row, after_stats, blood_dict)
        except Exception:
            scores_before[idx] = 50.0
            scores_after[idx]  = 50.0

    if not scores_after:
        continue

    # 修正前
    if before_stats and scores_before:
        best_before_idx = max(scores_before, key=scores_before.get)
        pred_before     = str(valid.loc[best_before_idx, '馬名']).strip()
        odds_before     = float(valid.loc[best_before_idx, '単勝オッズ_num'] or 0)
    else:
        pred_before = ''
        odds_before = 0.0

    # 修正後
    best_after_idx = max(scores_after, key=scores_after.get)
    pred_after     = str(valid.loc[best_after_idx, '馬名']).strip()
    odds_after     = float(valid.loc[best_after_idx, '単勝オッズ_num'] or 0)

    results.append({
        'race_key':    rk,
        'grade':       grade,
        'year':        year4,
        'n_horses':    len(valid),
        'actual_1st':  actual_1st,
        'pop1_horse':  pop1_horse,
        # 修正前（PKL）
        'pred_before':  pred_before,
        'hit_before':   pred_before == actual_1st,
        'place_before': pred_before in actual_top3,
        'odds_before':  odds_before,
        # 修正後（時系列分離）
        'pred_after':   pred_after,
        'hit_after':    pred_after == actual_1st,
        'place_after':  pred_after in actual_top3,
        'odds_after':   odds_after,
        # 1番人気
        'pop1_hit': pop1_horse == actual_1st if pop1_horse else False,
        # 予測一致
        'same_pred': pred_before == pred_after,
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


hit_before  = int(df_res['hit_before'].sum())
hit_after   = int(df_res['hit_after'].sum())
place_before = int(df_res['place_before'].sum())
place_after  = int(df_res['place_after'].sum())
pop1_hit     = int(df_res['pop1_hit'].sum())
roi_before   = calc_roi(df_res, 'hit_before', 'odds_before')
roi_after    = calc_roi(df_res, 'hit_after',  'odds_after')
same_pct     = df_res['same_pred'].mean() * 100

print("\n" + "=" * 72)
print("  重賞バックテスト 修正前後比較（backtest_grade_clean.py）")
print("=" * 72)
print(f"  テスト期間: 2022〜2026年 / 対象レース: {total_R}R（10頭以上 Grade）")
print(f"  修正前: PKL 統計（全期間 2015-2026）")
print(f"  修正後: get_stats_for_race() 時系列分離統計")
print(f"  ◎選出が同一のレース: {df_res['same_pred'].sum()}R / {total_R}R ({same_pct:.1f}%)")
print()
print(f"  {'指標':<24} {'修正前(PKL)':>13} {'修正後(分離)':>13} {'差(前-後)':>11}")
print(f"  {'─' * 64}")
hb_pct  = hit_before  / total_R * 100
ha_pct  = hit_after   / total_R * 100
pb_pct  = place_before / total_R * 100
pa_pct  = place_after  / total_R * 100
pop_pct = pop1_hit    / total_R * 100
print(f"  {'◎的中率（単勝）':<24} {hb_pct:>11.2f}%  {ha_pct:>11.2f}%  {hb_pct-ha_pct:>+9.2f}%")
print(f"  {'◎複勝率（3着以内）':<24} {pb_pct:>11.2f}%  {pa_pct:>11.2f}%  {pb_pct-pa_pct:>+9.2f}%")
print(f"  {'単勝ROI（100円）':<24} {roi_before:>11.1f}%  {roi_after:>11.1f}%  {roi_before-roi_after:>+9.1f}%")
print(f"  {'1番人気的中率':<24} {pop_pct:>11.2f}%  {'（基準）':>11}  {'—':>11}")

# グレード別
print(f"\n  ─ グレード別 ─")
print(f"  {'G':<4} {'R':>5} {'前的中%':>8} {'後的中%':>8} {'差':>7} {'前ROI%':>8} {'後ROI%':>8}")
for g in ['G1', 'G2', 'G3']:
    sub = df_res[df_res['grade'] == g]
    n   = len(sub)
    if n == 0:
        continue
    hb = sub['hit_before'].sum()
    ha = sub['hit_after'].sum()
    rb = calc_roi(sub, 'hit_before', 'odds_before')
    ra = calc_roi(sub, 'hit_after',  'odds_after')
    print(f"  {g:<4} {n:>5} {hb/n*100:>7.1f}% {ha/n*100:>7.1f}% "
          f"{(hb-ha)/n*100:>+6.1f}% {rb:>7.1f}% {ra:>7.1f}%")

# 年別
print(f"\n  ─ 年別 ─")
print(f"  {'年':>5} {'R':>5} {'前的中%':>8} {'後的中%':>8} {'差':>7} "
      f"{'前ROI%':>8} {'後ROI%':>8} {'使用カットオフ':>12}")
for yr in sorted(df_res['year'].unique()):
    sub = df_res[df_res['year'] == yr]
    n   = len(sub)
    hb  = sub['hit_before'].sum()
    ha  = sub['hit_after'].sum()
    rb  = calc_roi(sub, 'hit_before', 'odds_before')
    ra  = calc_roi(sub, 'hit_after',  'odds_after')
    cutoff = {2022: 2021, 2023: 2022, 2024: 2023}.get(yr, 2024)
    print(f"  {yr:>5} {n:>5} {hb/n*100:>7.1f}% {ha/n*100:>7.1f}% "
          f"{(hb-ha)/n*100:>+6.1f}% {rb:>7.1f}% {ra:>7.1f}%   ≤{cutoff}")

# ◎選出が異なるレースの内訳
diff_df = df_res[~df_res['same_pred']]
if len(diff_df) > 0:
    hit_b_only = int((diff_df['hit_before'] & ~diff_df['hit_after']).sum())
    hit_a_only = int((~diff_df['hit_before'] & diff_df['hit_after']).sum())
    hit_both   = int((diff_df['hit_before'] & diff_df['hit_after']).sum())
    print(f"\n  ─ ◎が異なるレース ({len(diff_df)}R) ─")
    print(f"    PKL的中・分離外れ: {hit_b_only}R / "
          f"分離的中・PKL外れ: {hit_a_only}R / "
          f"両方外れ: {len(diff_df)-hit_b_only-hit_a_only-hit_both}R")
    roi_d_b = calc_roi(diff_df, 'hit_before', 'odds_before')
    roi_d_a = calc_roi(diff_df, 'hit_after',  'odds_after')
    print(f"    差異レース ROI: PKL={roi_d_b:.1f}% / 分離={roi_d_a:.1f}%")

print()
print("  [解釈のポイント]")
print("  ・差(前-後) がプラス → PKL統計の未来データ混入による過大評価の大きさ")
print("  ・差(前-後) がゼロ付近 → その年・グレードは時系列リークの影響が小さい")
print("  ・修正後 ROI > 100% → 時系列リーク排除後も実質的プラスエッジが存在する")

print("\n■ 完了")
