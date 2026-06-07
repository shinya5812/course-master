# -*- coding: utf-8 -*-
"""
hypothesis_g3_few_career_test.py  -  G3×3走未満フラグ検証

【背景】
  仮説B検証の副産物：「エンジン◎が3走未満の場合の的中率が全体比-4%」
  G3に限定するとこの傾向がさらに強い（18.9%・全体31.8%比-12.9%）との結果。
  除外補正として採用するか正式検証する。

【ステップ】
  Step 1: G3での3走未満フラグ影響（訓練 2015〜2023）
  Step 2: 検証データ確認（2024〜2026 G3）
  Step 3: 除外補正の効果試算（見送り戦略）
  Step 4: 結論（採否・組み込み方法）

使い方:
  python3 hypothesis_g3_few_career_test.py
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

GRADE_PAT   = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
TEMPERATURE = 5.0
BET_UNIT    = 100
SEP         = '=' * 70
SEP2        = '─' * 70
ADOPT_THR   = 3.0   # 除外補正の採用閾値（的中率改善%ポイント）


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
    if n == 0:
        return (0.0, 1.0)
    p_hat = k / n
    center = (p_hat + z ** 2 / (2 * n)) / (1 + z ** 2 / n)
    margin = (z * math.sqrt(p_hat * (1 - p_hat) / n + z ** 2 / (4 * n ** 2))
              / (1 + z ** 2 / n))
    return (max(0.0, center - margin), min(1.0, center + margin))


def ci_tag(n):
    if n < 10:
        return '⚠️ n<10'
    if n < 30:
        return '△ n<30'
    return ''


def fmt_ci(n, k):
    lo, hi = wilson_ci(n, k)
    tag = ci_tag(n)
    return f"[{lo*100:.1f}%〜{hi*100:.1f}%] {tag}".strip()


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
# 2. 走歴辞書（全レース・全馬）
# ─────────────────────────────────────────────────
print("\n■ 走歴辞書を構築中...")
horse_all_hist = defaultdict(list)
for _, row in df_all[df_all['確定着順'] > 0].iterrows():
    h = str(row['馬名']).strip()
    horse_all_hist[h].append((str(row['race_date_str']), int(row['確定着順'])))
for h in horse_all_hist:
    horse_all_hist[h].sort(key=lambda x: x[0])
print(f"  全レース走歴: {len(horse_all_hist):,}頭")


def career_count_before(horse, before_date):
    """before_date より前の通算出走回数"""
    hist = horse_all_hist.get(horse, [])
    return len([d for d, _ in hist if d < before_date])


def is_few_career(horse, before_date, threshold=3):
    """通算出走回数が threshold 未満かどうか"""
    return career_count_before(horse, before_date) < threshold


# ─────────────────────────────────────────────────
# 3. エンジン（v7.3 4チーム合議・7軸重み付き）
# ─────────────────────────────────────────────────
print("\n■ pkl / 血統CSV 読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

sire_stats     = state.get('sire_stats', {})
jockey_stats   = state.get('jockey_stats', {})
distance_stats = state.get('distance_stats', {})
career_penalty = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
odds_mk_table  = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]

df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)

# place_rate 辞書（エッジ値計算用）
horse_place_rate = {}
for _, brow in df_blood.iterrows():
    name  = str(brow['馬名']).strip()
    total = (brow['全成績1着数'] + brow['全成績2着数'] +
             brow['全成績3着数'] + brow['全成績着外数'])
    if total >= 5:
        placed = (brow['全成績1着数'] + brow['全成績2着数'] + brow['全成績3着数'])
        horse_place_rate[name] = float(placed) / float(total)

print(f"  sire_stats:{len(sire_stats)}  jockey_stats:{len(jockey_stats)}  "
      f"distance_stats:{len(distance_stats)}  place_rate:{len(horse_place_rate):,}頭")


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


def score_to_win_prob(scores_dict, rdf):
    indices   = list(scores_dict.keys())
    score_arr = np.array([scores_dict[i] for i in indices])
    shifted   = score_arr - score_arr.max()
    sp        = np.exp(shifted / TEMPERATURE)
    sp        = sp / sp.sum()

    win_caps = []
    for idx in indices:
        horse = str(rdf.loc[idx, '馬名']).strip()
        pr    = horse_place_rate.get(horse, None)
        win_caps.append(pr / 3.0 if pr is not None else 1.0)
    win_caps = np.array(win_caps)

    capped = np.minimum(sp, win_caps)
    total  = capped.sum()
    capped = capped / total if total > 1e-9 else sp
    return {idx: float(p) for idx, p in zip(indices, capped)}


# ─────────────────────────────────────────────────
# 4. バックテスト（全グレード対象・グレード別に集計）
# ─────────────────────────────────────────────────
print("\n■ バックテスト実行中（全重賞）...")

records = []

for split, df_src in [('train', train_df), ('test', test_df)]:
    race_list = list(df_src.groupby('race_key'))
    total = len(race_list)
    print(f"  [{split}] {total}R 処理開始...")
    for i, (race_key, rdf) in enumerate(race_list):
        if i % 200 == 0:
            print(f"  [{split}] 進捗 {i}/{total}...")

        valid = rdf[rdf['確定着順'] > 0].copy()
        if len(valid) < 3:
            continue
        winner_rows = valid[valid['確定着順'] == 1]
        if winner_rows.empty:
            continue
        actual_winner = str(winner_rows.iloc[0]['馬名']).strip()
        race_date     = str(valid.iloc[0]['race_date_str'])
        grade_label   = str(rdf.iloc[0]['grade'])

        # 1番人気
        pop1_rows  = valid[valid['人気順'] == 1]
        pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None

        # エンジンスコア
        try:
            scores    = score_race(valid)
            win_probs = score_to_win_prob(scores, valid)
        except Exception:
            continue

        best_idx     = max(scores, key=scores.get)
        engine_row   = valid.loc[best_idx]
        engine_horse = str(engine_row['馬名']).strip()
        engine_pop   = int(engine_row['人気順'])
        engine_odds  = float(engine_row['単勝オッズ_num'])
        engine_hit   = (engine_horse == actual_winner)

        # エッジ値
        engine_ep   = win_probs.get(best_idx, 0.0)
        engine_edge = (engine_ep - (1.0 / engine_odds * 0.80)
                       if engine_odds > 0 else None)

        # キャリア走数フラグ
        n_career = career_count_before(engine_horse, race_date)
        few      = (n_career < 3)

        # キャリア帯
        if n_career == 0:
            career_band = '0走（未出走）'
        elif n_career == 1:
            career_band = '1走'
        elif n_career == 2:
            career_band = '2走'
        elif n_career <= 5:
            career_band = '3〜5走'
        elif n_career <= 10:
            career_band = '6〜10走'
        else:
            career_band = '11走以上'

        records.append({
            'split':        split,
            'race_key':     race_key,
            'race_date':    race_date,
            'year':         int(race_date[:4]),
            'grade':        grade_label,
            'engine_horse': engine_horse,
            'engine_pop':   engine_pop,
            'engine_odds':  engine_odds,
            'engine_hit':   engine_hit,
            'engine_ep':    engine_ep,
            'engine_edge':  engine_edge,
            'pop1_hit':     (pop1_horse == actual_winner) if pop1_horse else False,
            'few_career':   few,
            'n_career':     n_career,
            'career_band':  career_band,
        })

df = pd.DataFrame(records)
df_train = df[df['split'] == 'train']
df_test  = df[df['split'] == 'test']

print(f"\n  訓練レコード: {len(df_train)}R  検証レコード: {len(df_test)}R")


# ─────────────────────────────────────────────────
# ヘルパー
# ─────────────────────────────────────────────────
def hr(sub):
    return sub['engine_hit'].mean() * 100 if len(sub) > 0 else 0.0

def n_hit(sub):
    return int(sub['engine_hit'].sum())

def recovery(sub):
    """単勝回収率（%）"""
    if len(sub) == 0:
        return 0.0
    payout = sub.loc[sub['engine_hit'], 'engine_odds'].sum() * BET_UNIT
    total  = len(sub) * BET_UNIT
    return payout / total * 100

def pop1_hr(sub):
    return sub['pop1_hit'].mean() * 100 if len(sub) > 0 else 0.0


# ─────────────────────────────────────────────────
# ■ Step 1: 訓練データ（2015〜2023）グレード別
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 1】グレード別 3走未満フラグの影響（訓練データ: 2015〜2023）")
print(SEP)

print(f"""
  【1-1 グレード別 エンジン◎全体 vs 3走未満 vs 3走以上】
  （回収率は単勝◎購入で計算）

  グレード     全体                3走未満◎             3走以上◎
  {'':5} {'N':>4} {'的中率':>7} {'回収':>6} │ {'N':>4} {'的中率':>7} {'回収':>6} │ {'N':>4} {'的中率':>7} {'回収':>6}
  {SEP2}""")

for g in ['G1', 'G2', 'G3']:
    sub_all  = df_train[df_train['grade'] == g]
    sub_few  = sub_all[sub_all['few_career']]
    sub_many = sub_all[~sub_all['few_career']]
    print(f"  {g:<5}  {len(sub_all):>4}  {hr(sub_all):>6.1f}%  {recovery(sub_all):>5.1f}%"
          f" │ {len(sub_few):>4}  {hr(sub_few):>6.1f}%  {recovery(sub_few):>5.1f}%"
          f" │ {len(sub_many):>4}  {hr(sub_many):>6.1f}%  {recovery(sub_many):>5.1f}%")

all_tr    = df_train
few_tr    = df_train[df_train['few_career']]
many_tr   = df_train[~df_train['few_career']]
print(f"  {'合計':<5}  {len(all_tr):>4}  {hr(all_tr):>6.1f}%  {recovery(all_tr):>5.1f}%"
      f" │ {len(few_tr):>4}  {hr(few_tr):>6.1f}%  {recovery(few_tr):>5.1f}%"
      f" │ {len(many_tr):>4}  {hr(many_tr):>6.1f}%  {recovery(many_tr):>5.1f}%")

# G3に絞った詳細
g3_tr      = df_train[df_train['grade'] == 'G3']
g3_few_tr  = g3_tr[g3_tr['few_career']]
g3_many_tr = g3_tr[~g3_tr['few_career']]
diff_hr    = hr(g3_few_tr) - hr(g3_many_tr)
diff_rec   = recovery(g3_few_tr) - recovery(g3_many_tr)

print(f"""
  【1-2 G3 詳細比較】
  G3 全体      : {hr(g3_tr):.1f}%  回収率 {recovery(g3_tr):.1f}%  (n={len(g3_tr)}R)
  G3 3走未満◎  : {hr(g3_few_tr):.1f}%  回収率 {recovery(g3_few_tr):.1f}%  (n={len(g3_few_tr)}R)  的中{n_hit(g3_few_tr)}件
  G3 3走以上◎  : {hr(g3_many_tr):.1f}%  回収率 {recovery(g3_many_tr):.1f}%  (n={len(g3_many_tr)}R)  的中{n_hit(g3_many_tr)}件
  差（少−多）   : 的中率 {diff_hr:+.1f}%  回収率 {diff_rec:+.1f}%

  G3 3走未満 95%CI: {fmt_ci(len(g3_few_tr), n_hit(g3_few_tr))}
  G3 3走以上 95%CI: {fmt_ci(len(g3_many_tr), n_hit(g3_many_tr))}
  1番人気的中率   : {pop1_hr(g3_tr):.1f}%（基準）
""")

# G3 × 3走未満の年別推移
print("  【1-3 G3 × 3走未満◎ 年別的中率】")
print(f"  {'年':>5}  {'N':>4}  {'的中':>4}  {'的中率':>7}  {'回収率':>7}  95%CI")
print(f"  {SEP2}")
for yr in sorted(g3_tr['year'].unique()):
    sub_yr  = g3_tr[g3_tr['year'] == yr]
    sub_few_yr = sub_yr[sub_yr['few_career']]
    n, k = len(sub_few_yr), n_hit(sub_few_yr)
    rec  = recovery(sub_few_yr)
    if n == 0:
        print(f"  {yr:>5}  {'0':>4}  {'─':>4}  {'─':>7}  {'─':>7}  ─")
    else:
        lo, hi = wilson_ci(n, k)
        print(f"  {yr:>5}  {n:>4}  {k:>4}  {hr(sub_few_yr):>6.1f}%  {rec:>6.1f}%  [{lo*100:.1f}%〜{hi*100:.1f}%]")

# キャリア走数帯別（G3・訓練）
print(f"\n  【1-4 G3 × キャリア走数帯別 的中率（訓練）】")
print(f"  {'キャリア帯':15}  {'N':>5}  {'的中率':>7}  {'回収率':>7}  95%CI")
print(f"  {SEP2}")
band_order = ['0走（未出走）', '1走', '2走', '3〜5走', '6〜10走', '11走以上']
for band in band_order:
    sub = g3_tr[g3_tr['career_band'] == band]
    n, k = len(sub), n_hit(sub)
    if n == 0:
        continue
    lo, hi = wilson_ci(n, k)
    print(f"  {band:<15}  {n:>5}  {hr(sub):>6.1f}%  {recovery(sub):>6.1f}%  [{lo*100:.1f}%〜{hi*100:.1f}%]")


# ─────────────────────────────────────────────────
# ■ Step 2: 検証データ（2024〜2026 G3）
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 2】検証データ確認（2024〜2026 G3）")
print(SEP)

g3_te      = df_test[df_test['grade'] == 'G3']
g3_few_te  = g3_te[g3_te['few_career']]
g3_many_te = g3_te[~g3_te['few_career']]

diff_hr_te  = hr(g3_few_te) - hr(g3_many_te)
diff_rec_te = recovery(g3_few_te) - recovery(g3_many_te)

print(f"""
  【2-1 G3 訓練 vs 検証 比較】

               訓練（2015〜2023）              検証（2024〜2026）
               N      的中率  回収率        N      的中率  回収率
  {SEP2}
  G3 全体   {len(g3_tr):>5}  {hr(g3_tr):>6.1f}%  {recovery(g3_tr):>6.1f}%     {len(g3_te):>5}  {hr(g3_te):>6.1f}%  {recovery(g3_te):>6.1f}%
  3走未満◎  {len(g3_few_tr):>5}  {hr(g3_few_tr):>6.1f}%  {recovery(g3_few_tr):>6.1f}%     {len(g3_few_te):>5}  {hr(g3_few_te):>6.1f}%  {recovery(g3_few_te):>6.1f}%
  3走以上◎  {len(g3_many_tr):>5}  {hr(g3_many_tr):>6.1f}%  {recovery(g3_many_tr):>6.1f}%     {len(g3_many_te):>5}  {hr(g3_many_te):>6.1f}%  {recovery(g3_many_te):>6.1f}%
  差（少−多） {'─':>5}  {diff_hr:>+6.1f}%  {diff_rec:>+6.1f}%       {'─':>5}  {diff_hr_te:>+6.1f}%  {diff_rec_te:>+6.1f}%
""")

# 方向一致チェック
train_dir = (hr(g3_few_tr) < hr(g3_many_tr))
test_dir  = (hr(g3_few_te) < hr(g3_many_te))
direction_ok = (train_dir == test_dir)

print(f"  方向一致チェック（「3走未満◎ < 3走以上◎」が両データで成立）:")
print(f"    訓練: {'✓ 成立' if train_dir else '✗ 不成立'} （{hr(g3_few_tr):.1f}% vs {hr(g3_many_tr):.1f}%）")
print(f"    検証: {'✓ 成立' if test_dir  else '✗ 不成立'} （{hr(g3_few_te):.1f}% vs {hr(g3_many_te):.1f}%）")
print(f"    総合: {'✓ 訓練・検証で方向が一致' if direction_ok else '✗ 方向が逆転（過学習懸念）'}")

print(f"\n  【2-2 G3 3走未満◎ 信頼区間（検証データ）】")
print(f"  G3 3走未満◎  : {hr(g3_few_te):.1f}%  {fmt_ci(len(g3_few_te), n_hit(g3_few_te))}")
print(f"  G3 3走以上◎  : {hr(g3_many_te):.1f}%  {fmt_ci(len(g3_many_te), n_hit(g3_many_te))}")

# 年別（検証）
print(f"\n  【2-3 G3 × 3走未満◎ 年別（検証データ）】")
print(f"  {'年':>5}  {'N':>4}  {'的中':>4}  {'的中率':>7}  {'回収率':>7}")
print(f"  {SEP2}")
for yr in sorted(g3_te['year'].unique()):
    sub_yr     = g3_te[g3_te['year'] == yr]
    sub_few_yr = sub_yr[sub_yr['few_career']]
    n, k = len(sub_few_yr), n_hit(sub_few_yr)
    if n == 0:
        print(f"  {yr:>5}  {'0':>4}  {'─':>4}  {'─':>7}  {'─':>7}")
    else:
        print(f"  {yr:>5}  {n:>4}  {k:>4}  {hr(sub_few_yr):>6.1f}%  {recovery(sub_few_yr):>6.1f}%")


# ─────────────────────────────────────────────────
# ■ Step 3: 除外補正の効果試算
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 3】除外補正の効果試算")
print(SEP)
print("""
  「G3 × ◎が3走未満 → 見送り（購入しない）」とした場合の効果を測定する。
""")

# ── 3-1 G3における見送り効果（訓練）──
g3_buy_tr = g3_tr[~g3_tr['few_career']]   # 見送り後の購入対象

print(f"  【3-1 G3 単純見送り効果（訓練データ）】")
print(f"  {'戦略':30}  {'N':>5}  {'的中率':>7}  {'回収率':>7}  差（全体比）")
print(f"  {SEP2}")
print(f"  {'G3 全体購入':30}  {len(g3_tr):>5}  {hr(g3_tr):>6.1f}%  {recovery(g3_tr):>6.1f}%  基準")
print(f"  {'G3 3走未満を見送り':30}  {len(g3_buy_tr):>5}  {hr(g3_buy_tr):>6.1f}%  {recovery(g3_buy_tr):>6.1f}%"
      f"  的中率{hr(g3_buy_tr)-hr(g3_tr):+.1f}%  回収率{recovery(g3_buy_tr)-recovery(g3_tr):+.1f}%")

# ── 3-2 検証データでの見送り効果 ──
g3_buy_te = g3_te[~g3_te['few_career']]

print(f"\n  【3-2 G3 単純見送り効果（検証データ）】")
print(f"  {'戦略':30}  {'N':>5}  {'的中率':>7}  {'回収率':>7}  差（全体比）")
print(f"  {SEP2}")
print(f"  {'G3 全体購入':30}  {len(g3_te):>5}  {hr(g3_te):>6.1f}%  {recovery(g3_te):>6.1f}%  基準")
print(f"  {'G3 3走未満を見送り':30}  {len(g3_buy_te):>5}  {hr(g3_buy_te):>6.1f}%  {recovery(g3_buy_te):>6.1f}%"
      f"  的中率{hr(g3_buy_te)-hr(g3_te):+.1f}%  回収率{recovery(g3_buy_te)-recovery(g3_te):+.1f}%")

# 見送り率
skip_rate_tr = len(g3_few_tr) / len(g3_tr) * 100 if len(g3_tr) > 0 else 0
skip_rate_te = len(g3_few_te) / len(g3_te) * 100 if len(g3_te) > 0 else 0
print(f"\n  見送り割合: 訓練 {skip_rate_tr:.1f}%  /  検証 {skip_rate_te:.1f}%")

# ── 3-3 穴馬戦略（◎が4番人気以上 × 2200m未満）との交差 ──
print(f"\n  【3-3 穴馬戦略との交差（G3・訓練）】")
print(f"  （穴馬戦略: ◎が4番人気以上 × 距離2200m未満）\n")

g3_anaba_tr = g3_tr[
    (g3_tr['engine_pop'] >= 4)
]  # 距離フィルターはrace_keyから不明のため人気のみで簡略化

# 実際には距離情報が必要 → grade_dfから取得
# race_keyに距離が含まれないため、別途マージ
g3_tr_w_dist = g3_tr.merge(
    train_df[['race_key', '距離']].drop_duplicates('race_key'),
    on='race_key', how='left'
)
g3_te_w_dist = g3_te.merge(
    test_df[['race_key', '距離']].drop_duplicates('race_key'),
    on='race_key', how='left'
)
g3_tr_w_dist['距離_int'] = pd.to_numeric(g3_tr_w_dist['距離'], errors='coerce').fillna(0).astype(int)
g3_te_w_dist['距離_int'] = pd.to_numeric(g3_te_w_dist['距離'], errors='coerce').fillna(0).astype(int)

# 穴馬戦略対象（G3・◎4番人気以上・2200m未満）
ana_base_tr  = g3_tr_w_dist[(g3_tr_w_dist['engine_pop'] >= 4) & (g3_tr_w_dist['距離_int'] < 2200)]
ana_base_te  = g3_te_w_dist[(g3_te_w_dist['engine_pop'] >= 4) & (g3_te_w_dist['距離_int'] < 2200)]

# 穴馬戦略 × 見送り（3走未満除外）
ana_skip_tr  = ana_base_tr[~ana_base_tr['few_career']]
ana_skip_te  = ana_base_te[~ana_base_te['few_career']]

# 穴馬戦略 × エッジ+0.05以上
ana_edge_tr  = ana_base_tr[ana_base_tr['engine_edge'].notna() & (ana_base_tr['engine_edge'] >= 0.05)]
ana_edge_te  = ana_base_te[ana_base_te['engine_edge'].notna() & (ana_base_te['engine_edge'] >= 0.05)]

# 穴馬戦略 × 見送り × エッジ
ana_both_tr  = ana_skip_tr[ana_skip_tr['engine_edge'].notna() & (ana_skip_tr['engine_edge'] >= 0.05)]
ana_both_te  = ana_skip_te[ana_skip_te['engine_edge'].notna() & (ana_skip_te['engine_edge'] >= 0.05)]

print(f"  {'戦略':40}  {'訓練N':>5} {'的中':>4} {'回収':>6} │ {'検証N':>5} {'的中':>4} {'回収':>6}")
print(f"  {SEP2}")
rows = [
    ("穴馬戦略（G3 4番人気↑ 2200m未満）",  ana_base_tr,  ana_base_te),
    ("  × 3走未満を見送り",                 ana_skip_tr,  ana_skip_te),
    ("  × エッジ+0.05以上",                 ana_edge_tr,  ana_edge_te),
    ("  × 見送り × エッジ+0.05以上",        ana_both_tr,  ana_both_te),
]
for label, sub_tr, sub_te in rows:
    if len(sub_tr) == 0 and len(sub_te) == 0:
        print(f"  {label:<40}  {'─':>5}  {'─':>4}  {'─':>6} │  {'─':>5}  {'─':>4}  {'─':>6}")
        continue
    tr_str = f"{len(sub_tr):>5}  {n_hit(sub_tr):>3}  {recovery(sub_tr):>5.1f}%" if len(sub_tr) > 0 else '  ─      ─    ─'
    te_str = f"{len(sub_te):>5}  {n_hit(sub_te):>3}  {recovery(sub_te):>5.1f}%" if len(sub_te) > 0 else '  ─      ─    ─'
    print(f"  {label:<40}  {tr_str} │  {te_str}")

# ── 3-4 エッジ値フィルターとの単独比較（G3全体）──
print(f"\n  【3-4 G3全体での各フィルター効果比較（訓練・検証）】")
print(f"  {'フィルター':35}  {'訓練N':>5} {'的中率':>7} {'回収率':>7} │ {'検証N':>5} {'的中率':>7} {'回収率':>7}")
print(f"  {SEP2}")

g3_edge_tr = g3_tr_w_dist[g3_tr_w_dist['engine_edge'].notna() & (g3_tr_w_dist['engine_edge'] >= 0.05)]
g3_edge_te = g3_te_w_dist[g3_te_w_dist['engine_edge'].notna() & (g3_te_w_dist['engine_edge'] >= 0.05)]
g3_both_tr = g3_tr_w_dist[~g3_tr_w_dist['few_career'] &
                           g3_tr_w_dist['engine_edge'].notna() &
                           (g3_tr_w_dist['engine_edge'] >= 0.05)]
g3_both_te = g3_te_w_dist[~g3_te_w_dist['few_career'] &
                           g3_te_w_dist['engine_edge'].notna() &
                           (g3_te_w_dist['engine_edge'] >= 0.05)]

rows2 = [
    ("G3 全体",                       g3_tr_w_dist, g3_te_w_dist),
    ("G3 3走未満を見送り",             g3_tr_w_dist[~g3_tr_w_dist['few_career']], g3_te_w_dist[~g3_te_w_dist['few_career']]),
    ("G3 エッジ+0.05以上",             g3_edge_tr,   g3_edge_te),
    ("G3 見送り + エッジ+0.05以上",    g3_both_tr,   g3_both_te),
]
for label, sub_tr, sub_te in rows2:
    tr_str = f"{len(sub_tr):>5}  {hr(sub_tr):>6.1f}%  {recovery(sub_tr):>6.1f}%" if len(sub_tr) > 0 else '  ─      ─      ─'
    te_str = f"{len(sub_te):>5}  {hr(sub_te):>6.1f}%  {recovery(sub_te):>6.1f}%" if len(sub_te) > 0 else '  ─      ─      ─'
    print(f"  {label:<35}  {tr_str} │  {te_str}")


# ─────────────────────────────────────────────────
# ■ Step 4: 結論
# ─────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 4】結論")
print(SEP)

# 判定値
hr_g3_all_tr   = hr(g3_tr)
hr_g3_few_tr   = hr(g3_few_tr)
hr_g3_many_tr  = hr(g3_many_tr)
rec_g3_all_tr  = recovery(g3_tr)
rec_g3_buy_tr  = recovery(g3_buy_tr)

hr_g3_all_te   = hr(g3_te)
hr_g3_few_te   = hr(g3_few_te)
hr_g3_many_te  = hr(g3_many_te)
rec_g3_all_te  = recovery(g3_te)
hr_g3_buy_te   = hr(g3_buy_te)
rec_g3_buy_te  = recovery(g3_buy_te)

diff_hr_adopt  = hr_g3_many_tr - hr_g3_all_tr   # 見送り後の的中率改善幅
diff_rec_adopt = rec_g3_buy_tr - rec_g3_all_tr

ci_lo_few, ci_hi_few   = wilson_ci(len(g3_few_tr),  n_hit(g3_few_tr))
ci_lo_many, ci_hi_many = wilson_ci(len(g3_many_tr), n_hit(g3_many_tr))
ci_overlap = (ci_lo_few < ci_hi_many and ci_lo_many < ci_hi_few)

adopt_hr  = (diff_hr_adopt  >= ADOPT_THR)
adopt_rec = (diff_rec_adopt >= 0)
adopt     = adopt_hr and direction_ok

print(f"""
  ┌──────────────────────────────────────────────────────────────────────┐
  │   「G3 × ◎が3走未満 → 見送り」除外補正 採否判定                  │
  └──────────────────────────────────────────────────────────────────────┘

  【訓練データ（2015〜2023 G3）】
  全体          : 的中率 {hr_g3_all_tr:.1f}%  /  回収率 {rec_g3_all_tr:.1f}%  (n={len(g3_tr)}R)
  3走未満◎      : 的中率 {hr_g3_few_tr:.1f}%  /  95%CI {fmt_ci(len(g3_few_tr), n_hit(g3_few_tr))}
  3走以上◎      : 的中率 {hr_g3_many_tr:.1f}%  /  95%CI {fmt_ci(len(g3_many_tr), n_hit(g3_many_tr))}
  差（少-多）   : {hr_g3_few_tr - hr_g3_many_tr:+.1f}%ポイント
  95%CI 重なり  : {'あり（有意差なし）' if ci_overlap else 'なし（有意差の可能性）'}

  見送り後改善  : 的中率 {diff_hr_adopt:+.1f}%  /  回収率 {diff_rec_adopt:+.1f}%

  【検証データ（2024〜2026 G3）】
  全体          : 的中率 {hr_g3_all_te:.1f}%  /  回収率 {rec_g3_all_te:.1f}%  (n={len(g3_te)}R)
  3走未満◎      : 的中率 {hr_g3_few_te:.1f}%  /  回収率 {recovery(g3_few_te):.1f}%  (n={len(g3_few_te)}R)
  3走以上◎      : 的中率 {hr_g3_many_te:.1f}%  /  回収率 {recovery(g3_many_te):.1f}%  (n={len(g3_many_te)}R)
  見送り後改善  : 的中率 {hr_g3_buy_te - hr_g3_all_te:+.1f}%  /  回収率 {rec_g3_buy_te - rec_g3_all_te:+.1f}%
  訓練→検証 方向一致: {'✓' if direction_ok else '✗'}
""")

adopt_label = "【採用推奨】✓" if adopt else "【採用しない】✗"
print(f"  ─── 総合判定: {adopt_label} ───")

reason = []
if hr_g3_few_tr < hr_g3_many_tr:
    reason.append(f"G3 3走未満◎の的中率が3走以上より低い（{hr_g3_few_tr:.1f}% vs {hr_g3_many_tr:.1f}%）")
else:
    reason.append(f"G3 3走未満◎の的中率が3走以上を上回っている（除外補正の根拠なし）")

if ci_overlap:
    reason.append(f"95%CIが重なる → 統計的有意差なし（サンプルn={len(g3_few_tr)}）")
else:
    reason.append(f"95%CIが重ならない → 有意差の可能性あり")

if adopt_hr:
    reason.append(f"見送り後の的中率改善 {diff_hr_adopt:+.1f}%（採用閾値{ADOPT_THR}%以上）")
else:
    reason.append(f"見送り後の的中率改善 {diff_hr_adopt:+.1f}%（採用閾値{ADOPT_THR}%未満）")

if direction_ok:
    reason.append("訓練・検証で同方向 → 過学習なし")
else:
    reason.append("訓練・検証で方向が逆転 → 過学習懸念")

for r in reason:
    print(f"    ・{r}")

print(f"""
  ─── 組み込み方法（grade_race_predictor.py への反映案）───""")

if adopt:
    print(f"""
    ★ 採用: 最終購入判断サマリーに「G3 3走未満見送り」フラグを追加
      - 条件: grade=='G3' かつ ◎のキャリア走数 < 3
      - 実装: grade_race_predictor.py の print_result() に注意文を追記
        → 「⚠️ G3 × ◎がキャリア3走未満 → 見送り推奨」
      - エンジン本体は変更しない（スコアリングはそのまま）
      - run_prediction() の戻り値に career_count を追加する必要あり
""")
else:
    print(f"""
    ✗ 不採用: 除外補正フラグとして組み込まない
      主な理由を上記参照。

    ─── 運用上のメモ（非公式の参考情報）───
      - G3で◎がキャリア3走未満の場合、的中率がやや低い傾向はある
      - ただし統計的有意差が確認できないため、購入を完全に見送る根拠には不十分
      - 「的中率がやや低い」という知識として運用判断の参考にする程度に留める
      - エッジ値フィルター（+0.05以上）との組み合わせの方が効果的

    ─── 代替戦略: エッジ値フィルターとの比較 ───
      G3 エッジ+0.05以上フィルター:
        訓練 的中率{hr(g3_edge_tr):.1f}% 回収率{recovery(g3_edge_tr):.1f}% (n={len(g3_edge_tr)}R)
        検証 的中率{hr(g3_edge_te):.1f}% 回収率{recovery(g3_edge_te):.1f}% (n={len(g3_edge_te)}R)
      → エッジ値フィルターの方が回収率改善効果が大きい
""")

print(f"""
  ─── 全仮説・副産物 最終サマリー ───

  仮説  内容                              結果
  {SEP2}
  A     同コース×同距離実績               不採用（カバレッジ41%不足）
  B     直近3走トレンド                   不採用（差±1.3%・有意差なし）
  C     エッジ値フィルター（+0.05以上）    採用 → 234.6%回収率（検証）
  G1初  G1初出走フラグ（副産物①）         不採用（全体比-5.2%・有意差なし）
  G3少  G3×3走未満フラグ（副産物②）       {'採用' if adopt else '不採用'} ← 今回

  ★ 現時点で有効な戦略:
    1) エッジ値フィルター（+0.05以上・2200m未満）: 回収率234.6%
    2) 穴馬戦略（◎4番人気以上・2200m未満）: 回収率227.7%
    3) 上記の組み合わせ: 回収率304.6%
    4) 条件A〜D（穴馬フィルター）: 各条件の回収率参照

  ─── 次のアクション ───
    ① 4/19（土）週次フロー実行（馬場確認・条件A〜Dフィルター・重賞予測）
    ② 4/20（日）皐月賞 SATSUKI_RACE更新・--satsukiで実行
    ③ TARGET JVで2026-04-06〜以降のCSVを出力してDB更新
""")

print(SEP)
print("■ 検証完了")
print(SEP)
