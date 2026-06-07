# -*- coding: utf-8 -*-
"""
backtest_2200m_over.py
2200m超 G1/G2 バックテスト（時系列分離版）

対象: 2021-2023年 G1/G2 × 距離2201m以上 × 出走10頭以上
リーク防止: backtest_utils.get_stats_for_race() による年次カットオフ
出力: output/backtest_2200m_over_2021_2023.csv
"""
import sys
import io
import os
import re
import csv

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
RACE_DIR  = os.path.join(BASE_DIR, 'data', 'race')
PED_DIR   = os.path.join(BASE_DIR, 'data', 'pedigree')
OUT_DIR   = os.path.join(BASE_DIR, 'output')
os.makedirs(OUT_DIR, exist_ok=True)

BLOOD_FILE = os.path.join(PED_DIR, '20260217血統.csv')
OUTPUT_CSV = os.path.join(OUT_DIR, 'backtest_2200m_over_2021_2023.csv')

CSV_FILES = [
    os.path.join(RACE_DIR, '2015_2016結果.csv'),
    os.path.join(RACE_DIR, '2017_2018結果.csv'),
    os.path.join(RACE_DIR, '2019_2020結果.csv'),
    os.path.join(RACE_DIR, '2021_2023結果.csv'),
]

GRADE_PATTERN = re.compile(r'[GＧ][ⅠⅡ12１２]')

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
    return None


def softmax_probs(scores_dict, temperature=5.0):
    """スコア辞書 → softmax 確率辞書（T=5.0）"""
    indices = list(scores_dict.keys())
    vals    = np.array([scores_dict[i] for i in indices], dtype=float)
    shifted = vals - vals.max()
    exp_v   = np.exp(shifted / temperature)
    total   = exp_v.sum()
    return {idx: float(exp_v[i] / total) for i, idx in enumerate(indices)}


def calc_edge(win_prob, odds):
    if odds <= 0:
        return None
    return win_prob - (1.0 / odds) * 0.80


# ============================================================
# 1. データ読み込み
# ============================================================
print("■ CSVデータ読み込み中...")
dfs = []
for f in CSV_FILES:
    if os.path.exists(f):
        df = pd.read_csv(f, encoding='cp932', low_memory=False)
        dfs.append(df)
        print(f"  {os.path.basename(f)}: {len(df):,}行")
    else:
        print(f"  [SKIP] {os.path.basename(f)}")

df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}行")

# 数値化
df_all['確定着順']           = pd.to_numeric(df_all['確定着順'],    errors='coerce').fillna(0).astype(int)
df_all['人気順']             = pd.to_numeric(df_all['人気順'],      errors='coerce').fillna(0).astype(int)
df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'],    errors='coerce')
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'],  errors='coerce').fillna(0)
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
df_all['距離']               = pd.to_numeric(df_all['距離'],        errors='coerce').fillna(0).astype(int)
df_all['年4']                = df_all['年'].apply(lambda y: 2000 + int(y) if pd.notna(y) and 0 < int(y) < 100 else int(y) if pd.notna(y) else 0)
for col in ['通過順1', '通過順2', '通過順3', '通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# ============================================================
# 2. 血統CSV 読み込み（CF軸フォールバック用）
# ============================================================
print("\n■ 血統データ読み込み...")
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
print(f"  blood_dict: {len(blood_dict):,}件")

# ============================================================
# 3. G1/G2 × 2201m以上 × 2021-2023 に絞り込み
# ============================================================
df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None
)

test_df = df_all[
    (df_all['年4'] >= 2021) &
    (df_all['年4'] <= 2023) &
    (df_all['grade'].isin(['G1', 'G2'])) &
    (df_all['距離'] >= 2201)
].copy()

test_df['race_key'] = (
    test_df['年4'].astype(str) + '_' +
    test_df['月'].astype(str).str.zfill(2) + '_' +
    test_df['日'].astype(str).str.zfill(2) + '_' +
    test_df['場所'].astype(str) + '_' +
    test_df['日次'].astype(str) + '_' +
    test_df['レース番号'].astype(str).str.zfill(2)
)
test_df = test_df.drop_duplicates(subset=['race_key', '馬名'])

total_races_before = test_df['race_key'].nunique()
print(f"\n■ 対象レース候補: {total_races_before}R (10頭フィルター前)")

# ============================================================
# 4. レース単位でバックテスト
# ============================================================
print("■ バックテスト実行中...")

results = []
race_groups = list(test_df.groupby('race_key'))

for i, (rk, rdf) in enumerate(race_groups):
    if i % 20 == 0:
        print(f"  進捗: {i}/{len(race_groups)}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 10:
        continue

    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue

    actual_1st   = str(winner_rows.iloc[0]['馬名']).strip()
    actual_top3  = {str(h).strip() for h in valid[valid['確定着順'] <= 3]['馬名']}

    meta      = valid.iloc[0]
    year4     = int(meta['年4'])
    month     = int(meta['月'])
    day       = int(meta['日'])
    grade     = str(meta['grade'])
    dist      = int(meta['距離'])
    race_name = str(meta['レース名'])
    venue     = str(meta['場所'])
    race_date = f"{year4:04d}-{month:02d}-{day:02d}"

    # 時系列分離統計取得
    try:
        stats = get_stats_for_race(race_date)
    except FileNotFoundError as e:
        print(f"  [WARN] {e}")
        continue

    # スコア計算
    scores = {}
    for idx, row in valid.iterrows():
        try:
            scores[idx] = score_horse_v73(row, stats, blood_dict, use_horse_stats=True)
        except Exception:
            scores[idx] = 50.0

    if not scores:
        continue

    # softmax → 推定勝率
    win_probs = softmax_probs(scores, temperature=5.0)

    # ◎ = 最高スコア馬
    best_idx     = max(scores, key=scores.get)
    best_row     = valid.loc[best_idx]
    pred_name    = str(best_row['馬名']).strip()
    pred_score   = scores[best_idx]
    pred_wp      = win_probs[best_idx]
    pred_pop     = int(best_row['人気順'] or 0)
    pred_odds    = float(best_row['単勝オッズ_num'] or 0)
    pred_finish  = int(best_row['確定着順'])
    edge         = calc_edge(pred_wp, pred_odds)

    hit_win   = pred_name == actual_1st
    hit_place = pred_name in actual_top3

    dist_band = '2201〜2400m' if dist <= 2400 else '2401m以上'
    if edge is None:
        edge_band = 'オッズ不明'
    elif edge >= 0.06:
        edge_band = '+0.06以上'
    elif edge >= 0.00:
        edge_band = '0〜+0.06'
    else:
        edge_band = 'マイナス'

    results.append({
        'race_date':   race_date,
        'venue':       venue,
        'race_name':   race_name,
        'grade':       grade,
        'distance':    dist,
        'dist_band':   dist_band,
        'n_horses':    len(valid),
        'pred_horse':  pred_name,
        'pred_score':  round(pred_score, 2),
        'pred_wp':     round(pred_wp, 4),
        'pred_pop':    pred_pop,
        'pred_odds':   pred_odds,
        'edge':        round(edge, 4) if edge is not None else None,
        'edge_band':   edge_band,
        'actual_finish': pred_finish,
        'actual_1st':  actual_1st,
        'hit_win':     hit_win,
        'hit_place':   hit_place,
    })

print(f"  完了: 有効レース数 {len(results)}R (10頭以上)")

# ============================================================
# 5. 集計
# ============================================================
df_res  = pd.DataFrame(results)
total_R = len(df_res)

if total_R == 0:
    print("\n[ERROR] 有効レースが0件です")
    sys.exit(1)

win_rate   = df_res['hit_win'].mean()
place_rate = df_res['hit_place'].mean()

print(f"\n{'='*60}")
print(f"【2200m超 G1/G2 バックテスト結果（2021〜2023）】")
print(f"{'='*60}")
print(f"  対象レース    : {total_R}R")
print(f"  ◎的中率（1着）: {win_rate*100:.1f}%  ({df_res['hit_win'].sum()}/{total_R})")
print(f"  ◎複勝率（3着内）: {place_rate*100:.1f}%  ({df_res['hit_place'].sum()}/{total_R})")

# 距離帯別
print(f"\n--- 距離帯別 ---")
for band in ['2201〜2400m', '2401m以上']:
    sub = df_res[df_res['dist_band'] == band]
    if len(sub) == 0:
        continue
    print(f"  {band}: {len(sub)}R  的中率 {sub['hit_win'].mean()*100:.1f}%  複勝率 {sub['hit_place'].mean()*100:.1f}%")

# グレード別
print(f"\n--- グレード別 ---")
for grade in ['G1', 'G2']:
    sub = df_res[df_res['grade'] == grade]
    if len(sub) == 0:
        continue
    print(f"  {grade}: {len(sub)}R  的中率 {sub['hit_win'].mean()*100:.1f}%  複勝率 {sub['hit_place'].mean()*100:.1f}%")

# エッジ値分布
print(f"\n--- エッジ値分布 ---")
for band in ['+0.06以上', '0〜+0.06', 'マイナス', 'オッズ不明']:
    sub = df_res[df_res['edge_band'] == band]
    if len(sub) == 0:
        continue
    print(f"  {band}: {len(sub)}R  的中率 {sub['hit_win'].mean()*100:.1f}%  複勝率 {sub['hit_place'].mean()*100:.1f}%")

# 穴馬戦略（◎4番人気以上）
anaba = df_res[df_res['pred_pop'] >= 4]
if len(anaba) > 0:
    print(f"\n--- 穴馬戦略（◎4番人気以上） ---")
    print(f"  {len(anaba)}R  的中率 {anaba['hit_win'].mean()*100:.1f}%  複勝率 {anaba['hit_place'].mean()*100:.1f}%")
    if len(anaba[anaba['pred_odds'] > 0]) > 0:
        sub_odds = anaba[anaba['pred_odds'] > 0]
        roi = (sub_odds['hit_win'] * sub_odds['pred_odds']).sum() / len(sub_odds) * 100
        print(f"  単勝回収率: {roi:.1f}%  (有効{len(sub_odds)}R)")

# ============================================================
# 6. CSV保存
# ============================================================
df_res.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
print(f"\n■ CSV保存: {OUTPUT_CSV}")
print(f"  レコード数: {len(df_res)}件")

print(f"\n{'='*60}")
print("完了")
print(f"{'='*60}")
