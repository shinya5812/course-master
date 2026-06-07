# -*- coding: utf-8 -*-
"""
backtest_distance_rule.py
距離別エッジ精度の検証

【目的】
  現行の「長距離2200m超は見送り」ルールの妥当性を再検証する。
  2024〜2026年の重賞データで、距離帯別の◎的中率・回収率を集計し、
  除外ルールの維持／緩和／強化の推奨を出力する。

使い方:
  python backtest_distance_rule.py
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
    os.path.join(BASE_DIR, 'data', 'race', '結果202604110419.csv'),
]

TEMPERATURE    = 5.0
BET_UNIT       = 100
EDGE_THRESHOLD = 0.06
GRADE_PAT      = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
TEST_YEAR_MIN  = 24


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


def dist_band_fine(d):
    """詳細距離帯（検証用）"""
    if d <= 0:
        return '不明'
    elif d <= 1400:
        return '〜1400m'
    elif d <= 1800:
        return '1401〜1800m'
    elif d <= 2000:
        return '1801〜2000m'
    elif d <= 2200:
        return '2001〜2200m'
    elif d <= 2400:
        return '2201〜2400m'
    else:
        return '2401m〜'


# pkl 読み込み
print("■ pkl 読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

sire_stats      = state.get('sire_stats', {})
jockey_stats    = state.get('jockey_stats', {})
distance_stats  = state.get('distance_stats', {})
career_penalty  = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
odds_mk_table   = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]
print(f"  sire_stats:{len(sire_stats)}件  jockey_stats:{len(jockey_stats)}件")

# CSV 読み込み
print("\n■ CSV 読み込み中...")
dfs = []
for fpath in CSV_FILES:
    if os.path.exists(fpath):
        dfs.append(pd.read_csv(fpath, encoding='cp932', low_memory=False))
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

print("■ 血統データ読み込み...")
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
    name = str(brow['馬名']).strip()
    total = (brow['全成績1着数'] + brow['全成績2着数'] +
             brow['全成績3着数'] + brow['全成績着外数'])
    if total >= 5:
        placed = brow['全成績1着数'] + brow['全成績2着数'] + brow['全成績3着数']
        horse_place_rate[name] = float(placed) / float(total)

# 重賞抽出
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
grade_df['year_2d'] = grade_df['年'].astype(str).str[-2:].astype(int)


# スコア計算
def score_horse(row, team_type='I'):
    axes = {}
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

    agari = row['上がり3Fタイム_sec']
    axes['SI'] = max(10, 100 - (agari - 30) * 2) if pd.notna(agari) else 50

    jockey = row['騎手名']
    axes['JT'] = min(100, jockey_stats[jockey]['win_rate'] * 100) if pd.notna(jockey) and jockey in jockey_stats else 50

    passages = [row.get('通過順1'), row.get('通過順2'), row.get('通過順3'), row.get('通過順4')]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    axes['PD'] = max(10, 100 - abs(np.mean(passages) - 7) * 3) if passages else 50

    pop = int(row['人気順'])
    axes['BL'] = max(10, 100 - pop * 5) if pop > 0 else 50

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
    return float(np.average([axes[k] for k in keys], weights=[W.get(k, 1.0) for k in keys]))


def score_race_4teams(rdf):
    teams = ['I', 'O', 'U', 'S']
    team_scores = {t: {} for t in teams}
    for t in teams:
        for idx, row in rdf.iterrows():
            try:
                team_scores[t][idx] = score_horse(row, t)
            except Exception:
                team_scores[t][idx] = 50.0
    return {idx: float(np.mean([team_scores[t][idx] for t in teams])) for idx in rdf.index}


def score_to_win_prob(scores_dict, rdf):
    indices   = list(scores_dict.keys())
    score_arr = np.array([scores_dict[i] for i in indices])
    shifted   = score_arr - score_arr.max()
    sp = np.exp(shifted / TEMPERATURE)
    sp = sp / sp.sum()
    win_caps = []
    for idx in indices:
        pr = horse_place_rate.get(str(rdf.loc[idx, '馬名']).strip(), None)
        win_caps.append(pr / 3.0 if pr is not None else 1.0)
    win_caps = np.array(win_caps)
    capped = np.minimum(sp, win_caps)
    total  = capped.sum()
    capped = capped / total if total > 1e-9 else sp
    return {idx: float(p) for idx, p in zip(indices, capped)}


# ============================================================
# バックテスト（全期間 + テスト期間で並行実施）
# ============================================================
print("\n■ バックテスト実行中（全期間・詳細距離帯）...")

# 全期間: 距離帯別 ◎単勝 無条件（エッジフィルターなし）
all_races_stats = defaultdict(lambda: {'n':0,'hits':0,'inv':0,'ret':0})
# テスト期間 2024〜: エッジ+0.06フィルターあり
test_edge_stats = defaultdict(lambda: {'n':0,'hits':0,'inv':0,'ret':0})

# 全期間: 2200m超 詳細分析
long_detail = defaultdict(lambda: {'n':0,'hits':0,'inv':0,'ret':0,'year_hits':defaultdict(int),'year_n':defaultdict(int)})

for period, df_use in [('ALL', grade_df), ('TEST', grade_df[grade_df['year_2d'] >= TEST_YEAR_MIN])]:
    race_groups = df_use.groupby('race_key')
    total = len(race_groups)
    print(f"  [{period}] {total}R...")

    for i, (race_key, rdf) in enumerate(race_groups):
        if i % 300 == 0 and i > 0:
            print(f"    進捗: {i}/{total}...")

        valid = rdf[rdf['確定着順'] > 0].copy()
        if len(valid) < 3 or valid[valid['確定着順'] == 1].empty:
            continue

        year     = int(race_key.split('_')[0])
        dist_val = int(valid.iloc[0]['距離']) if pd.notna(valid.iloc[0]['距離']) else 0
        band     = dist_band_fine(dist_val)
        grade_lbl = str(rdf.iloc[0]['grade'])

        scores    = score_race_4teams(valid)
        win_probs = score_to_win_prob(scores, valid)

        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        if not sorted_scores:
            continue

        honmei_idx = sorted_scores[0][0]
        honmei_row = valid.loc[honmei_idx]
        raw_odds   = float(honmei_row['単勝オッズ_num'])
        if raw_odds <= 0:
            continue

        market_prob = (1.0 / raw_odds) * 0.80
        wp          = win_probs.get(honmei_idx, 0.0)
        edge        = wp - market_prob
        hit         = int(honmei_row['確定着順']) == 1

        # 全期間・エッジフィルターなし（純粋な距離帯別◎単勝）
        if period == 'ALL':
            ret = raw_odds * BET_UNIT if hit else 0
            all_races_stats[band]['n']    += 1
            all_races_stats[band]['hits'] += int(hit)
            all_races_stats[band]['inv']  += BET_UNIT
            all_races_stats[band]['ret']  += ret

            # 2200m超の詳細（グレード×年別）
            if dist_val >= 2200:
                key2 = f"{grade_lbl}"
                long_detail[key2]['n']    += 1
                long_detail[key2]['hits'] += int(hit)
                long_detail[key2]['inv']  += BET_UNIT
                long_detail[key2]['ret']  += ret
                long_detail[key2]['year_hits'][year] += int(hit)
                long_detail[key2]['year_n'][year]    += 1

        # テスト期間・エッジフィルターあり
        if period == 'TEST' and edge >= EDGE_THRESHOLD:
            ret = raw_odds * BET_UNIT if hit else 0
            test_edge_stats[band]['n']    += 1
            test_edge_stats[band]['hits'] += int(hit)
            test_edge_stats[band]['inv']  += BET_UNIT
            test_edge_stats[band]['ret']  += ret


# ============================================================
# 出力
# ============================================================
print("\n" + "="*60)
print("【全期間（2015〜2026）距離帯別 ◎単勝 無条件】")
print("="*60)
bands_order = ['〜1400m','1401〜1800m','1801〜2000m','2001〜2200m','2201〜2400m','2401m〜']
for band in bands_order:
    d = all_races_stats.get(band)
    if d and d['n'] > 0:
        roi = d['ret'] / d['inv'] * 100
        wr  = d['hits'] / d['n'] * 100
        note = "← 除外対象" if band in ('2201〜2400m','2401m〜') else ""
        print(f"  {band:15s}: {d['n']:4d}R  的中率{wr:5.1f}%  ROI={roi:6.1f}%  {note}")

print("\n" + "="*60)
print("【テスト期間（2024〜2026）エッジ+0.06以上 × 距離帯別】")
print("="*60)
for band in bands_order:
    d = test_edge_stats.get(band)
    if d and d['n'] > 0:
        roi = d['ret'] / d['inv'] * 100
        wr  = d['hits'] / d['n'] * 100
        note = "← 除外対象" if band in ('2201〜2400m','2401m〜') else ""
        print(f"  {band:15s}: {d['n']:3d}R  的中率{wr:5.1f}%  ROI={roi:6.1f}%  {note}")

# 2200m超の年別詳細
print("\n" + "="*60)
print("【全期間 2200m超 グレード×年別詳細（除外判断の根拠確認）】")
print("="*60)
for gk in ['G1','G2','G3']:
    d = long_detail.get(gk)
    if d and d['n'] > 0:
        roi = d['ret'] / d['inv'] * 100
        wr  = d['hits'] / d['n'] * 100
        print(f"\n  {gk} ({d['n']}R  的中率{wr:.1f}%  ROI={roi:.1f}%)")
        # 年別
        for y in sorted(d['year_n'].keys()):
            yn = d['year_n'][y]
            yh = d['year_hits'][y]
            yr = (yh * raw_odds / yn) * 100 if yn > 0 else 0  # 粗い近似
            print(f"    {y}年: {yn}R  的中{yh}回")

# ────────────────────────────────────────
# エッジ+0.06フィルター × 全距離帯 比較サマリー
# ────────────────────────────────────────
print("\n" + "="*60)
print("【テスト期間: 2200m未満 vs 2200m以上 エッジ+0.06フィルター比較】")
print("="*60)

under2200  = {'n':0,'hits':0,'inv':0,'ret':0}
over2200   = {'n':0,'hits':0,'inv':0,'ret':0}
for band, d in test_edge_stats.items():
    if band in ('2201〜2400m','2401m〜'):
        for k in under2200:
            over2200[k] += d[k]
    else:
        for k in under2200:
            under2200[k] += d[k]

for label, d in [('2200m未満（採用対象）', under2200), ('2200m以上（除外対象）', over2200)]:
    if d['inv'] > 0:
        roi = d['ret'] / d['inv'] * 100
        wr  = d['hits'] / d['n'] * 100 if d['n'] > 0 else 0
        print(f"  {label}: {d['n']}R  的中率{wr:.1f}%  ROI={roi:.1f}%")

# ────────────────────────────────────────
# 境界線の精緻化（2001〜2200m の精度確認）
# ────────────────────────────────────────
print("\n" + "="*60)
print("【境界帯（2001〜2200m）の詳細確認 — 緩和の余地があるか？】")
print("="*60)

band_2001_2200 = test_edge_stats.get('2001〜2200m', {})
if band_2001_2200 and band_2001_2200.get('n', 0) > 0:
    d = band_2001_2200
    roi = d['ret'] / d['inv'] * 100
    wr  = d['hits'] / d['n'] * 100
    print(f"  2001〜2200m（テスト）: {d['n']}R  的中率{wr:.1f}%  ROI={roi:.1f}%")
    if roi >= 150:
        print("  → ✅ ROI150%超: 2001〜2200mは採用検討の余地あり")
    elif roi >= 100:
        print("  → △ ROI100〜150%: 採用には更なるデータ蓄積が必要")
    else:
        print("  → ✗ ROI100%未満: 2200m以下でも2001〜2200mは慎重に")
else:
    print("  2001〜2200mのテストデータ（エッジ+0.06以上）なし")

# ============================================================
# 最終推奨
# ============================================================
print("\n" + "="*60)
print("【最終推奨】")
print("="*60)

under2200_roi = under2200['ret'] / under2200['inv'] * 100 if under2200['inv'] > 0 else 0
over2200_roi  = over2200['ret']  / over2200['inv']  * 100 if over2200['inv']  > 0 else 0

print(f"  2200m未満: ROI {under2200_roi:.1f}%")
print(f"  2200m以上: ROI {over2200_roi:.1f}%")

diff = under2200_roi - over2200_roi
print(f"  差分: {diff:+.1f}%")

if over2200_roi >= 100:
    print("\n  → ⚠️ 2200m以上も100%超: 除外ルール緩和を検討")
elif over2200_roi >= 80:
    print("\n  → △ 2200m以上は80〜100%: 現行除外ルール維持（様子見）")
else:
    print("\n  → ✅ 2200m以上は80%未満: 現行除外ルール（2200m超見送り）を維持")
