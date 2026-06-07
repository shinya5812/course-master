# -*- coding: utf-8 -*-
"""
hypothesis_e5_edge_threshold.py  -  ⑤ エッジ値閾値最適化

【目的】
  現行の+0.05閾値を+0.03〜+0.08の範囲で再検証し最適閾値を特定する。

【検証ステップ】
  Step 1: 閾値別の回収率・的中率（訓練データ 2015〜2023 重賞）
  Step 2: 検証データでの確認（2024〜2026 重賞）トップ3閾値を確認
  Step 3: 穴馬戦略 × 各閾値の組み合わせ
  Step 4: 阪神稍重+0.07引き上げルールの検証
  Step 5: 結論

使い方:
  python3 hypothesis_e5_edge_threshold.py
"""

import sys
import io
import os
import re
import pickle
import numpy as np
import pandas as pd
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
PKL_PATH   = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_FILE = os.path.join(BASE_DIR, 'data', 'pedigree', '血統_0410.csv')
CSV_FILES  = [
    os.path.join(BASE_DIR, 'data', 'race', '2015_2016結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2017_2018結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2019_2020結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2021_2023結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2024_2026結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2026結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '202602280331結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '結果202603070405.csv'),
]

TEMPERATURE    = 5.0
BET_UNIT       = 100
GRADE_PAT      = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
TRAIN_YEAR_MAX = 23
TEST_YEAR_MIN  = 24

# 検証する閾値リスト
THRESHOLDS = [0.03, 0.04, 0.05, 0.06, 0.07, 0.08]

SEP = "=" * 65


# ============================================================
# ユーティリティ
# ============================================================
def detect_grade(race_name):
    if not race_name:
        return None
    m = GRADE_PAT.search(str(race_name))
    if not m:
        return None
    g = m.group()
    if g[-1] in ('Ⅰ', '1', '１'):
        return 'G1'
    elif g[-1] in ('Ⅱ', '2', '２'):
        return 'G2'
    elif g[-1] in ('Ⅲ', '3', '３'):
        return 'G3'
    return None


def dist_band(d):
    if d <= 0:
        return '不明'
    elif d <= 1400:
        return '〜1400m'
    elif d <= 2000:
        return '1600〜2000m'
    else:
        return '2200m〜'


def race_recovery(sub_df):
    """race_records サブセットの単勝回収率（%）"""
    if len(sub_df) == 0:
        return 0.0
    payout = sub_df.loc[sub_df['hit'], 'pred_odds'].sum() * BET_UNIT
    total  = len(sub_df) * BET_UNIT
    return payout / total * 100


def yearly_black_rate(sub_df):
    """年別黒字率（100%超の年の割合）"""
    years = sorted(sub_df['year'].unique())
    if len(years) == 0:
        return 0.0, []
    black = 0
    detail = []
    for yr in years:
        ysub = sub_df[sub_df['year'] == yr]
        rec  = race_recovery(ysub)
        if rec >= 100.0:
            black += 1
        detail.append((yr, len(ysub), rec))
    return black / len(years) * 100, detail


# ============================================================
# 1. pkl読み込み
# ============================================================
print("■ pkl 読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

sire_stats      = state.get('sire_stats', {})
jockey_stats    = state.get('jockey_stats', {})
distance_stats  = state.get('distance_stats', {})
career_penalty  = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
odds_mk_table   = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]

print(f"  sire_stats:{len(sire_stats)}件  jockey_stats:{len(jockey_stats)}件  "
      f"distance_stats:{len(distance_stats)}件")


# ============================================================
# 2. CSV読み込み・前処理
# ============================================================
print("\n■ CSV 読み込み中...")
dfs = []
for fpath in CSV_FILES:
    if os.path.exists(fpath):
        dfs.append(pd.read_csv(fpath, encoding='cp932', low_memory=False))
        print(f"  {os.path.basename(fpath)}: {len(dfs[-1]):,}件")
    else:
        print(f"  [スキップ] {os.path.basename(fpath)}")

df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}件")

for col, dtype in [('確定着順','int'),('人気順','int'),('距離','int'),('年齢','float')]:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(
        int if dtype == 'int' else float)
df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'],       errors='coerce')
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'],     errors='coerce').fillna(0.0)
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
for col in ['通過順1','通過順2','通過順3','通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# 芝ダ正規化
if '芝・ダ' in df_all.columns:
    df_all['surface'] = df_all['芝・ダ'].astype(str).str.strip()
else:
    df_all['surface'] = ''

print("\n■ 血統データ読み込み...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数','全成績2着数','全成績3着数','全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)

blood_slim = df_blood[['血統登録番号','種牡馬名','母の父名']].copy()
blood_slim.columns = ['血統登録番号','父馬名_b','母の父馬名_b']
df_all = df_all.merge(blood_slim, on='血統登録番号', how='left')
df_all['父馬名']     = df_all['父馬名'].fillna(df_all['父馬名_b'])
df_all['母の父馬名'] = df_all['母の父馬名'].fillna(df_all['母の父馬名_b'])
df_all.drop(['父馬名_b','母の父馬名_b'], axis=1, inplace=True)

horse_place_rate = {}
for _, brow in df_blood.iterrows():
    name  = str(brow['馬名']).strip()
    total = (brow['全成績1着数'] + brow['全成績2着数'] +
             brow['全成績3着数'] + brow['全成績着外数'])
    if total >= 5:
        placed = brow['全成績1着数'] + brow['全成績2着数'] + brow['全成績3着数']
        horse_place_rate[name] = float(placed) / float(total)

print(f"  place_rate取得馬数: {len(horse_place_rate):,}頭")

df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None)
grade_df = df_all[df_all['grade'].notna()].copy()

grade_df['race_key'] = (
    grade_df['年'].astype(str) + '_' +
    grade_df['月'].astype(str).str.zfill(2) + '_' +
    grade_df['日'].astype(str).str.zfill(2) + '_' +
    grade_df['場所'].astype(str) + '_' +
    grade_df['日次'].astype(str) + '_' +
    grade_df['レース番号'].astype(str).str.zfill(2)
)
grade_df = grade_df.drop_duplicates(subset=['race_key','馬名'])

print(f"  重賞レコード: {len(grade_df):,}件  "
      f"G1:{(grade_df['grade']=='G1').sum():,}  "
      f"G2:{(grade_df['grade']=='G2').sum():,}  "
      f"G3:{(grade_df['grade']=='G3').sum():,}")


# ============================================================
# 3. スコア計算（v7.3エンジン忠実再現）
# ============================================================
def score_horse(row, team_type='I'):
    axes = {}

    # CF
    horse_name = str(row['馬名']).strip()
    bi = df_blood[df_blood['馬名'] == horse_name]
    if not bi.empty:
        total = int(bi['全成績1着数'].iloc[0] + bi['全成績2着数'].iloc[0] +
                    bi['全成績3着数'].iloc[0] + bi['全成績着外数'].iloc[0])
        wins  = int(bi['全成績1着数'].iloc[0])
        if total > 0:
            conf = min(1.0, total / 10)
            cf   = wins / total * 100 * conf + 50 * (1 - conf)
            cf   = min(100, cf)
            pen  = career_penalty.get(total, 1.0)
            if pen < 1.0 and cf > 50:
                cf = 50 + (cf - 50) * pen
        else:
            cf = 20
    else:
        cf = 20
    axes['CF'] = cf

    # SI
    agari = row['上がり3Fタイム_sec']
    axes['SI'] = max(10, 100 - (agari - 30) * 2) if pd.notna(agari) else 50

    # JT
    jockey = row['騎手名']
    if pd.notna(jockey) and jockey in jockey_stats:
        axes['JT'] = min(100, jockey_stats[jockey]['win_rate'] * 100)
    else:
        axes['JT'] = 50

    # PD
    passages = [row.get('通過順1'), row.get('通過順2'),
                row.get('通過順3'), row.get('通過順4')]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    axes['PD'] = max(10, 100 - abs(np.mean(passages) - 7) * 3) if passages else 50

    # BL
    pop = int(row['人気順'])
    axes['BL'] = max(10, 100 - pop * 5) if pop > 0 else 50

    # SPD
    dist  = int(row['距離'])
    jikan = row['走破時計_sec']
    if dist in distance_stats and pd.notna(jikan):
        ds = distance_stats[dist]
        if ds['std_time'] > 0:
            z = (float(jikan) - ds['avg_time']) / ds['std_time']
            axes['SPD'] = max(10, min(100, 50 - z * 10))
        else:
            axes['SPD'] = 50
    else:
        axes['SPD'] = 50

    # MK
    odds = float(row['単勝オッズ_num']) if pd.notna(row.get('単勝オッズ_num')) else 0.0
    if 1 <= pop <= 5:
        mk = 100 - pop * 10
    elif 6 <= pop <= 10:
        mk = 50 - (pop - 5) * 5
    else:
        mk = max(10, 30 - (pop - 10))
    if team_type == 'I' and pop > 5:
        mk += (pop - 5) * 2
    elif team_type == 'O' and pop <= 3:
        mk += (4 - pop) * 5
    if odds > 0:
        for lo, hi, mult in odds_mk_table:
            if lo < odds <= hi:
                if mult != 1.0:
                    mk = 50 + (mk - 50) * mult
                break
    axes['MK'] = mk

    W = {'CF': 2.0, 'SI': 2.0, 'SPD': 2.0, 'JT': 2.0,
         'PD': 1.0, 'BL': 0.3, 'MK': 0.3}
    keys = list(axes.keys())
    vals = [axes[k] for k in keys]
    wts  = [W.get(k, 1.0) for k in keys]
    return float(np.average(vals, weights=wts))


def score_race_4teams(rdf):
    teams = ['I', 'O', 'U', 'S']
    team_scores = {t: {} for t in teams}
    for t in teams:
        for idx, row in rdf.iterrows():
            try:
                team_scores[t][idx] = score_horse(row, t)
            except Exception:
                team_scores[t][idx] = 50.0
    return {idx: float(np.mean([team_scores[t][idx] for t in teams]))
            for idx in rdf.index}


def score_to_win_prob(scores_dict, rdf):
    indices   = list(scores_dict.keys())
    score_arr = np.array([scores_dict[i] for i in indices])
    shifted       = score_arr - score_arr.max()
    softmax_probs = np.exp(shifted / TEMPERATURE)
    softmax_probs = softmax_probs / softmax_probs.sum()

    win_caps = []
    for idx in indices:
        horse_name = str(rdf.loc[idx, '馬名']).strip()
        pr  = horse_place_rate.get(horse_name, None)
        cap = pr / 3.0 if pr is not None else 1.0
        win_caps.append(cap)
    win_caps = np.array(win_caps)

    capped = np.minimum(softmax_probs, win_caps)
    total  = capped.sum()
    if total < 1e-9:
        capped = softmax_probs
    else:
        capped = capped / total

    return {idx: float(p) for idx, p in zip(indices, capped)}


# ============================================================
# 4. バックテスト実行
# ============================================================
print("\n■ バックテスト実行中（全重賞）...")
race_groups = grade_df.groupby('race_key')
total_races = len(race_groups)
print(f"  対象レース数: {total_races:,}R")

race_records = []

for i, (race_key, rdf) in enumerate(race_groups):
    if i % 300 == 0:
        print(f"  進捗: {i:,}/{total_races:,}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3:
        continue
    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue

    actual_1st = str(winner_rows.iloc[0]['馬名']).strip()

    year  = int(race_key.split('_')[0]) if '_' in race_key else 0
    meta  = valid.iloc[0]
    grade_label = str(rdf.iloc[0]['grade'])
    dist_val    = int(meta['距離']) if pd.notna(meta['距離']) else 0
    venue       = str(meta['場所']).strip()

    # 馬場状態
    track_cond = str(meta.get('馬場状態', '')).strip() if pd.notna(meta.get('馬場状態', '')) else ''
    surface_val = str(meta.get('surface', '')).strip()

    scores    = score_race_4teams(valid)
    win_probs = score_to_win_prob(scores, valid)

    best_idx  = max(scores, key=scores.get)
    best_row  = valid.loc[best_idx]
    pred_name = str(best_row['馬名']).strip()
    pred_pop  = int(best_row['人気順'])
    pred_odds = float(best_row['単勝オッズ_num'])
    pred_ep   = win_probs.get(best_idx, 0.0)
    pred_edge = pred_ep - (1.0 / pred_odds * 0.80) if pred_odds > 0 else None

    race_records.append({
        'race_key':   race_key,
        'year':       year,
        'grade':      grade_label,
        'venue':      venue,
        'distance':   dist_val,
        'dist_band':  dist_band(dist_val),
        'track_cond': track_cond,
        'surface':    surface_val,
        'hit':        (pred_name == actual_1st),
        'pred_pop':   pred_pop,
        'pred_odds':  pred_odds,
        'pred_ep':    pred_ep,
        'pred_edge':  pred_edge,
    })

df_race  = pd.DataFrame(race_records)
train_r  = df_race[df_race['year'] <= TRAIN_YEAR_MAX].copy()
test_r   = df_race[df_race['year'] >= TEST_YEAR_MIN].copy()

print(f"\n  レースレコード: 訓練{len(train_r):,}R・検証{len(test_r):,}R")


# ============================================================
# Step 1: 閾値別の回収率・的中率（訓練データ）
# ============================================================
print(f"\n\n{SEP}")
print("【Step 1】閾値別 回収率・的中率（訓練データ 2015〜2023 重賞）")
print(SEP)

print(f"\n訓練データ: {len(train_r):,}R")
base_train_hit = train_r['hit'].mean() * 100
base_train_rec = race_recovery(train_r)
print(f"ベースライン: 的中率{base_train_hit:.1f}%  単勝回収率{base_train_rec:.1f}%\n")

train_threshold_results = []

print(f"{'閾値':>8s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}  "
      f"{'黒字年率':>8s}  {'カバレッジ':>10s}  {'平均人気':>8s}  {'平均オッズ':>9s}")
print("-" * 80)

for th in THRESHOLDS:
    sub = train_r[train_r['pred_edge'].notna() & (train_r['pred_edge'] >= th)]
    if len(sub) == 0:
        print(f"{th:+.2f}以上  {'0':>5s}  {'  -':>7s}  {'  -':>10s}  {'  -':>8s}  {'  -':>10s}")
        train_threshold_results.append({'threshold': th, 'n': 0, 'hit': 0, 'rec': 0, 'black': 0})
        continue
    hr   = sub['hit'].mean() * 100
    rec  = race_recovery(sub)
    cov  = len(sub) / len(train_r) * 100
    avgp = sub['pred_pop'].mean()
    avgo = sub['pred_odds'].mean()
    black_rate, _ = yearly_black_rate(sub)
    print(f"{th:+.2f}以上  {len(sub):>5,d}  {hr:>6.1f}%  {rec:>9.1f}%  "
          f"{black_rate:>7.0f}%  {cov:>9.1f}%  {avgp:>7.1f}番  {avgo:>8.1f}倍")
    train_threshold_results.append({
        'threshold': th, 'n': len(sub), 'hit': hr, 'rec': rec,
        'black': black_rate, 'cov': cov
    })

# 年別詳細（各閾値）
print(f"\n── 年別黒字率の詳細（訓練データ）──")
for th in THRESHOLDS:
    sub = train_r[train_r['pred_edge'].notna() & (train_r['pred_edge'] >= th)]
    if len(sub) == 0:
        continue
    _, detail = yearly_black_rate(sub)
    years_str = "  ".join([f"{yr}:{rec:.0f}%" for yr, n, rec in detail])
    black_cnt = sum(1 for _, _, rec in detail if rec >= 100)
    print(f"  {th:+.2f}以上  黒字{black_cnt}/{len(detail)}年  [{years_str}]")


# ============================================================
# Step 2: 検証データ（2024〜2026）でのトップ3閾値確認
# ============================================================
print(f"\n\n{SEP}")
print("【Step 2】検証データ（2024〜2026 重賞）でのトップ3閾値確認")
print(SEP)

# 訓練データで回収率順にソートしトップ3を特定
valid_results = [r for r in train_threshold_results if r['n'] >= 5]
sorted_by_rec = sorted(valid_results, key=lambda x: x['rec'], reverse=True)
top3_thresholds = [r['threshold'] for r in sorted_by_rec[:3]]

print(f"\n訓練データでの回収率上位3閾値: {[f'+{th:.2f}' for th in top3_thresholds]}")
print(f"\n検証データ: {len(test_r):,}R")
base_test_hit = test_r['hit'].mean() * 100
base_test_rec = race_recovery(test_r)
print(f"ベースライン: 的中率{base_test_hit:.1f}%  単勝回収率{base_test_rec:.1f}%\n")

print(f"{'閾値':>8s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}  "
      f"{'黒字年率':>8s}  {'カバレッジ':>10s}  {'訓練との差':>10s}")
print("-" * 75)

# まず全閾値を表示（訓練との差が見えるように）
for item in train_threshold_results:
    th = item['threshold']
    sub = test_r[test_r['pred_edge'].notna() & (test_r['pred_edge'] >= th)]
    if len(sub) == 0:
        marker = '★' if th in top3_thresholds else ' '
        print(f"{marker}{th:+.2f}以上  {'0':>5s}  {'  -':>7s}  {'  -':>10s}  {'  -':>8s}")
        continue
    hr   = sub['hit'].mean() * 100
    rec  = race_recovery(sub)
    cov  = len(sub) / len(test_r) * 100
    black_rate, _ = yearly_black_rate(sub)
    diff_rec = rec - item['rec'] if item['n'] > 0 else 0
    marker = '★' if th in top3_thresholds else ' '
    diff_str = f"{diff_rec:+.1f}%" if item['n'] > 0 else "  N/A"
    print(f"{marker}{th:+.2f}以上  {len(sub):>5,d}  {hr:>6.1f}%  {rec:>9.1f}%  "
          f"{black_rate:>7.0f}%  {cov:>9.1f}%  {diff_str:>10s}")

# 検証データの年別詳細（トップ3閾値）
print(f"\n── トップ3閾値の年別詳細（検証データ 2024〜2026）──")
for th in top3_thresholds:
    sub = test_r[test_r['pred_edge'].notna() & (test_r['pred_edge'] >= th)]
    if len(sub) == 0:
        continue
    _, detail = yearly_black_rate(sub)
    years_str = "  ".join([f"{yr}:{rec:.0f}%（{n}R）" for yr, n, rec in detail])
    black_cnt = sum(1 for _, _, rec in detail if rec >= 100)
    print(f"  {th:+.2f}以上  黒字{black_cnt}/{len(detail)}年  [{years_str}]")

# 距離帯別（トップ3閾値、検証データ）
print(f"\n── トップ3閾値 × 距離帯別（検証データ）──")
print(f"{'閾値':>8s}  {'距離帯':15s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}")
print("-" * 55)
for th in top3_thresholds:
    for db in ['〜1400m', '1600〜2000m', '2200m〜']:
        sub = test_r[
            test_r['pred_edge'].notna() &
            (test_r['pred_edge'] >= th) &
            (test_r['dist_band'] == db)
        ]
        if len(sub) == 0:
            continue
        hr  = sub['hit'].mean() * 100
        rec = race_recovery(sub)
        print(f"{th:+.2f}以上  {db:15s}  {len(sub):>5,d}  {hr:>6.1f}%  {rec:>9.1f}%")
    print()


# ============================================================
# Step 3: 穴馬戦略 × 各閾値の組み合わせ
# ============================================================
print(f"\n{SEP}")
print("【Step 3】穴馬戦略（◎4番人気以上×距離2200m未満）× 各閾値")
print(SEP)

anaba_base_train = train_r[(train_r['pred_pop'] >= 4) & (train_r['distance'] < 2200)]
anaba_base_test  = test_r[(test_r['pred_pop'] >= 4) & (test_r['distance'] < 2200)]

print(f"\n穴馬戦略ベース（フィルターなし）")
print(f"  訓練: {len(anaba_base_train):,}R  的中率{anaba_base_train['hit'].mean()*100:.1f}%"
      f"  回収率{race_recovery(anaba_base_train):.1f}%")
print(f"  検証: {len(anaba_base_test):,}R  的中率{anaba_base_test['hit'].mean()*100:.1f}%"
      f"  回収率{race_recovery(anaba_base_test):.1f}%\n")

print(f"{'閾値':>8s}  "
      f"{'訓練N':>6s}  {'訓練的中率':>9s}  {'訓練回収率':>9s}  "
      f"{'検証N':>6s}  {'検証的中率':>9s}  {'検証回収率':>9s}")
print("-" * 75)

combo_results = []
for th in THRESHOLDS:
    st = anaba_base_train[anaba_base_train['pred_edge'].notna() & (anaba_base_train['pred_edge'] >= th)]
    sv = anaba_base_test[anaba_base_test['pred_edge'].notna() & (anaba_base_test['pred_edge'] >= th)]
    tr_hit = st['hit'].mean() * 100 if len(st) > 0 else 0.0
    tr_rec = race_recovery(st)
    te_hit = sv['hit'].mean() * 100 if len(sv) > 0 else 0.0
    te_rec = race_recovery(sv)
    combo_results.append({'threshold': th, 'train_n': len(st), 'train_rec': tr_rec,
                          'test_n': len(sv), 'test_rec': te_rec})
    print(f"{th:+.2f}以上  {len(st):>6,d}  {tr_hit:>8.1f}%  {tr_rec:>8.1f}%  "
          f"{len(sv):>6,d}  {te_hit:>8.1f}%  {te_rec:>8.1f}%")

# 年間ベット数の試算
print(f"\n── 穴馬戦略 × 閾値別 年間ベット数試算 ──")
test_years = sorted(test_r['year'].unique())
n_years = max(1, len(test_years))
train_years = sorted(train_r['year'].unique())
n_train_years = max(1, len(train_years))
print(f"  (訓練期間:{n_train_years}年 / 検証期間:{n_years}年)")
for cr in combo_results:
    th  = cr['threshold']
    ann_tr = cr['train_n'] / n_train_years
    ann_te = cr['test_n']  / n_years
    print(f"  {th:+.2f}以上  訓練年間約{ann_tr:.0f}R  検証年間約{ann_te:.0f}R")


# ============================================================
# Step 4: 阪神稍重 +0.07引き上げルールの検証
# ============================================================
print(f"\n\n{SEP}")
print("【Step 4】阪神稍重 エッジ閾値+0.07引き上げルールの検証")
print(SEP)

# 阪神×稍重の重賞を抽出
# 馬場状態コード: 良=1/稍重=2/重=3/不良=4 または文字列での格納
# 「稍」を含む場合を稍重として扱う
hanshin_df = df_race[df_race['venue'].str.contains('阪神', na=False)].copy()
hanshin_df['is_yaや'] = hanshin_df['track_cond'].astype(str).str.contains('稍|2', na=False)
hanshin_df['is_good'] = hanshin_df['track_cond'].astype(str).str.contains('良|1', na=False)

print(f"\n阪神開催 重賞レコード: {len(hanshin_df):,}R")
print(f"  馬場状態の分布:")
for cond in hanshin_df['track_cond'].value_counts().head(10).index:
    cnt = (hanshin_df['track_cond'] == cond).sum()
    print(f"    '{cond}': {cnt}R")

# 馬場状態別に分類
# track_condの値を確認してフィルタを調整
# 文字列「稍重」または数値「2」を対応
def is_yaや(cond):
    s = str(cond).strip()
    return '稍' in s or s == '2'

def is_heavy(cond):
    s = str(cond).strip()
    return ('重' in s and '稍' not in s) or s == '3'

def is_good_cond(cond):
    s = str(cond).strip()
    return s == '良' or s == '1'

hanshin_df['cond_cat'] = hanshin_df['track_cond'].apply(
    lambda c: '稍重' if is_yaや(c) else
              ('重' if is_heavy(c) else
               ('良' if is_good_cond(c) else 'その他'))
)

# 全期間（訓練+検証）で阪神別
print(f"\n── 阪神重賞：馬場状態×閾値別 単勝回収率 ──")
print(f"\n{'馬場':>5s}  {'閾値':>8s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}  {'備考':s}")
print("-" * 60)
for cond_label in ['良', '稍重', '重']:
    sub_cond = hanshin_df[hanshin_df['cond_cat'] == cond_label]
    if len(sub_cond) == 0:
        continue
    # ベースライン
    base_hr  = sub_cond['hit'].mean() * 100
    base_rec = race_recovery(sub_cond)
    print(f"{cond_label:>5s}  {'全体':>8s}  {len(sub_cond):>5,d}  "
          f"{base_hr:>6.1f}%  {base_rec:>9.1f}%  （閾値なし）")
    for th in [0.05, 0.06, 0.07, 0.08]:
        sub_th = sub_cond[sub_cond['pred_edge'].notna() & (sub_cond['pred_edge'] >= th)]
        if len(sub_th) == 0:
            continue
        hr  = sub_th['hit'].mean() * 100
        rec = race_recovery(sub_th)
        note = ' ← 現行' if th == 0.05 else (' ← 提案' if th == 0.07 else '')
        print(f"{cond_label:>5s}  {th:+.2f}以上  {len(sub_th):>5,d}  "
              f"{hr:>6.1f}%  {rec:>9.1f}%{note}")
    print()

# 阪神稍重 vs 他会場稍重 の比較
print(f"── 阪神稍重 vs 他会場稍重 比較（全期間）──")
other_yaや = df_race[
    ~df_race['venue'].str.contains('阪神', na=False) &
    df_race['track_cond'].apply(is_yaや)
]
hanshin_yaや = hanshin_df[hanshin_df['cond_cat'] == '稍重']

print(f"\n{'対象':15s}  {'N':>5s}  {'ベース回収率':>12s}  {'+0.05回収率':>12s}  {'+0.07回収率':>12s}")
print("-" * 60)
for label, sub in [('阪神稍重', hanshin_yaや), ('他会場稍重', other_yaや)]:
    if len(sub) == 0:
        continue
    rec_base = race_recovery(sub)
    s05 = sub[sub['pred_edge'].notna() & (sub['pred_edge'] >= 0.05)]
    s07 = sub[sub['pred_edge'].notna() & (sub['pred_edge'] >= 0.07)]
    rec05 = race_recovery(s05) if len(s05) > 0 else 0.0
    rec07 = race_recovery(s07) if len(s07) > 0 else 0.0
    print(f"{label:15s}  {len(sub):>5,d}  {rec_base:>11.1f}%  {rec05:>11.1f}%  {rec07:>11.1f}%")

# 阪神稍重の年別詳細（+0.05 vs +0.07）
print(f"\n── 阪神稍重 +0.05 vs +0.07 年別比較 ──")
print(f"\n{'年':>5s}  {'全体N':>6s}  {'全体回収率':>10s}  "
      f"{'+0.05N':>7s}  {'+0.05回収率':>10s}  "
      f"{'+0.07N':>7s}  {'+0.07回収率':>10s}")
print("-" * 65)
if len(hanshin_yaや) > 0:
    for yr in sorted(hanshin_yaや['year'].unique()):
        ysub = hanshin_yaや[hanshin_yaや['year'] == yr]
        y05  = ysub[ysub['pred_edge'].notna() & (ysub['pred_edge'] >= 0.05)]
        y07  = ysub[ysub['pred_edge'].notna() & (ysub['pred_edge'] >= 0.07)]
        rec_base = race_recovery(ysub)
        rec05    = race_recovery(y05) if len(y05) > 0 else 0.0
        rec07    = race_recovery(y07) if len(y07) > 0 else 0.0
        print(f"{yr:>5d}  {len(ysub):>6,d}  {rec_base:>9.1f}%  "
              f"{len(y05):>7,d}  {rec05:>9.1f}%  "
              f"{len(y07):>7,d}  {rec07:>9.1f}%")


# ============================================================
# Step 5: 結論
# ============================================================
print(f"\n\n{SEP}")
print("【Step 5】結論")
print(SEP)

# 全閾値の訓練・検証の比較サマリー
print(f"\n■ 全閾値 訓練→検証 回収率サマリー（エッジ値フィルター単体）\n")
print(f"{'閾値':>8s}  {'訓練N':>6s}  {'訓練回収率':>10s}  "
      f"{'検証N':>6s}  {'検証回収率':>10s}  {'方向整合':>8s}  {'推奨度':s}")
print("-" * 70)

recommendations = []
for item in train_threshold_results:
    th = item['threshold']
    sub_v = test_r[test_r['pred_edge'].notna() & (test_r['pred_edge'] >= th)]
    te_rec = race_recovery(sub_v) if len(sub_v) > 0 else 0.0
    te_n   = len(sub_v)
    tr_rec = item['rec']
    tr_n   = item['n']

    # 方向整合: 訓練>検証でも両方>ベース（150%以上）なら整合あり
    both_over = (tr_rec > 150) and (te_rec > 150)
    direction = '✓' if both_over else ('△' if te_rec > base_test_rec else '✗')

    # 推奨度
    if te_rec >= 200 and te_n >= 10 and both_over:
        recmd = '★★★ 強推奨'
    elif te_rec >= 150 and te_n >= 10 and te_rec > base_test_rec:
        recmd = '★★  推奨'
    elif te_rec >= 130 and te_n >= 5:
        recmd = '★   採用検討'
    else:
        recmd = '    見送り'

    recommendations.append({'threshold': th, 'train_rec': tr_rec, 'test_rec': te_rec,
                             'test_n': te_n, 'direction': direction, 'recmd': recmd})
    print(f"{th:+.2f}以上  {tr_n:>6,d}  {tr_rec:>9.1f}%  "
          f"{te_n:>6,d}  {te_rec:>9.1f}%  {direction:>8s}  {recmd}")

# 穴馬戦略との組み合わせサマリー
print(f"\n■ 穴馬戦略（◎4番人気以上×距離2200m未満）× 閾値 サマリー\n")
anaba_base_train_rec = race_recovery(anaba_base_train)
anaba_base_test_rec  = race_recovery(anaba_base_test)
print(f"穴馬戦略ベース: 訓練{anaba_base_train_rec:.1f}%  検証{anaba_base_test_rec:.1f}%\n")

print(f"{'閾値':>8s}  {'訓練N':>5s}  {'訓練回収率':>10s}  "
      f"{'検証N':>5s}  {'検証回収率':>10s}  {'訓練比':>8s}  {'検証比':>8s}")
print("-" * 65)
for cr in combo_results:
    th = cr['threshold']
    tr_diff = cr['train_rec'] - anaba_base_train_rec
    te_diff = cr['test_rec']  - anaba_base_test_rec
    sv = anaba_base_test[anaba_base_test['pred_edge'].notna() & (anaba_base_test['pred_edge'] >= th)]
    te_hit = sv['hit'].mean() * 100 if len(sv) > 0 else 0.0
    st = anaba_base_train[anaba_base_train['pred_edge'].notna() & (anaba_base_train['pred_edge'] >= th)]
    tr_hit = st['hit'].mean() * 100 if len(st) > 0 else 0.0
    print(f"{th:+.2f}以上  {cr['train_n']:>5,d}  {cr['train_rec']:>9.1f}%  "
          f"{cr['test_n']:>5,d}  {cr['test_rec']:>9.1f}%  "
          f"{tr_diff:>+7.1f}%  {te_diff:>+7.1f}%")

# 阪神稍重ルールの判定
print(f"\n■ 阪神稍重 閾値引き上げルールの判定\n")
hanshin_yaや_all = hanshin_df[hanshin_df['cond_cat'] == '稍重']
if len(hanshin_yaや_all) > 0:
    base_rec_hy  = race_recovery(hanshin_yaや_all)
    s05_hy = hanshin_yaや_all[hanshin_yaや_all['pred_edge'].notna() &
                               (hanshin_yaや_all['pred_edge'] >= 0.05)]
    s07_hy = hanshin_yaや_all[hanshin_yaや_all['pred_edge'].notna() &
                               (hanshin_yaや_all['pred_edge'] >= 0.07)]
    rec05_hy = race_recovery(s05_hy) if len(s05_hy) > 0 else 0.0
    rec07_hy = race_recovery(s07_hy) if len(s07_hy) > 0 else 0.0
    print(f"  阪神稍重 全体: {len(hanshin_yaや_all):,}R  ベース回収率 {base_rec_hy:.1f}%")
    print(f"  阪神稍重 +0.05以上: {len(s05_hy):,}R  回収率 {rec05_hy:.1f}%")
    print(f"  阪神稍重 +0.07以上: {len(s07_hy):,}R  回収率 {rec07_hy:.1f}%")
    if rec07_hy > rec05_hy and rec07_hy > base_rec_hy:
        print(f"  → ✅ +0.07引き上げルール: 有効（+{rec07_hy-rec05_hy:.1f}%改善）")
    elif rec05_hy > rec07_hy:
        print(f"  → ⚠️  +0.05の方が高い（引き上げ不要の可能性）")
    else:
        print(f"  → ⚠️  サンプル不足または差が小さい（様子見）")
else:
    print("  阪神稍重の重賞データが見つかりませんでした")

# 最終推奨
print(f"\n■ 最終推奨\n")
best_single = max(recommendations, key=lambda x: x['test_rec'] if x['test_n'] >= 5 else 0)
best_combo  = max(combo_results, key=lambda x: x['test_rec'] if x['test_n'] >= 5 else 0)

print(f"  エッジ値フィルター単体  最適閾値: {best_single['threshold']:+.2f}以上")
print(f"    訓練回収率: {best_single['train_rec']:.1f}%  検証回収率: {best_single['test_rec']:.1f}%")
print(f"    評価: {best_single['recmd']}")
print()
print(f"  穴馬戦略との組み合わせ  最適閾値: {best_combo['threshold']:+.2f}以上")
print(f"    訓練回収率: {best_combo['train_rec']:.1f}%  検証回収率: {best_combo['test_rec']:.1f}%")
print()
print(f"  現行閾値（+0.05）との比較:")
current = next((r for r in recommendations if abs(r['threshold'] - 0.05) < 0.001), None)
if current:
    print(f"    現行  訓練{current['train_rec']:.1f}%  検証{current['test_rec']:.1f}%")
if best_single['threshold'] != 0.05:
    print(f"    最適  訓練{best_single['train_rec']:.1f}%  検証{best_single['test_rec']:.1f}%")
    if best_single['test_rec'] > (current['test_rec'] if current else 0) + 10:
        print(f"    → ★ 変更推奨（+{best_single['test_rec']-(current['test_rec'] if current else 0):.1f}%改善）")
    elif best_single['test_rec'] > (current['test_rec'] if current else 0):
        print(f"    → △ わずかに改善（+{best_single['test_rec']-(current['test_rec'] if current else 0):.1f}%）"
              f"。サンプル数を考慮して判断")
    else:
        print(f"    → 現行+0.05を維持推奨（最適閾値の検証データ優位が確認できない）")
else:
    print(f"    → ✅ 現行+0.05が最適（変更不要）")

print(f"\n{SEP}")
print("■ 完了")
print(SEP)
