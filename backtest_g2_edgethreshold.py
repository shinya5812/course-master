# -*- coding: utf-8 -*-
"""
backtest_g2_edgethreshold.py
G2補正案X（エッジ閾値+0.07）単独検証

Step1: エッジ閾値+0.04〜+0.09 を G2レースで比較
       距離帯別ベット件数・ROI・的中率
       見送り増加数（全体比）

Step2: 長距離G2（2201m〜）見送りルール検証
       長距離除外 + エッジ閾値+0.07 の複合ルール

Step3: 実装判断
       採用基準: ROI > 133.1% かつ 見送り増加 ≤ 全体の30%

テスト期間: 2022〜2026年 G2レース（10頭以上・時系列分離済み統計）
真のベースライン: ROI133.1%（条件C 全軸リーク排除 G1/G2/G3 全体）
G2ベースライン: ROI133.7%（同上・G2のみ）
"""

import sys
import io
import os
import re
import json
import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RACE_DIR   = os.path.join(BASE_DIR, 'data', 'race')
PED_DIR    = os.path.join(BASE_DIR, 'data', 'pedigree')
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

GRADE_PATTERN  = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
CAREER_PENALTY = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
ODDS_MK_TABLE  = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]
WEIGHTS        = {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0, 'BL': 0.3, 'MK': 0.3}

# 検証パラメータ
BASELINE_ROI_ALL = 133.1   # 真のベースライン（全グレード）
BASELINE_ROI_G2  = 133.7   # G2単体ベースライン
EDGE_THRESHOLDS  = [0.04, 0.05, 0.06, 0.07, 0.08, 0.09]
LONG_DIST_CUTOFF = 2201     # 長距離G2の閾値（m）
MAX_SKIP_RATIO   = 0.30     # 採用基準: 見送り増加が全体の30%以内


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


def calc_roi(df_sub, hit_col, odds_col):
    n = len(df_sub)
    if n == 0:
        return 0.0
    paid_out = (df_sub[hit_col] * df_sub[odds_col] * 100).sum()
    return float(paid_out / (n * 100) * 100)


# ============================================================
# 1. データ読み込み
# ============================================================
print("■ CSVデータ読み込み中...")
dfs = []
for f in CSV_FILES:
    if os.path.exists(f):
        dfs.append(pd.read_csv(f, encoding='cp932', low_memory=False))
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
    tr = int(brow['全成績1着数'] + brow['全成績2着数'] + brow['全成績3着数'] + brow['全成績着外数'])
    tw = int(brow['全成績1着数'])
    blood_dict[name] = (tr, tw)
print(f"  血統CSV: {len(blood_dict):,}件")

df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None
)

sys.path.insert(0, BASE_DIR)
from backtest_utils import get_stats_for_race

# ============================================================
# 2. スコア計算・エッジ計算 ヘルパー
# ============================================================
def score_horse(row, stats):
    axes = {}
    horse_name  = str(row.get('馬名', '') or '').strip()
    horse_stats = stats.get('horse_stats', {})
    if horse_name in horse_stats:
        hs      = horse_stats[horse_name]
        total_r = hs['total_races']
        total_w = hs['total_wins']
    elif horse_name in blood_dict:
        total_r, total_w = blood_dict[horse_name]
    else:
        total_r, total_w = 0, 0

    if total_r > 0:
        wr   = total_w / total_r
        conf = min(1.0, total_r / 10)
        cf   = min(100.0, wr * 100 * conf + 50 * (1 - conf))
        pen  = CAREER_PENALTY.get(total_r, 1.0)
        if pen < 1.0 and cf > 50:
            cf = 50 + (cf - 50) * pen
    else:
        cf = 20.0
    axes['CF'] = cf

    agari = row.get('上がり3Fタイム_sec')
    axes['SI'] = max(10.0, 100 - (float(agari) - 30) * 2) if pd.notna(agari) else 50.0

    jockey       = row.get('騎手名')
    jockey_stats = stats.get('jockey_stats', {})
    axes['JT'] = (min(100.0, jockey_stats[str(jockey)]['win_rate'] * 100)
                  if pd.notna(jockey) and str(jockey) in jockey_stats else 50.0)

    passages = [float(p) for p in [row.get(f'通過順{i}') for i in range(1, 5)]
                if p is not None and not (isinstance(p, float) and np.isnan(p)) and float(p) > 0]
    axes['PD'] = max(10.0, 100 - abs(float(np.mean(passages)) - 7) * 3) if passages else 50.0

    pop = int(row.get('人気順', 0) or 0)
    axes['BL'] = max(10.0, 100 - pop * 5) if pop > 0 else 50.0

    dist           = int(row.get('距離', 0) or 0)
    jikan          = row.get('走破時計_sec')
    distance_stats = stats.get('distance_stats', {})
    if dist in distance_stats and pd.notna(jikan):
        ds = distance_stats[dist]
        if ds.get('std_time', 0) > 0:
            z = (float(jikan) - ds['avg_time']) / ds['std_time']
            axes['SPD'] = max(10.0, min(100.0, 50 - z * 10))
        else:
            axes['SPD'] = 50.0
    else:
        axes['SPD'] = 50.0

    odds = float(row.get('単勝オッズ_num', 0) or 0)
    if 1 <= pop <= 5:
        mk = float(100 - pop * 10)
    elif 6 <= pop <= 10:
        mk = float(50 - (pop - 5) * 5)
    else:
        mk = max(10.0, float(30 - max(0, pop - 10)))
    if pop > 5:
        mk += (pop - 5) * 2
    if odds > 0:
        for lo, hi, mult in ODDS_MK_TABLE:
            if lo < odds <= hi:
                if mult != 1.0:
                    mk = 50 + (mk - 50) * mult
                break
    axes['MK'] = mk

    keys = list(axes.keys())
    return float(np.average([axes[k] for k in keys], weights=[WEIGHTS.get(k, 1.0) for k in keys]))


def compute_edge(scores_dict, target_idx, target_odds):
    score_vals = np.array(list(scores_dict.values()), dtype=float)
    T = 5.0
    exp_v = np.exp((score_vals - score_vals.mean()) / T)
    probs = exp_v / exp_v.sum()
    pos   = list(scores_dict.keys()).index(target_idx)
    est_prob    = float(probs[pos])
    market_prob = (1.0 / target_odds * 0.80) if target_odds > 0 else 0.0
    return est_prob - market_prob


# ============================================================
# 3. テスト対象（G2・2022〜2026・10頭以上）
# ============================================================
test_df = df_all[(df_all['年4'] >= 2022) & (df_all['grade'] == 'G2')].copy()
test_df['race_key'] = (
    test_df['年4'].astype(str) + '_' +
    test_df['月'].astype(str).str.zfill(2) + '_' +
    test_df['日'].astype(str).str.zfill(2) + '_' +
    test_df['場所'].astype(str) + '_' +
    test_df['日次'].astype(str) + '_' +
    test_df['レース番号'].astype(str).str.zfill(2)
)
test_df = test_df.drop_duplicates(subset=['race_key', '馬名'])
print(f"\n■ G2テスト対象: {len(test_df.groupby('race_key'))}R (2022-2026, 10頭フィルター前)")

# ============================================================
# 4. バックテスト本体
# ============================================================
print("■ バックテスト実行中...")

records = []
race_groups = list(test_df.groupby('race_key'))

for i, (rk, rdf) in enumerate(race_groups):
    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 10:
        continue

    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_1st  = str(winner_rows.iloc[0]['馬名']).strip()
    actual_top3 = {str(h).strip() for h in valid[valid['確定着順'] <= 3]['馬名']}

    meta      = valid.iloc[0]
    year4     = int(meta['年4'])
    month     = int(meta['月'])
    day       = int(meta['日'])
    dist      = int(meta['距離'])
    race_date = f"{year4:04d}-{month:02d}-{day:02d}"

    try:
        sep_stats = get_stats_for_race(race_date)
    except FileNotFoundError:
        continue

    scores = {}
    for idx, row in valid.iterrows():
        try:
            scores[idx] = score_horse(row, sep_stats)
        except Exception:
            scores[idx] = 50.0

    if not scores:
        continue

    best_idx  = max(scores, key=scores.get)
    pred_name = str(valid.loc[best_idx, '馬名']).strip()
    pred_odds = float(valid.loc[best_idx, '単勝オッズ_num'] or 0)
    pred_pop  = int(valid.loc[best_idx, '人気順'] or 0)

    edge = compute_edge(scores, best_idx, pred_odds)

    records.append({
        'race_key':   rk,
        'year':       year4,
        'distance':   dist,
        'is_longdist': dist >= LONG_DIST_CUTOFF,
        'n_horses':   len(valid),
        'actual_1st': actual_1st,
        'actual_pop': int(winner_rows.iloc[0]['人気順']),
        'actual_odds':float(winner_rows.iloc[0]['単勝オッズ_num'] or 0),
        'pred_name':  pred_name,
        'pred_odds':  pred_odds,
        'pred_pop':   pred_pop,
        'edge':       round(edge, 4),
        'hit':        pred_name == actual_1st,
        'place':      pred_name in actual_top3,
    })

df_g2 = pd.DataFrame(records)
n_total = len(df_g2)
print(f"  完了: G2有効レース数 {n_total}R")

# 距離帯ラベル付け
dist_bins   = [0, 1400, 1800, 2200, 9999]
dist_labels = ['〜1400m', '1401〜1800m', '1801〜2200m', '2201m〜']
df_g2['dist_band'] = pd.cut(df_g2['distance'], bins=dist_bins, labels=dist_labels, right=True)

# ============================================================
# 5. Step1: エッジ閾値比較
# ============================================================
print("\n" + "=" * 82)
print("  ■ Step1: G2 エッジ閾値別バックテスト（+0.04〜+0.09）")
print("=" * 82)
print(f"  対象: G2 {n_total}R（2022〜2026年・10頭以上）")
print(f"  真のベースライン全体: ROI{BASELINE_ROI_ALL:.1f}%")
print(f"  G2ベースライン:       ROI{BASELINE_ROI_G2:.1f}%（{n_total}R全件ベット時）")
print()

# 全件ベット（閾値なし）をベースラインとして明示
roi_nofilter  = calc_roi(df_g2, 'hit', 'pred_odds')
hit_nofilter  = df_g2['hit'].mean() * 100
plc_nofilter  = df_g2['place'].mean() * 100
print(f"  ─ 閾値なし（全件ベット）─")
print(f"    {n_total}R  的中率{hit_nofilter:.2f}%  複勝率{plc_nofilter:.2f}%  ROI{roi_nofilter:.1f}%")
print()

threshold_results = {}

# 距離帯別ヘッダ
print(f"  {'閾値':>6} {'ベットR':>7} {'見送R':>6} {'見送%':>6} "
      f"{'的中%':>7} {'複勝%':>7} {'ROI':>8} {'ROI差':>8}  "
      f"| {'〜1400':>8} {'1401-1800':>10} {'1801-2200':>10} {'2201〜':>8}")
print("  " + "─" * 100)

for thr in EDGE_THRESHOLDS:
    bet_df  = df_g2[df_g2['edge'] >= thr]
    skip_df = df_g2[df_g2['edge'] < thr]
    n_bet   = len(bet_df)
    n_skip  = len(skip_df)

    if n_bet == 0:
        threshold_results[str(thr)] = {'n_bet': 0, 'n_skip': n_skip}
        print(f"  {thr:>+.2f}   {n_bet:>6}  {n_skip:>6} {n_skip/n_total*100:>5.1f}%   ベットなし")
        continue

    hit_r  = bet_df['hit'].mean() * 100
    plc_r  = bet_df['place'].mean() * 100
    roi    = calc_roi(bet_df, 'hit', 'pred_odds')
    roi_diff = roi - BASELINE_ROI_G2

    # 距離帯別ROI（表右側）
    dist_roi_strs = []
    for band in dist_labels:
        sub_b = bet_df[bet_df['dist_band'] == band]
        if len(sub_b) == 0:
            dist_roi_strs.append('   —')
        else:
            roi_b = calc_roi(sub_b, 'hit', 'pred_odds')
            dist_roi_strs.append(f'{roi_b:>6.0f}%')

    skip_ratio = n_skip / n_total
    flag = ' ← 見送超過' if skip_ratio > MAX_SKIP_RATIO else ''

    print(f"  {thr:>+.2f}   {n_bet:>6}  {n_skip:>6} {n_skip/n_total*100:>5.1f}%  "
          f"{hit_r:>6.2f}%  {plc_r:>6.2f}%  {roi:>7.1f}%  {roi_diff:>+7.1f}%pt  "
          f"| {dist_roi_strs[0]:>8} {dist_roi_strs[1]:>10} {dist_roi_strs[2]:>10} {dist_roi_strs[3]:>8}{flag}")

    threshold_results[str(thr)] = {
        'n_bet':      n_bet,
        'n_skip':     n_skip,
        'skip_ratio': round(skip_ratio, 3),
        'hit_rate':   round(hit_r, 2),
        'place_rate': round(plc_r, 2),
        'roi':        round(roi, 1),
        'roi_diff':   round(roi_diff, 1),
        'dist_roi': {
            band: round(calc_roi(bet_df[bet_df['dist_band'] == band], 'hit', 'pred_odds'), 1)
            if len(bet_df[bet_df['dist_band'] == band]) > 0 else None
            for band in dist_labels
        },
    }

# +0.06と+0.07の差分（見送り増加分の定量化）
n_bet_06 = len(df_g2[df_g2['edge'] >= 0.06])
n_bet_07 = len(df_g2[df_g2['edge'] >= 0.07])
n_new_skip = n_bet_06 - n_bet_07

print()
print(f"  ─ +0.06 → +0.07 の変化 ─")
print(f"    +0.06でベット: {n_bet_06}R  →  +0.07でベット: {n_bet_07}R")
print(f"    新たに見送り: {n_new_skip}R（+0.06でベットしていたが+0.07では見送り）")
print(f"    見送り増加率（全体比）: {n_new_skip/n_total*100:.1f}%  "
      f"{'← 採用基準30%以内 ✓' if n_new_skip/n_total <= MAX_SKIP_RATIO else f'← 採用基準30%超 ✗（{n_new_skip/n_total*100:.1f}%）'}")

# 年別（+0.07のみ）
print(f"\n  ─ 年別（+0.07でベット）─")
print(f"  {'年':>5} {'ベットR':>7} {'全G2R':>7} {'ベット%':>7} {'的中%':>7} {'ROI':>8}")
for yr in sorted(df_g2['year'].unique()):
    sub_yr  = df_g2[df_g2['year'] == yr]
    bet_yr  = sub_yr[sub_yr['edge'] >= 0.07]
    n_all_yr = len(sub_yr)
    n_bet_yr = len(bet_yr)
    if n_bet_yr == 0:
        print(f"  {yr:>5} {n_bet_yr:>7}  {n_all_yr:>6}  —%  —%  —%")
        continue
    hit_yr = bet_yr['hit'].mean() * 100
    roi_yr = calc_roi(bet_yr, 'hit', 'pred_odds')
    print(f"  {yr:>5} {n_bet_yr:>7}  {n_all_yr:>6} {n_bet_yr/n_all_yr*100:>6.1f}%  {hit_yr:>6.2f}%  {roi_yr:>7.1f}%")

# ============================================================
# 6. Step2: 長距離G2（2201m〜）見送りルール検証
# ============================================================
print("\n" + "=" * 82)
print("  ■ Step2: 長距離G2（2201m〜）見送りルール検証")
print("=" * 82)

df_long = df_g2[df_g2['is_longdist']]
df_short = df_g2[~df_g2['is_longdist']]
n_long  = len(df_long)
n_short = len(df_short)

# 長距離G2の詳細
roi_long  = calc_roi(df_long, 'hit', 'pred_odds')
hit_long  = df_long['hit'].mean() * 100 if n_long > 0 else 0
plc_long  = df_long['place'].mean() * 100 if n_long > 0 else 0
roi_short = calc_roi(df_short, 'hit', 'pred_odds')
hit_short = df_short['hit'].mean() * 100 if n_short > 0 else 0

print(f"\n  長距離（2201m〜）: {n_long}R  的中率{hit_long:.2f}%  複勝率{plc_long:.2f}%  ROI{roi_long:.1f}%")
print(f"  短中距離（〜2200m）: {n_short}R  的中率{hit_short:.2f}%  ROI{roi_short:.1f}%")

# 長距離を見送りにした場合のG2全体ROI
print(f"\n  ─ 長距離G2見送りルール 試算 ─")
print(f"  {'条件':<36} {'ベットR':>6} {'見送R':>6} {'見送%':>6} {'的中%':>7} {'ROI':>8} {'ROI差':>9}")
print("  " + "─" * 82)

# A: 全件ベット（ベースライン）
print(f"  {'A: 閾値なし・全件ベット':<36} {n_total:>6} {'0':>6} {'0.0%':>6} "
      f"{hit_nofilter:>6.2f}%  {roi_nofilter:>7.1f}%  {'（基準）':>9}")

# B: 長距離除外のみ
roi_b  = calc_roi(df_short, 'hit', 'pred_odds')
hit_b  = df_short['hit'].mean() * 100
skip_b = n_long
print(f"  {'B: 長距離除外（〜2200m）のみ':<36} {n_short:>6} {skip_b:>6} {skip_b/n_total*100:>5.1f}%  "
      f"{hit_b:>6.2f}%  {roi_b:>7.1f}%  {roi_b-roi_nofilter:>+8.1f}%pt")

# C: エッジ+0.07のみ（全距離）
bet_c  = df_g2[df_g2['edge'] >= 0.07]
n_c    = len(bet_c)
roi_c  = calc_roi(bet_c, 'hit', 'pred_odds') if n_c > 0 else 0
hit_c  = bet_c['hit'].mean() * 100 if n_c > 0 else 0
skip_c = n_total - n_c
print(f"  {'C: エッジ+0.07のみ（全距離）':<36} {n_c:>6} {skip_c:>6} {skip_c/n_total*100:>5.1f}%  "
      f"{hit_c:>6.2f}%  {roi_c:>7.1f}%  {roi_c-roi_nofilter:>+8.1f}%pt")

# D: 長距離除外 + エッジ+0.07
bet_d  = df_short[df_short['edge'] >= 0.07]
n_d    = len(bet_d)
roi_d  = calc_roi(bet_d, 'hit', 'pred_odds') if n_d > 0 else 0
hit_d  = bet_d['hit'].mean() * 100 if n_d > 0 else 0
skip_d = n_total - n_d
print(f"  {'D: 長距離除外 + エッジ+0.07':<36} {n_d:>6} {skip_d:>6} {skip_d/n_total*100:>5.1f}%  "
      f"{hit_d:>6.2f}%  {roi_d:>7.1f}%  {roi_d-roi_nofilter:>+8.1f}%pt")

# E: 長距離除外 + エッジ+0.06
bet_e  = df_short[df_short['edge'] >= 0.06]
n_e    = len(bet_e)
roi_e  = calc_roi(bet_e, 'hit', 'pred_odds') if n_e > 0 else 0
hit_e  = bet_e['hit'].mean() * 100 if n_e > 0 else 0
skip_e = n_total - n_e
print(f"  {'E: 長距離除外 + エッジ+0.06':<36} {n_e:>6} {skip_e:>6} {skip_e/n_total*100:>5.1f}%  "
      f"{hit_e:>6.2f}%  {roi_e:>7.1f}%  {roi_e-roi_nofilter:>+8.1f}%pt")

# 長距離G2の年別内訳
print(f"\n  ─ 長距離G2（2201m〜）年別内訳 ─")
print(f"  {'年':>5} {'R':>4} {'的中%':>7} {'ROI':>8}")
for yr in sorted(df_long['year'].unique()):
    sub_yr   = df_long[df_long['year'] == yr]
    roi_yr   = calc_roi(sub_yr, 'hit', 'pred_odds')
    hit_yr   = sub_yr['hit'].mean() * 100
    print(f"  {yr:>5} {len(sub_yr):>4} {hit_yr:>6.2f}%  {roi_yr:>7.1f}%")

# 長距離G2のレース名確認（上位外れ例）
print(f"\n  ─ 長距離G2 オッズ上位的中例（参考） ─")
hit_long_df = df_long[df_long['hit']].sort_values('pred_odds', ascending=False)
for _, r in hit_long_df.head(5).iterrows():
    print(f"    {r['year']}年 {r['distance']}m  ◎{r['pred_name']}  {r['pred_odds']:.1f}倍  edge{r['edge']:+.3f}")

# ============================================================
# 7. Step3: 実装判断
# ============================================================
print("\n" + "=" * 82)
print("  ■ Step3: 実装判断")
print("=" * 82)

decisions = {}

print(f"\n  採用基準: ROI > {BASELINE_ROI_ALL:.1f}% かつ 見送り増加 ≤ 全体の{MAX_SKIP_RATIO*100:.0f}%")
print()

# 各ルールを判定
rules = [
    ('C: エッジ+0.07のみ',          n_c,  skip_c, roi_c,  hit_c),
    ('D: 長距離除外 + エッジ+0.07', n_d,  skip_d, roi_d,  hit_d),
    ('E: 長距離除外 + エッジ+0.06', n_e,  skip_e, roi_e,  hit_e),
    ('B: 長距離除外のみ',            n_short, skip_b, roi_b, hit_b),
]

for name, n_bet, n_skip, roi, hit in rules:
    skip_ratio    = n_skip / n_total
    roi_ok        = roi > BASELINE_ROI_ALL
    skip_ok       = skip_ratio <= MAX_SKIP_RATIO
    adopted       = roi_ok and skip_ok

    if adopted:
        verdict = '★★ 採用'
    elif roi_ok:
        verdict = '△  ROIは基準超・見送り超過'
    elif skip_ok:
        verdict = '△  見送りは基準内・ROI不足'
    else:
        verdict = '✗  不採用（両基準未達）'

    decisions[name] = {
        'n_bet': n_bet, 'n_skip': n_skip, 'skip_ratio': round(skip_ratio, 3),
        'roi': round(roi, 1), 'hit_rate': round(hit, 2),
        'roi_ok': roi_ok, 'skip_ok': skip_ok, 'adopted': adopted, 'verdict': verdict,
    }

    print(f"  【{name}】")
    print(f"    ベット: {n_bet}R / 見送り: {n_skip}R ({skip_ratio*100:.1f}%)  ROI: {roi:.1f}%  的中率: {hit:.2f}%")
    print(f"    ROI基準({BASELINE_ROI_ALL:.1f}%超): {'✓' if roi_ok else '✗'}  "
          f"見送り基準({MAX_SKIP_RATIO*100:.0f}%以内): {'✓' if skip_ok else '✗'}  "
          f"→ {verdict}")
    print()

# 最終推奨
best_adopted = [(name, v) for name, v in decisions.items() if v['adopted']]
print("  ─ 最終推奨 ─")
if best_adopted:
    # ROI最高の採用案を推奨
    best = max(best_adopted, key=lambda x: x[1]['roi'])
    print(f"  ★ 推奨ルール: {best[0]}")
    print(f"    ROI: {best[1]['roi']:.1f}%  ベット: {best[1]['n_bet']}R  見送り: {best[1]['n_skip']}R")
else:
    print("  ✗ 採用基準を満たすルールなし（全て「見送り超過」または「ROI不足」）")

print()
print("  ─ 運用メモ ─")
print(f"  ・G2 〜1400m（{len(df_g2[df_g2['dist_band']=='〜1400m'])}R）: エッジ閾値によらず高ROI傾向→ 閾値緩和も検討")
print(f"  ・G2 2201m〜（{n_long}R）: ROI{roi_long:.1f}% → 見送り候補（長距離は難予測）")
print(f"  ・見送り増加 +0.06→+0.07: {n_new_skip}R（全体{n_new_skip/n_total*100:.1f}%）")

print("\n■ 完了")

# ============================================================
# 8. JSON 保存
# ============================================================
output = {
    'created':       pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
    'test_period':   '2022-2026',
    'n_g2_races':    n_total,
    'baseline': {
        'all_grades_roi':   BASELINE_ROI_ALL,
        'g2_only_roi':      BASELINE_ROI_G2,
        'g2_nofilter_roi':  round(roi_nofilter, 1),
        'g2_nofilter_hit':  round(hit_nofilter, 2),
    },
    'step1_thresholds': {
        'thresholds_tested':       [str(t) for t in EDGE_THRESHOLDS],
        'skip_increase_0.06_to_07': {
            'n_bet_06':   n_bet_06,
            'n_bet_07':   n_bet_07,
            'n_new_skip': n_new_skip,
            'skip_ratio': round(n_new_skip / n_total, 3),
        },
        'by_threshold': threshold_results,
    },
    'step2_longdist': {
        'cutoff_m':           LONG_DIST_CUTOFF,
        'n_long':             n_long,
        'n_short':            n_short,
        'long_hit_rate':      round(hit_long, 2),
        'long_roi':           round(roi_long, 1),
        'short_hit_rate':     round(hit_short, 2),
        'short_roi':          round(roi_short, 1),
        'rules': {
            'A_no_filter':     {'n_bet': n_total, 'roi': round(roi_nofilter, 1)},
            'B_longdist_excl': {'n_bet': n_short, 'roi': round(roi_b, 1)},
            'C_edge007':       {'n_bet': n_c,      'roi': round(roi_c, 1)},
            'D_longexcl_e007': {'n_bet': n_d,      'roi': round(roi_d, 1)},
            'E_longexcl_e006': {'n_bet': n_e,      'roi': round(roi_e, 1)},
        },
    },
    'step3_decisions': decisions,
}

out_path = os.path.join(BASE_DIR, 'backtest_g2_edgethreshold.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n  → {out_path}")
