# -*- coding: utf-8 -*-
"""
hypothesis_g1_first_test.py  -  G1初出走フラグ検証

【背景】
  仮説B（直近3走トレンド）検証の副産物として：
  「エンジン◎が3走未満（パターン不明）のG1で60%的中」という結果が出た。
  これが統計的に有意かどうかを検証する。

【ステップ】
  Step 1: サンプル数確認（検証データ 2024〜2026 G1）
  Step 2: 訓練データ検証（2015〜2023 G1）
  Step 3: G1初出走フラグの精緻化
            「3走未満」→「G1自体が初出走（G1出走歴なし）」に再定義
  Step 4: 結論（統計的有意性・エンジン組み込み方法・採否）

使い方:
  python3 hypothesis_g1_first_test.py
"""

import sys
import io
import os
import re
import math
import pickle
import numpy as np
import pandas as pd
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'course_master.db')
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

GRADE_PAT  = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
SEP        = '=' * 70
SEP2       = '─' * 70
BET_UNIT   = 100
ADOPT_THR  = 5.0   # 改善率の採用閾値（%ポイント）


# ─────────────────────────────────────────────────
# ユーティリティ
# ─────────────────────────────────────────────────
def detect_grade(name):
    if not name:
        return None
    m = GRADE_PAT.search(str(name))
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


def wilson_ci(n, k, z=1.96):
    """Wilson信頼区間（95%）。n=試行回数、k=成功回数。"""
    if n == 0:
        return (0.0, 1.0)
    p_hat = k / n
    center = (p_hat + z ** 2 / (2 * n)) / (1 + z ** 2 / n)
    margin = (z * math.sqrt(p_hat * (1 - p_hat) / n + z ** 2 / (4 * n ** 2))
              / (1 + z ** 2 / n))
    return (max(0.0, center - margin), min(1.0, center + margin))


def ci_str(n, k):
    """信頼区間を文字列で返す。サンプルが10未満なら「統計的に不十分」と付記。"""
    lo, hi = wilson_ci(n, k)
    base = f"95%CI [{lo*100:.1f}%〜{hi*100:.1f}%]"
    if n < 10:
        base += "  ⚠️ サンプル不十分（n<10）"
    elif n < 30:
        base += "  △ サンプル小（n<30）"
    return base


def pos_to_label(pos):
    if pos <= 0:
        return None
    if pos <= 3:
        return 'W'
    if pos <= 6:
        return 'M'
    return 'L'


def make_pattern(labels):
    if len(labels) < 3 or any(l is None for l in labels):
        return None
    return '-'.join(labels)


# ─────────────────────────────────────────────────
# 1. CSV読み込み・前処理
# ─────────────────────────────────────────────────
print("■ CSV 読み込み中...")
dfs = []
for fp in CSV_FILES:
    if os.path.exists(fp):
        dfs.append(pd.read_csv(fp, encoding='cp932', low_memory=False))
        print(f"  {os.path.basename(fp)}: {len(dfs[-1]):,}件")
    else:
        print(f"  [スキップ] {os.path.basename(fp)}")

df_all = pd.concat(dfs, ignore_index=True)

for col in ['確定着順', '人気順', '距離']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(int)
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'],     errors='coerce').fillna(0.0)
df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'],       errors='coerce')
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
for col in ['通過順1', '通過順2', '通過順3', '通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
df_all['場所'] = df_all['場所'].astype(str).str.strip()

df_all['year_int'] = df_all['年'].astype(int) + 2000
df_all['race_date_str'] = (
    df_all['year_int'].astype(str) + '-' +
    df_all['月'].astype(str).str.zfill(2) + '-' +
    df_all['日'].astype(str).str.zfill(2)
)
df_all['race_key'] = (
    df_all['年'].astype(str) + '_' +
    df_all['月'].astype(str).str.zfill(2) + '_' +
    df_all['日'].astype(str).str.zfill(2) + '_' +
    df_all['場所'] + '_' +
    df_all['日次'].astype(str) + '_' +
    df_all['レース番号'].astype(str).str.zfill(2)
)
df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None
)

grade_df = df_all[df_all['grade'].notna()].drop_duplicates(subset=['race_key', '馬名']).copy()
print(f"\n  重賞レコード: {len(grade_df):,}件  "
      f"G1:{(grade_df['grade']=='G1').sum():,}  "
      f"G2:{(grade_df['grade']=='G2').sum():,}  "
      f"G3:{(grade_df['grade']=='G3').sum():,}")

train_df = grade_df[grade_df['year_int'] <= 2023].copy()
test_df  = grade_df[grade_df['year_int'] >= 2024].copy()


# ─────────────────────────────────────────────────
# 2. 走歴辞書の構築（全レース・全馬）
# ─────────────────────────────────────────────────
print("\n■ 走歴辞書を構築中...")

# 全レース走歴（着順付き）
horse_all_hist = defaultdict(list)
for _, row in df_all[df_all['確定着順'] > 0].iterrows():
    h = str(row['馬名']).strip()
    horse_all_hist[h].append((str(row['race_date_str']), int(row['確定着順'])))
for h in horse_all_hist:
    horse_all_hist[h].sort(key=lambda x: x[0])

# G1レース走歴のみ（日付付き）
g1_df = df_all[(df_all['grade'] == 'G1') & (df_all['確定着順'] > 0)].copy()
horse_g1_hist = defaultdict(list)
for _, row in g1_df.iterrows():
    h = str(row['馬名']).strip()
    horse_g1_hist[h].append(str(row['race_date_str']))
for h in horse_g1_hist:
    horse_g1_hist[h].sort()

print(f"  全レース走歴: {len(horse_all_hist):,}頭")
print(f"  G1出走歴あり: {len(horse_g1_hist):,}頭")


def get_recent3_total(horse, before_date):
    """before_date より前の直近3走（全レース）の着順リスト（古い順）"""
    hist = horse_all_hist.get(horse, [])
    prior = [p for d, p in hist if d < before_date]
    return prior[-3:]  # 直近3走


def is_few_career(horse, before_date):
    """当日より前の通算出走数が3走未満かどうか"""
    hist = horse_all_hist.get(horse, [])
    prior = [d for d, p in hist if d < before_date]
    return len(prior) < 3


def is_g1_first(horse, before_date):
    """当日より前にG1出走歴がないかどうか（G1初出走）"""
    g1_dates = horse_g1_hist.get(horse, [])
    prior_g1 = [d for d in g1_dates if d < before_date]
    return len(prior_g1) == 0


def get_g1_count(horse, before_date):
    """当日より前のG1出走回数"""
    g1_dates = horse_g1_hist.get(horse, [])
    return len([d for d in g1_dates if d < before_date])


# ─────────────────────────────────────────────────
# 3. エンジン再現（v7.3 4チーム合議・7軸重み付き）
# ─────────────────────────────────────────────────
print("\n■ pkl 読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

sire_stats      = state.get('sire_stats', {})
jockey_stats    = state.get('jockey_stats', {})
distance_stats  = state.get('distance_stats', {})
career_penalty  = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
odds_mk_table   = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]

print(f"  sire_stats:{len(sire_stats)}  jockey_stats:{len(jockey_stats)}  "
      f"distance_stats:{len(distance_stats)}")

print("\n■ 血統CSV 読み込み中...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)


def score_horse_engine(row, team_type='I'):
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
    agari = row.get('上がり3Fタイム_sec')
    axes['SI'] = max(10, 100 - (float(agari) - 30) * 2) if pd.notna(agari) else 50

    # JT
    jockey = row.get('騎手名')
    axes['JT'] = (min(100, jockey_stats[jockey]['win_rate'] * 100)
                  if pd.notna(jockey) and jockey in jockey_stats else 50)

    # PD
    passages = [row.get(c) for c in ['通過順1', '通過順2', '通過順3', '通過順4']]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    axes['PD'] = max(10, 100 - abs(np.mean(passages) - 7) * 3) if passages else 50

    # BL
    pop = int(row['人気順'])
    axes['BL'] = max(10, 100 - pop * 5) if pop > 0 else 50

    # SPD
    dist  = int(row['距離'])
    jikan = row.get('走破時計_sec')
    if dist in distance_stats and pd.notna(jikan):
        ds = distance_stats[dist]
        axes['SPD'] = (max(10, min(100, 50 - (float(jikan) - ds['avg_time']) / ds['std_time'] * 10))
                       if ds['std_time'] > 0 else 50)
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


def score_race(rdf):
    teams = ['I', 'O', 'U', 'S']
    team_scores = {t: {} for t in teams}
    for t in teams:
        for idx, row in rdf.iterrows():
            try:
                team_scores[t][idx] = score_horse_engine(row, t)
            except Exception:
                team_scores[t][idx] = 50.0
    return {idx: float(np.mean([team_scores[t][idx] for t in teams]))
            for idx in rdf.index}


# ─────────────────────────────────────────────────
# 4. バックテスト: G1のみ対象
# ─────────────────────────────────────────────────
print("\n■ バックテスト実行中（G1のみ）...")

g1_train = train_df[train_df['grade'] == 'G1'].copy()
g1_test  = test_df[test_df['grade']  == 'G1'].copy()

train_races = list(g1_train.groupby('race_key'))
test_races  = list(g1_test.groupby('race_key'))

print(f"  訓練G1: {len(train_races)}R  /  検証G1: {len(test_races)}R")

records = []

for split, race_list in [('train', train_races), ('test', test_races)]:
    total = len(race_list)
    for i, (race_key, rdf) in enumerate(race_list):
        if i % 50 == 0:
            print(f"  [{split}] 進捗 {i}/{total}...")

        valid = rdf[rdf['確定着順'] > 0].copy()
        if len(valid) < 3:
            continue
        winner_rows = valid[valid['確定着順'] == 1]
        if winner_rows.empty:
            continue
        actual_winner = str(winner_rows.iloc[0]['馬名']).strip()
        race_date     = str(valid.iloc[0]['race_date_str'])

        # 1番人気
        pop1_rows  = valid[valid['人気順'] == 1]
        pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None

        # エンジンスコアで◎を決定
        try:
            scores = score_race(valid)
        except Exception:
            continue
        best_idx   = max(scores, key=scores.get)
        engine_row = valid.loc[best_idx]
        engine_horse = str(engine_row['馬名']).strip()
        engine_pop   = int(engine_row['人気順'])
        engine_hit   = (engine_horse == actual_winner)

        # ── フラグ算出 ──
        # フラグA: キャリア3走未満（仮説Bの副産物定義）
        flag_a = is_few_career(engine_horse, race_date)

        # フラグB: G1初出走（G1出走歴ゼロ）
        flag_b = is_g1_first(engine_horse, race_date)

        # G1出走回数
        g1_cnt = get_g1_count(engine_horse, race_date)

        records.append({
            'split':        split,
            'race_key':     race_key,
            'race_date':    race_date,
            'year':         int(race_date[:4]),
            'engine_horse': engine_horse,
            'engine_pop':   engine_pop,
            'engine_hit':   engine_hit,
            'pop1_hit':     (pop1_horse == actual_winner) if pop1_horse else False,
            'flag_a':       flag_a,      # キャリア3走未満
            'flag_b':       flag_b,      # G1初出走
            'g1_count':     g1_cnt,      # 当日より前のG1出走回数
        })

df = pd.DataFrame(records)
df_train = df[df['split'] == 'train']
df_test  = df[df['split'] == 'test']


# ─────────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────────
def hr(sub):
    return sub['engine_hit'].mean() * 100 if len(sub) > 0 else 0.0

def pop1_hr(sub):
    return sub['pop1_hit'].mean() * 100 if len(sub) > 0 else 0.0

def n_hits(sub):
    return int(sub['engine_hit'].sum())


# ─────────────────────────────────────────────────
# ■ Step 1: 検証データ（2024〜2026 G1）のサンプル確認
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 1】サンプル数確認（検証データ: 2024〜2026 G1）")
print(SEP)

total_test  = len(df_test)
total_hits  = n_hits(df_test)
total_hr    = hr(df_test)

fa_test = df_test[df_test['flag_a']]   # キャリア3走未満
fb_test = df_test[df_test['flag_b']]   # G1初出走

fa_n, fa_k = len(fa_test), n_hits(fa_test)
fb_n, fb_k = len(fb_test), n_hits(fb_test)

print(f"""
  検証G1レース総数    : {total_test}R
  エンジン◎的中率（全体）: {total_hr:.1f}%  ({total_hits}/{total_test}R)
  1番人気的中率（比較）: {pop1_hr(df_test):.1f}%

  ─── フラグA: エンジン◎がキャリア3走未満 ───
  対象レース数  : {fa_n}R
  的中数        : {fa_k}件
  的中率        : {hr(fa_test):.1f}%
  {ci_str(fa_n, fa_k)}
""")

if fa_n < 10:
    print("  ⚠️  フラグA: 検証データのサンプルが10件未満 → Step2で訓練データのみで判断")
elif fa_n < 30:
    print("  △  フラグA: サンプル30件未満 → 傾向はあるが統計的信頼性に注意")

print(f"""
  ─── フラグB: エンジン◎がG1初出走（G1出走歴なし） ───
  対象レース数  : {fb_n}R
  的中数        : {fb_k}件
  的中率        : {hr(fb_test):.1f}%
  {ci_str(fb_n, fb_k)}
""")

if fb_n < 10:
    print("  ⚠️  フラグB: 検証データのサンプルが10件未満 → Step2で訓練データのみで判断")
elif fb_n < 30:
    print("  △  フラグB: サンプル30件未満 → 傾向はあるが統計的信頼性に注意")


# ─────────────────────────────────────────────────
# ■ Step 2: 訓練データ（2015〜2023 G1）での検証
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 2】訓練データ検証（2015〜2023 G1）")
print(SEP)

total_train   = len(df_train)
total_train_h = n_hits(df_train)

fa_train = df_train[df_train['flag_a']]
fa_not   = df_train[~df_train['flag_a']]
fb_train = df_train[df_train['flag_b']]
fb_not   = df_train[~df_train['flag_b']]

fa_tr_n, fa_tr_k = len(fa_train), n_hits(fa_train)
fb_tr_n, fb_tr_k = len(fb_train), n_hits(fb_train)

print(f"""
  訓練G1レース総数        : {total_train}R
  エンジン◎的中率（全体） : {hr(df_train):.1f}%  ({total_train_h}/{total_train}R)
  1番人気的中率（基準）    : {pop1_hr(df_train):.1f}%

  ─── フラグA比較: キャリア3走未満 vs 3走以上 ───
  フラグA（3走未満）       : {hr(fa_train):.1f}%  ({fa_tr_k}/{fa_tr_n}R)
                             {ci_str(fa_tr_n, fa_tr_k)}
  非フラグA（3走以上）     : {hr(fa_not):.1f}%  ({n_hits(fa_not)}/{len(fa_not)}R)
                             {ci_str(len(fa_not), n_hits(fa_not))}
  差（A − 非A）           : {hr(fa_train) - hr(fa_not):+.1f}%ポイント

  ─── フラグB比較: G1初出走 vs G1経験あり ───
  フラグB（G1初出走）      : {hr(fb_train):.1f}%  ({fb_tr_k}/{fb_tr_n}R)
                             {ci_str(fb_tr_n, fb_tr_k)}
  非フラグB（G1経験あり）  : {hr(fb_not):.1f}%  ({n_hits(fb_not)}/{len(fb_not)}R)
                             {ci_str(len(fb_not), n_hits(fb_not))}
  差（B − 非B）           : {hr(fb_train) - hr(fb_not):+.1f}%ポイント
""")

# 年別内訳（フラグB）
print("  ─── フラグB: G1初出走◎の年別的中率 ───")
print(f"  {'年':>5}  {'G1初出走N':>9}  {'的中':>5}  {'的中率':>7}  95%CI")
print(f"  {SEP2}")
for yr in sorted(df_train['year'].unique()):
    sub_yr = df_train[df_train['year'] == yr]
    sub_fb = sub_yr[sub_yr['flag_b']]
    n_yr, k_yr = len(sub_fb), n_hits(sub_fb)
    if n_yr == 0:
        print(f"  {yr:>5}  {'0':>9}  {'─':>5}  {'─':>7}  ─")
    else:
        lo, hi = wilson_ci(n_yr, k_yr)
        print(f"  {yr:>5}  {n_yr:>9}  {k_yr:>5}  {hr(sub_fb):>6.1f}%  "
              f"[{lo*100:.1f}%〜{hi*100:.1f}%]")


# ─────────────────────────────────────────────────
# ■ Step 3: G1初出走フラグの精緻化（G1出走回数別）
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 3】G1初出走フラグの精緻化（G1出走回数別・訓練データ）")
print(SEP)

print(f"""
  【G1出走回数別 エンジン◎的中率（訓練）】

  G1出走回数（当日前）  N     的中率   95%CI
  {SEP2}""")

for cnt_lo, cnt_hi, label in [
    (0, 0,   "初出走（0回）"),
    (1, 1,   "2回目出走（1回経験）"),
    (2, 2,   "3回目出走（2回経験）"),
    (3, 5,   "4〜6回目（3〜5回経験）"),
    (6, 999, "7回以上出走"),
]:
    sub = df_train[(df_train['g1_count'] >= cnt_lo) & (df_train['g1_count'] <= cnt_hi)]
    n, k = len(sub), n_hits(sub)
    if n == 0:
        print(f"  {label:<22}  {'0':>5}  {'─':>7}  ─")
    else:
        lo, hi = wilson_ci(n, k)
        print(f"  {label:<22}  {n:>5}  {hr(sub):>6.1f}%  [{lo*100:.1f}%〜{hi*100:.1f}%]")

print(f"""
  【参考: 1番人気 vs エンジン全体 vs フラグB（訓練）】
  1番人気的中率（訓練）     : {pop1_hr(df_train):.1f}%
  エンジン◎全体（訓練）     : {hr(df_train):.1f}%
  エンジン◎G1初出走（訓練） : {hr(fb_train):.1f}%

  ─── 「初出走◎」の人気帯分布 ───""")

print(f"  {'人気帯':15}  {'N':>5}  {'的中率':>7}  95%CI")
print(f"  {SEP2}")
for pop_lo, pop_hi, label in [
    (1, 3, '1〜3番人気'),
    (4, 6, '4〜6番人気'),
    (7, 9, '7〜9番人気'),
    (10, 99, '10番人気以上'),
]:
    sub = fb_train[(fb_train['engine_pop'] >= pop_lo) & (fb_train['engine_pop'] <= pop_hi)]
    n, k = len(sub), n_hits(sub)
    if n == 0:
        continue
    lo, hi = wilson_ci(n, k)
    print(f"  {label:<15}  {n:>5}  {hr(sub):>6.1f}%  [{lo*100:.1f}%〜{hi*100:.1f}%]")

# 検証データでの確認
print(f"""
  ─── 検証データ（2024〜2026）でのG1出走回数別 ───
  G1出走回数（当日前）  N     的中率   95%CI
  {SEP2}""")

for cnt_lo, cnt_hi, label in [
    (0, 0,   "初出走（0回）"),
    (1, 2,   "1〜2回経験"),
    (3, 5,   "3〜5回経験"),
    (6, 999, "6回以上"),
]:
    sub = df_test[(df_test['g1_count'] >= cnt_lo) & (df_test['g1_count'] <= cnt_hi)]
    n, k = len(sub), n_hits(sub)
    if n == 0:
        print(f"  {label:<22}  {'0':>5}  {'─':>7}  ─")
    else:
        lo, hi = wilson_ci(n, k)
        print(f"  {label:<22}  {n:>5}  {hr(sub):>6.1f}%  [{lo*100:.1f}%〜{hi*100:.1f}%]")


# ─────────────────────────────────────────────────
# ■ Step 4: 結論
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 4】結論")
print(SEP)

# 判定ロジック（訓練データ基準）
base_hr_val = hr(df_train)
fb_hr_val   = hr(fb_train)
diff_b      = fb_hr_val - base_hr_val

# 訓練と検証の方向が一致しているか
if fb_n > 0:
    fb_test_hr = hr(fb_test)
    direction_consistent = ((fb_hr_val > base_hr_val and fb_test_hr > hr(df_test)) or
                            (fb_hr_val < base_hr_val and fb_test_hr < hr(df_test)))
else:
    direction_consistent = False
    fb_test_hr = 0.0

# 統計的信頼性（訓練データ）
lo_b, hi_b   = wilson_ci(fb_tr_n, fb_tr_k)
lo_nb, hi_nb = wilson_ci(len(fb_not), n_hits(fb_not))
# 信頼区間が重なっているかどうか
ci_overlap = (lo_b < hi_nb and lo_nb < hi_b)

print(f"""
  ┌─────────────────────────────────────────────────────────────────────┐
  │   「G1初出走フラグ」統計的有意性・採否判定                         │
  └─────────────────────────────────────────────────────────────────────┘

  【訓練データ（2015〜2023 G1・{total_train}R）基準値】
    エンジン◎全体          : {hr(df_train):.1f}%
    1番人気的中率           : {pop1_hr(df_train):.1f}%

  【フラグB: G1初出走◎】
    訓練的中率              : {fb_hr_val:.1f}%  (n={fb_tr_n}, 的中{fb_tr_k}件)
    訓練95%CI               : [{lo_b*100:.1f}%〜{hi_b*100:.1f}%]
    全体との差              : {diff_b:+.1f}%ポイント

  【フラグ非該当（G1経験あり◎）】
    訓練的中率              : {hr(fb_not):.1f}%  (n={len(fb_not)}, 的中{n_hits(fb_not)}件)
    訓練95%CI               : [{lo_nb*100:.1f}%〜{hi_nb*100:.1f}%]

  【信頼区間の重なり】
    G1初出走CI:   [{lo_b*100:.1f}%〜{hi_b*100:.1f}%]
    G1経験ありCI: [{lo_nb*100:.1f}%〜{hi_nb*100:.1f}%]
    重なり        : {'あり（有意差なし）' if ci_overlap else 'なし（有意差の可能性あり）'}

  【検証データ（2024〜2026 G1・{total_test}R）での確認】
    フラグB的中率（検証）   : {fb_test_hr:.1f}%  (n={fb_n}, 的中{fb_k}件)
    全体的中率（検証）      : {hr(df_test):.1f}%
    訓練→検証で同じ方向     : {'✓ 一致' if direction_consistent else '✗ 逆転（過学習懸念）'}
""")

# 総合判定
adopt = False
reason = []

if diff_b >= ADOPT_THR and not ci_overlap and direction_consistent:
    adopt = True
    reason.append(f"改善幅+{diff_b:.1f}%（閾値{ADOPT_THR}%以上）")
    reason.append("95%信頼区間が重ならない（有意差あり）")
    reason.append("訓練→検証で同方向")
elif diff_b >= ADOPT_THR and ci_overlap:
    reason.append(f"改善幅+{diff_b:.1f}%だが95%CIが重なる → 統計的に有意差を確認できない")
elif diff_b < 0:
    reason.append(f"G1初出走◎の的中率が全体より低い（差{diff_b:+.1f}%）")
else:
    reason.append(f"改善幅+{diff_b:.1f}%（閾値{ADOPT_THR}%に未達）")
    if ci_overlap:
        reason.append("95%CIが重なる（有意差なし）")
    if not direction_consistent and fb_n > 0:
        reason.append("訓練→検証で方向が逆転（過学習懸念）")

adopt_label = "【採用推奨】✓" if adopt else "【採用しない】✗"
print(f"  ─── 総合判定: {adopt_label} ───")
for r in reason:
    print(f"    ・{r}")

print(f"""
  ─── エンジンへの組み込み方法（判定参考）───""")

if adopt:
    print(f"""
    ★ 採用: G1初出走フラグを補正フラグとして組み込む
      - G1初出走馬が◎になった場合: 信頼度アップ（購入推奨）
      - 実装方法候補:
        A) grade_race_predictor.py の最終判断サマリーに「G1初出走フラグ」を追記
        B) エンジン出力（print_result）で★マークを付けて視覚的に区別
        C) CF軸に+3〜5点の加点（効果は限定的だが論理的）
      - 推奨: Aのサマリー追記のみ（エンジン本体に手を加えない）
""")
else:
    print(f"""
    ✗ 不採用: 現時点での統計的根拠が不十分
      - サンプル数 n={fb_tr_n}（訓練）/ n={fb_n}（検証）のため判断に限界あり
      - G1は年間約20〜25Rのみ。「初出走」条件はさらに絞られ、統計的検証が困難
      - 今後3〜5年のデータ蓄積後に再検証を推奨
      - エンジン本体への組み込みは見送り

    ─── 運用上のメモ（参考情報として記録）───
      - 当日の出馬表で「G1初出走馬が◎」になった場合は注目度を上げる（非公式）
      - 「若駒がG1に初参戦 + エンジンが本命視」はポジティブなシグナルである可能性
      - 次回のG1シーズンで個別に確認を続けること
""")

print(f"""
  ─── 副産物②: G3×3走未満フラグの参考数値（訓練データ）───
  （2026-04-15の仮説B結果より。今回は詳細検証を省略）
    G3 × 3走未満フラグ的中率: 約18.9%（全体31.8%より-12.9%）
    → G3では3走未満の馬が◎になった場合の精度が低い
""")

print(SEP)
print("■ 検証完了")
print(SEP)
