# -*- coding: utf-8 -*-
"""
hypothesis_c_test.py  -  仮説C: エッジ値（エンジン推定勝率 vs 市場確率）の予測力検証

【定義】
  市場確率  = 1 / 単勝オッズ × 0.80（控除率20%補正）
  エンジン推定勝率 = スコア → softmax変換（temperature=5.0）+ place_rateキャップ
  エッジ値  = エンジン推定勝率 - 市場確率
  ※ エッジ値がプラス = 市場が過小評価している馬

【検証ステップ】
  Step 1: エッジ値の分布確認（訓練データ 2015〜2023年）
  Step 2: エッジ値閾値別の単勝回収率（訓練データ）
  Step 3: 現行◎との組み合わせ効果（検証データ 2024〜2026年）
  Step 4: 結論・穴馬戦略との組み合わせ試算

使い方:
  python hypothesis_c_test.py
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

TEMPERATURE = 5.0   # softmax温度（エンジンと同値）
BET_UNIT    = 100   # 1ベット（円）
GRADE_PAT   = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')

# 訓練/検証分割（年は西暦下2桁: 2023→23, 2024→24）
TRAIN_YEAR_MAX = 23
TEST_YEAR_MIN  = 24


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

# place_rate用：馬ごとの複勝率辞書を血統CSVから事前構築
horse_place_rate = {}
for _, brow in df_blood.iterrows():
    name = str(brow['馬名']).strip()
    total = (brow['全成績1着数'] + brow['全成績2着数'] +
             brow['全成績3着数'] + brow['全成績着外数'])
    if total >= 5:
        placed = brow['全成績1着数'] + brow['全成績2着数'] + brow['全成績3着数']
        horse_place_rate[name] = float(placed) / float(total)

print(f"  place_rate取得馬数: {len(horse_place_rate):,}頭")

# 重賞抽出
df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None)
grade_df = df_all[df_all['grade'].notna()].copy()

# レースキー
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
# 3. スコア計算（v7.3 エンジン 4チーム合議 忠実再現）
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
    """4チーム平均スコア {idx: float}"""
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
    """
    スコア → 推定勝率（softmax + place_rateキャップ）
    エンジンの score_to_win_prob と同一ロジック（temperature=5.0）
    """
    indices   = list(scores_dict.keys())
    score_arr = np.array([scores_dict[i] for i in indices])

    # softmax
    shifted       = score_arr - score_arr.max()
    softmax_probs = np.exp(shifted / TEMPERATURE)
    softmax_probs = softmax_probs / softmax_probs.sum()

    # place_rate からキャップ
    win_caps = []
    for idx in indices:
        horse_name = str(rdf.loc[idx, '馬名']).strip()
        pr = horse_place_rate.get(horse_name, None)
        cap = pr / 3.0 if pr is not None else 1.0
        win_caps.append(cap)
    win_caps = np.array(win_caps)

    # softmax と cap の最小値、正規化
    capped = np.minimum(softmax_probs, win_caps)
    total  = capped.sum()
    if total < 1e-9:
        capped = softmax_probs
    else:
        capped = capped / total

    return {idx: float(p) for idx, p in zip(indices, capped)}


# ============================================================
# 4. バックテスト実行（全馬レベルのデータを収集）
# ============================================================
print("\n■ バックテスト実行中...")
race_groups = grade_df.groupby('race_key')
total_races = len(race_groups)
print(f"  対象レース数: {total_races:,}R")

horse_records = []   # 全馬レコード（エッジ値計算用）
race_records  = []   # 1レース1件（◎ベース）

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
    placed_set = {str(r['馬名']).strip()
                  for _, r in valid[valid['確定着順'] <= 3].iterrows()}

    year = int(race_key.split('_')[0]) if '_' in race_key else 0
    meta = valid.iloc[0]
    grade_label = str(rdf.iloc[0]['grade'])
    dist_val  = int(meta['距離']) if pd.notna(meta['距離']) else 0
    venue     = str(meta['場所']).strip()

    # スコア計算
    scores     = score_race_4teams(valid)
    win_probs  = score_to_win_prob(scores, valid)

    # ── 全馬レコード収集 ──
    for idx, row in valid.iterrows():
        odds_raw = float(row['単勝オッズ_num'])
        if odds_raw <= 0:
            continue
        market_prob  = (1.0 / odds_raw) * 0.80
        engine_prob  = win_probs.get(idx, 0.0)
        edge         = engine_prob - market_prob
        fin_pos      = int(row['確定着順'])
        pop          = int(row['人気順'])

        horse_records.append({
            'race_key':   race_key,
            'year':       year,
            'grade':      grade_label,
            'venue':      venue,
            'distance':   dist_val,
            'horse_name': str(row['馬名']).strip(),
            'pop':        pop,
            'odds':       odds_raw,
            'market_prob': market_prob,
            'engine_prob': engine_prob,
            'edge':        edge,
            'finish':     fin_pos,
            'is_winner':  (fin_pos == 1),
            'is_placed':  (fin_pos <= 3),
        })

    # ── 1レース1件：◎（最高スコア馬）ベース ──
    best_idx  = max(scores, key=scores.get)
    best_row  = valid.loc[best_idx]
    pred_name = str(best_row['馬名']).strip()
    pred_pop  = int(best_row['人気順'])
    pred_odds = float(best_row['単勝オッズ_num'])
    pred_ep   = win_probs.get(best_idx, 0.0)
    pred_edge = pred_ep - (1.0 / pred_odds * 0.80) if pred_odds > 0 else None

    race_records.append({
        'race_key':  race_key,
        'year':      year,
        'grade':     grade_label,
        'venue':     venue,
        'distance':  dist_val,
        'dist_band': dist_band(dist_val),
        'hit':       (pred_name == actual_1st),
        'pred_pop':  pred_pop,
        'pred_odds': pred_odds,
        'pred_ep':   pred_ep,
        'pred_edge': pred_edge,
    })

df_horse = pd.DataFrame(horse_records)
df_race  = pd.DataFrame(race_records)

n_train_h = (df_horse['year'] <= TRAIN_YEAR_MAX).sum()
n_test_h  = (df_horse['year'] >= TEST_YEAR_MIN).sum()
n_train_r = (df_race['year'] <= TRAIN_YEAR_MAX).sum()
n_test_r  = (df_race['year'] >= TEST_YEAR_MIN).sum()
print(f"\n  全馬レコード: 訓練{n_train_h:,}頭・検証{n_test_h:,}頭")
print(f"  レースレコード: 訓練{n_train_r:,}R・検証{n_test_r:,}R")


# ============================================================
# 5. 結果集計
# ============================================================
SEP = "=" * 60

def recovery(sub_df):
    """horse_recordsサブセットの単勝回収率（%）"""
    payout = sub_df.loc[sub_df['is_winner'], 'odds'].sum() * BET_UNIT
    total  = len(sub_df) * BET_UNIT
    return payout / total * 100 if total > 0 else 0.0


def race_recovery(sub_df):
    """race_recordsサブセットの単勝回収率（%）"""
    payout = sub_df.loc[sub_df['hit'], 'pred_odds'].sum() * BET_UNIT
    total  = len(sub_df) * BET_UNIT
    return payout / total * 100 if total > 0 else 0.0


# --- 訓練データ用フィルター ---
train_h = df_horse[df_horse['year'] <= TRAIN_YEAR_MAX].copy()
test_r  = df_race[df_race['year']  >= TEST_YEAR_MIN].copy()
train_r = df_race[df_race['year']  <= TRAIN_YEAR_MAX].copy()

print(f"\n\n{SEP}")
print("【Step 1】エッジ値の分布確認（訓練データ 2015〜2023年）")
print(SEP)

edges = train_h['edge']
print(f"\nエッジ値の統計（全馬）:")
print(f"  件数      : {len(edges):,}頭")
print(f"  平均      : {edges.mean():.4f}")
print(f"  標準偏差  : {edges.std():.4f}")
print(f"  最小      : {edges.min():.4f}")
print(f"  25%ile    : {edges.quantile(0.25):.4f}")
print(f"  中央値    : {edges.median():.4f}")
print(f"  75%ile    : {edges.quantile(0.75):.4f}")
print(f"  最大      : {edges.max():.4f}")
print(f"  プラス比率: {(edges > 0).mean()*100:.1f}%")

# 各レースのエッジ値最大馬
top_edge = train_h.sort_values(['race_key','edge'], ascending=[True,False])
top_edge_per_race = top_edge.groupby('race_key').first().reset_index()
print(f"\n各レースのエッジ値最大馬（訓練 {len(top_edge_per_race):,}R）:")
print(f"  勝率     : {top_edge_per_race['is_winner'].mean()*100:.1f}%")
print(f"  複勝率   : {top_edge_per_race['is_placed'].mean()*100:.1f}%")
recov_top = top_edge_per_race.loc[top_edge_per_race['is_winner'], 'odds'].sum() * BET_UNIT
total_top = len(top_edge_per_race) * BET_UNIT
print(f"  単勝回収率: {recov_top/total_top*100:.1f}%")
print(f"  ◎平均人気: {top_edge_per_race['pop'].mean():.1f}番人気")
print(f"  ◎平均オッズ: {top_edge_per_race['odds'].mean():.1f}倍")

# エッジ値と着順の相関
corr = train_h[['edge','finish']].corr().iloc[0,1]
print(f"\nエッジ値と着順の相関係数: {corr:.4f}")
print("  ※ 着順は少ないほど良い。負の相関 = エッジ高いほど着順が良い傾向")

# 相関係数の解釈
if corr < -0.05:
    print("  → 有意な負の相関あり（エッジ値は着順予測に有効）")
elif corr > 0.05:
    print("  → 正の相関（逆効果・エッジ値は着順予測に有害）")
else:
    print("  → 相関ほぼゼロ（エッジ値単独での着順予測力は低い）")


print(f"\n\n{SEP}")
print("【Step 2】エッジ値閾値別の単勝回収率（訓練データ）")
print(SEP)

bands = [
    ('+0.10以上（強い割安）',   train_h['edge'] >= 0.10),
    ('+0.05〜0.10',            (train_h['edge'] >= 0.05) & (train_h['edge'] < 0.10)),
    ('+0.00〜0.05',            (train_h['edge'] >= 0.00) & (train_h['edge'] < 0.05)),
    ('マイナス（割高）',         train_h['edge'] < 0.00),
    # 追加: より細かい正エッジ帯
    ('+0.15以上',              train_h['edge'] >= 0.15),
]

print(f"\n{'帯':20s}  {'N':>6s}  {'勝率':>6s}  {'単勝回収率':>10s}  {'平均人気':>8s}  {'平均オッズ':>9s}")
print("-" * 70)
for label, mask in bands:
    sub = train_h[mask]
    if len(sub) == 0:
        print(f"{label:20s}  {'0':>6s}  {'-':>6s}  {'  -':>10s}  {'   -':>8s}  {'   -':>9s}")
        continue
    wr   = sub['is_winner'].mean() * 100
    rec  = recovery(sub)
    avgp = sub['pop'].mean()
    avgo = sub['odds'].mean()
    print(f"{label:20s}  {len(sub):>6,d}  {wr:>5.1f}%  {rec:>9.1f}%  {avgp:>7.1f}番  {avgo:>8.1f}倍")

# 追加：◎（各レース最高スコア馬）のエッジ値帯別回収率
print(f"\n── ◎（各レース最高スコア馬）のエッジ値帯別 ──")
train_r_copy = train_r.copy()
train_r_copy['edge_band'] = pd.cut(
    train_r_copy['pred_edge'],
    bins=[-999, 0.0, 0.05, 0.10, 999],
    labels=['マイナス', '0〜+0.05', '+0.05〜0.10', '+0.10以上']
)
print(f"\n{'帯':20s}  {'N':>5s}  {'◎的中率':>8s}  {'単勝回収率':>10s}")
print("-" * 50)
for band in ['マイナス', '0〜+0.05', '+0.05〜0.10', '+0.10以上']:
    sub = train_r_copy[train_r_copy['edge_band'] == band]
    if len(sub) == 0:
        continue
    hr  = sub['hit'].mean() * 100
    rec = race_recovery(sub)
    print(f"{band:20s}  {len(sub):>5,d}  {hr:>7.1f}%  {rec:>9.1f}%")


print(f"\n\n{SEP}")
print("【Step 3】現行◎との組み合わせ効果（検証データ 2024〜2026年）")
print(SEP)

print(f"\n検証データ: {len(test_r):,}R（{TEST_YEAR_MIN}〜2026年）")

# ベースライン（フィルターなし）
base_hit = test_r['hit'].mean() * 100
base_rec = race_recovery(test_r)
print(f"\nベースライン（全レース◎購入）:")
print(f"  R数: {len(test_r):,}  的中率: {base_hit:.1f}%  単勝回収率: {base_rec:.1f}%")

# ① 現行◎のエッジ値 +0.05以上のみ購入
filt_05 = test_r[test_r['pred_edge'] >= 0.05]
if len(filt_05) > 0:
    hit_05 = filt_05['hit'].mean() * 100
    rec_05 = race_recovery(filt_05)
else:
    hit_05 = rec_05 = 0.0

# ② 現行◎のエッジ値 +0.10以上のみ購入
filt_10 = test_r[test_r['pred_edge'] >= 0.10]
if len(filt_10) > 0:
    hit_10 = filt_10['hit'].mean() * 100
    rec_10 = race_recovery(filt_10)
else:
    hit_10 = rec_10 = 0.0

# ③ 現行◎のエッジ値がマイナスのみ購入（見送り効果の裏付け）
filt_neg = test_r[test_r['pred_edge'] < 0]
if len(filt_neg) > 0:
    hit_neg = filt_neg['hit'].mean() * 100
    rec_neg = race_recovery(filt_neg)
else:
    hit_neg = rec_neg = 0.0

# ④ 現行◎のエッジ値 0.00〜+0.05
filt_0005 = test_r[(test_r['pred_edge'] >= 0.00) & (test_r['pred_edge'] < 0.05)]
if len(filt_0005) > 0:
    hit_0005 = filt_0005['hit'].mean() * 100
    rec_0005 = race_recovery(filt_0005)
else:
    hit_0005 = rec_0005 = 0.0

print(f"\n{'フィルター':30s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}  {'カバレッジ':>10s}")
print("-" * 70)
rows = [
    ("① エッジ+0.05以上",  filt_05,  hit_05,  rec_05),
    ("② エッジ+0.10以上",  filt_10,  hit_10,  rec_10),
    ("③ エッジ0〜+0.05",   filt_0005, hit_0005, rec_0005),
    ("④ エッジマイナス",    filt_neg,  hit_neg,  rec_neg),
    ("⑤ 全レース（比較）",  test_r,    base_hit, base_rec),
]
for label, sub, hr, rc in rows:
    cov = len(sub) / len(test_r) * 100 if len(test_r) > 0 else 0
    print(f"{label:30s}  {len(sub):>5,d}  {hr:>6.1f}%  {rc:>9.1f}%  {cov:>9.1f}%")

# 年別内訳（エッジ+0.05以上）
print(f"\n── ① エッジ+0.05以上の年別内訳 ──")
if len(filt_05) > 0:
    print(f"\n{'年':>5s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}")
    print("-" * 35)
    for yr in sorted(filt_05['year'].unique()):
        sub = filt_05[filt_05['year'] == yr]
        hr  = sub['hit'].mean() * 100
        rc  = race_recovery(sub)
        print(f"{yr:>5d}  {len(sub):>5,d}  {hr:>6.1f}%  {rc:>9.1f}%")
else:
    print("  該当なし")

# グレード別（エッジ+0.05以上）
print(f"\n── ① エッジ+0.05以上のグレード別 ──")
if len(filt_05) > 0:
    print(f"\n{'グレード':>8s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}")
    print("-" * 38)
    for g in ['G1','G2','G3']:
        sub = filt_05[filt_05['grade'] == g]
        if len(sub) == 0:
            continue
        hr  = sub['hit'].mean() * 100
        rc  = race_recovery(sub)
        print(f"{g:>8s}  {len(sub):>5,d}  {hr:>6.1f}%  {rc:>9.1f}%")

# 距離帯別（エッジ+0.05以上）
print(f"\n── ① エッジ+0.05以上の距離帯別 ──")
if len(filt_05) > 0:
    filt_05_copy = filt_05.copy()
    filt_05_copy['db'] = filt_05_copy['distance'].apply(dist_band)
    print(f"\n{'距離帯':15s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}")
    print("-" * 42)
    for db in ['〜1400m','1600〜2000m','2200m〜']:
        sub = filt_05_copy[filt_05_copy['db'] == db]
        if len(sub) == 0:
            continue
        hr  = sub['hit'].mean() * 100
        rc  = race_recovery(sub)
        print(f"{db:15s}  {len(sub):>5,d}  {hr:>6.1f}%  {rc:>9.1f}%")


print(f"\n\n{SEP}")
print("【Step 4】結論・穴馬戦略との組み合わせ試算")
print(SEP)

# 現行穴馬戦略（2200m未満 × ◎が4番人気以上）の検証データでの結果
anaba_base = test_r[
    (test_r['pred_pop'] >= 4) &
    (test_r['distance'] < 2200)
]
anaba_hit = anaba_base['hit'].mean() * 100 if len(anaba_base) > 0 else 0.0
anaba_rec = race_recovery(anaba_base)

# 穴馬戦略 × エッジ+0.05以上
anaba_e05 = anaba_base[anaba_base['pred_edge'] >= 0.05]
anaba_e05_hit = anaba_e05['hit'].mean() * 100 if len(anaba_e05) > 0 else 0.0
anaba_e05_rec = race_recovery(anaba_e05)

# 穴馬戦略 × エッジ+0.10以上
anaba_e10 = anaba_base[anaba_base['pred_edge'] >= 0.10]
anaba_e10_hit = anaba_e10['hit'].mean() * 100 if len(anaba_e10) > 0 else 0.0
anaba_e10_rec = race_recovery(anaba_e10)

print(f"\n── 穴馬戦略（◎4番人気以上 × 距離2200m未満）× エッジ絞り込み ──")
print(f"  検証データ（2024〜2026年）対象\n")
print(f"{'戦略':35s}  {'N':>5s}  {'的中率':>7s}  {'単勝回収率':>10s}")
print("-" * 62)
rows2 = [
    ("穴馬戦略（フィルターなし）",             anaba_base, anaba_hit, anaba_rec),
    ("穴馬戦略 × エッジ+0.05以上",            anaba_e05,  anaba_e05_hit, anaba_e05_rec),
    ("穴馬戦略 × エッジ+0.10以上",            anaba_e10,  anaba_e10_hit, anaba_e10_rec),
]
for label, sub, hr, rc in rows2:
    cov = len(sub) / len(anaba_base) * 100 if len(anaba_base) > 0 else 0
    print(f"{label:35s}  {len(sub):>5,d}  {hr:>6.1f}%  {rc:>9.1f}%  (カバレッジ{cov:.0f}%)")

# 年間ベット数の試算
print(f"\n── 年間ベット数の試算（穴馬戦略 × エッジ絞り込み）──")
years_in_test = sorted(test_r['year'].unique())
if len(years_in_test) > 0:
    n_years_test = max(1, len(years_in_test))
    print(f"  検証期間: {min(years_in_test)}〜{max(years_in_test)} ({n_years_test}年間相当)")
    if len(anaba_base) > 0:
        print(f"  穴馬戦略（フィルターなし）: 年間約{len(anaba_base)/n_years_test:.0f}R")
    if len(anaba_e05) > 0:
        print(f"  穴馬戦略 × エッジ+0.05以上: 年間約{len(anaba_e05)/n_years_test:.0f}R")
    if len(anaba_e10) > 0:
        print(f"  穴馬戦略 × エッジ+0.10以上: 年間約{len(anaba_e10)/n_years_test:.0f}R")

print(f"\n── 結論サマリー ──")

# 結論判定
if len(filt_05) > 0 and rec_05 > base_rec:
    edge_useful = True
    improvement = rec_05 - base_rec
    print(f"\n  エッジ+0.05以上フィルター: 回収率 {base_rec:.1f}% → {rec_05:.1f}% (+{improvement:.1f}%)")
    if improvement >= 5:
        print("  ★ エッジ値フィルターは有効（+5%以上の改善）")
    else:
        print("  △ エッジ値フィルターの改善効果は限定的（+5%未満）")
else:
    edge_useful = False
    print(f"\n  エッジ+0.05以上フィルター: 回収率が改善しない or サンプル不足")
    print("  ✗ エッジ値フィルターは検証データで有効性を確認できず")

# 穴馬戦略との組み合わせ判定
if len(anaba_e05) > 0 and anaba_e05_rec > anaba_rec:
    combo_delta = anaba_e05_rec - anaba_rec
    if combo_delta >= 5:
        print(f"\n  穴馬戦略 × エッジ+0.05以上: {anaba_rec:.1f}% → {anaba_e05_rec:.1f}% (+{combo_delta:.1f}%)")
        print("  ★ 穴馬戦略との組み合わせで回収率が改善（採用推奨）")
    else:
        print(f"\n  穴馬戦略 × エッジ+0.05以上: {anaba_rec:.1f}% → {anaba_e05_rec:.1f}% (+{combo_delta:.1f}%)")
        print("  △ 穴馬戦略との組み合わせ効果は限定的")
elif len(anaba_e05) > 0:
    print(f"\n  穴馬戦略 × エッジ+0.05以上: {anaba_rec:.1f}% → {anaba_e05_rec:.1f}% (改善なし)")
    print("  ✗ 穴馬戦略との組み合わせで回収率が改善しない（フィルター不採用）")

print(f"\n  仮説Cバックテスト参照用数値:")
print(f"    穴馬戦略バックテスト基準（2015〜2026年 150R）: 227.7%")
print(f"    本検証は検証データ（{TEST_YEAR_MIN}〜）のみ。全期間は別途評価が必要。")

print(f"\n{SEP}")
print("■ 完了")
print(SEP)
