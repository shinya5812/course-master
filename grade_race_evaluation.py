# -*- coding: utf-8 -*-
"""
grade_race_evaluation.py  -  COURSE MASTER v7.3 重賞評価レポート

【算出指標】
  1. 単勝回収率        : ◎1着時の払戻合計 ÷ 総ベット数 × 100
  2. 複勝回収率（推定）: ◎3着内の推定払戻合計 ÷ 総ベット数 × 100（複勝オッズ = 単勝×0.3）
  3. 人気帯別 的中率・回収率
  4. ◎の平均人気・平均オッズ
  5. 年別的中率推移（2015〜2026）
  6. グレード別 的中率・単勝回収率

【設計方針】
  - スコア計算は実際のエンジン（4チーム I/O/U/S 合議平均）を忠実に再現する
  - 複勝オッズ未収録のため「単勝×0.3」で推定（上限キャップなし・上限8.0倍の両表示）
  - 1ベット = 100円固定

使い方:
  python grade_race_evaluation.py
"""

import sys
import io
import os
import re
import json
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

BET_UNIT        = 100    # 1ベット（円）
PLACE_ODDS_MULT = 0.3    # 複勝オッズ推定係数
PLACE_ODDS_CAP  = 8.0    # 複勝オッズ上限（保守的推定用）

# grade検出パターン（全角・半角・ローマ数字対応）
GRADE_PATTERN = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')


# ============================================================
# ユーティリティ
# ============================================================
def detect_grade(race_name):
    if not race_name:
        return None
    m = GRADE_PATTERN.search(str(race_name))
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


def pop_tier(pop):
    """人気帯ラベル（表示順ソート用キー付き）"""
    if pop <= 0:
        return (4, '不明')
    elif pop <= 3:
        return (0, '1〜3番人気')
    elif pop <= 6:
        return (1, '4〜6番人気')
    elif pop <= 9:
        return (2, '7〜9番人気')
    else:
        return (3, '10番人気以上')


def dist_band(d):
    """距離帯ラベル"""
    if d <= 0:
        return '不明'
    elif d <= 1400:
        return '〜1400m'
    elif d <= 2000:
        return '1600〜2000m'
    else:
        return '2200m〜'


# ============================================================
# 1. pkl 読み込み
# ============================================================
print("■ pkl 読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

sire_stats      = state.get('sire_stats', {})
jockey_stats    = state.get('jockey_stats', {})
distance_stats  = state.get('distance_stats', {})
sire_dist_stats = state.get('sire_dist_stats', {})
bms_dist_stats  = state.get('bms_dist_stats', {})
career_penalty  = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
odds_mk_table   = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]

print(f"  sire_stats: {len(sire_stats)}件  "
      f"jockey_stats: {len(jockey_stats)}件  "
      f"distance_stats: {len(distance_stats)}件")


# ============================================================
# 2. CSV 読み込み・前処理
# ============================================================
print("\n■ CSV 読み込み中...")
dfs = []
for fpath in CSV_FILES:
    if os.path.exists(fpath):
        dfs.append(pd.read_csv(fpath, encoding='cp932', low_memory=False))
        print(f"  {os.path.basename(fpath)}: {len(dfs[-1])}件")

df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}件")

# 数値変換
for col, dtype in [
    ('確定着順',      'int'),
    ('人気順',        'int'),
    ('距離',          'int'),
    ('年齢',          'float'),
]:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(
        int if dtype == 'int' else float
    )

df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'],       errors='coerce')
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'],     errors='coerce').fillna(0.0)
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
df_all['斤量_num']           = pd.to_numeric(df_all['斤量'],           errors='coerce')
for col in ['通過順1', '通過順2', '通過順3', '通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# 血統データ結合（父馬名補完）
print("\n■ 血統データ読み込み...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)

blood_slim = df_blood[['血統登録番号', '種牡馬名', '母の父名']].copy()
blood_slim.columns = ['血統登録番号', '父馬名_b', '母の父馬名_b']
df_all = df_all.merge(blood_slim, on='血統登録番号', how='left')
df_all['父馬名']     = df_all['父馬名'].fillna(df_all['父馬名_b'])
df_all['母の父馬名'] = df_all['母の父馬名'].fillna(df_all['母の父馬名_b'])
df_all.drop(['父馬名_b', '母の父馬名_b'], axis=1, inplace=True)

# 重賞グレード列
df_all['grade'] = df_all['レース名'].apply(lambda x: detect_grade(x) if pd.notna(x) else None)
grade_df = df_all[df_all['grade'].notna()].copy()

# レースキー（年_月_日_場所_日次_Rno）
grade_df['race_key'] = (
    grade_df['年'].astype(str) + '_' +
    grade_df['月'].astype(str).str.zfill(2) + '_' +
    grade_df['日'].astype(str).str.zfill(2) + '_' +
    grade_df['場所'].astype(str) + '_' +
    grade_df['日次'].astype(str) + '_' +
    grade_df['レース番号'].astype(str).str.zfill(2)
)
grade_df = grade_df.drop_duplicates(subset=['race_key', '馬名'])

print(f"  重賞レコード: {len(grade_df):,}件  "
      f"G1:{(grade_df['grade']=='G1').sum():,}  "
      f"G2:{(grade_df['grade']=='G2').sum():,}  "
      f"G3:{(grade_df['grade']=='G3').sum():,}")


# ============================================================
# 3. スコア計算関数（v7.3 エンジン 4チーム合議を忠実再現）
# ============================================================
def score_horse(row, team_type='I'):
    """
    1頭の最終スコアを返す。
    team_type: 'I'=Upset, 'O'=Mainstream, 'U'=Utility, 'S'=Special
    """
    axes = {}

    # ── CF: キャリア形成 ──
    horse_name = str(row['馬名']).strip()
    bi = df_blood[df_blood['馬名'] == horse_name]
    if not bi.empty:
        total = int(bi['全成績1着数'].iloc[0] + bi['全成績2着数'].iloc[0] +
                    bi['全成績3着数'].iloc[0] + bi['全成績着外数'].iloc[0])
        wins  = int(bi['全成績1着数'].iloc[0])
        if total > 0:
            conf   = min(1.0, total / 10)
            cf     = wins / total * 100 * conf + 50 * (1 - conf)
            cf     = min(100, cf)
            pen    = career_penalty.get(total, 1.0)
            if pen < 1.0 and cf > 50:
                cf = 50 + (cf - 50) * pen
        else:
            cf = 20
    else:
        cf = 20
    axes['CF'] = cf

    # BF: 除外（Phase 3 Step 5）

    # ── SI: スピードインデックス（上がり3F） ──
    agari = row['上がり3Fタイム_sec']
    axes['SI'] = max(10, 100 - (agari - 30) * 2) if pd.notna(agari) else 50

    # ── JT: ジョッキー ──
    jockey = row['騎手名']
    if pd.notna(jockey) and jockey in jockey_stats:
        axes['JT'] = min(100, jockey_stats[jockey]['win_rate'] * 100)
    else:
        axes['JT'] = 50

    # ── PD: ペースデザイン（通過順） ──
    passages = [row.get('通過順1'), row.get('通過順2'),
                row.get('通過順3'), row.get('通過順4')]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    axes['PD'] = max(10, 100 - abs(np.mean(passages) - 7) * 3) if passages else 50

    # HP: 除外（Phase 3 Step 5）

    # ── BL: ベース力（人気順） ──
    pop = int(row['人気順'])
    axes['BL'] = max(10, 100 - pop * 5) if pop > 0 else 50

    # ── SPD: スピード能力（走破時計 z-score） ──
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

    # ── MK: マーケット（人気＋オッズ帯補正） ──
    odds = float(row['単勝オッズ_num']) if pd.notna(row.get('単勝オッズ_num')) else 0.0
    if 1 <= pop <= 5:
        mk = 100 - pop * 10
    elif 6 <= pop <= 10:
        mk = 50 - (pop - 5) * 5
    else:
        mk = max(10, 30 - (pop - 10))

    # チーム別特性（エンジンと同一ロジック）
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

    # ── 重み付き平均（7軸・Phase 3 Step 5確定版） ──
    W = {'CF': 2.0, 'SI': 2.0, 'SPD': 2.0, 'JT': 2.0,
         'PD': 1.0, 'BL': 0.3, 'MK': 0.3}
    keys = list(axes.keys())
    vals = [axes[k] for k in keys]
    wts  = [W.get(k, 1.0) for k in keys]
    return float(np.average(vals, weights=wts))


def score_race_4teams(rdf):
    """4チームの平均スコアを返す（エンジンの score_race 相当）"""
    teams = ['I', 'O', 'U', 'S']
    team_scores = {team: {} for team in teams}
    for team in teams:
        for idx, row in rdf.iterrows():
            try:
                team_scores[team][idx] = score_horse(row, team)
            except Exception:
                team_scores[team][idx] = 50.0

    final = {}
    for idx in rdf.index:
        final[idx] = np.mean([team_scores[t][idx] for t in teams])
    return final


# ============================================================
# 4. バックテスト実行
# ============================================================
print("\n■ バックテスト実行中...")
race_groups = grade_df.groupby('race_key')
total_races = len(race_groups)
print(f"  対象レース数: {total_races:,}R")

records = []  # 1レース1件

for i, (race_key, rdf) in enumerate(race_groups):
    if i % 300 == 0:
        print(f"  進捗: {i:,}/{total_races:,}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3:
        continue

    # 実際の1〜3着
    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_1st  = str(winner_rows.iloc[0]['馬名']).strip()
    placed_rows = valid[valid['確定着順'] <= 3]
    placed_set  = {str(r['馬名']).strip() for _, r in placed_rows.iterrows()}

    # 1番人気
    pop1_rows  = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None
    pop1_odds  = float(pop1_rows.iloc[0]['単勝オッズ_num']) if not pop1_rows.empty else 0.0

    # 4チームスコア計算
    scores = score_race_4teams(valid)
    if not scores:
        continue
    best_idx = max(scores, key=scores.get)

    best_row    = valid.loc[best_idx]
    pred_name   = str(best_row['馬名']).strip()
    pred_pop    = int(best_row['人気順'])
    pred_odds   = float(best_row['単勝オッズ_num']) if pd.notna(best_row['単勝オッズ_num']) else 0.0
    pred_finish = int(best_row['確定着順'])

    hit       = (pred_name == actual_1st)
    place_hit = pred_name in placed_set
    pop1_hit  = (pop1_horse == actual_1st) if pop1_horse else False

    # 年
    year = int(race_key.split('_')[0]) if '_' in race_key else 0

    meta = valid.iloc[0]
    dist_val = int(meta['距離']) if pd.notna(meta['距離']) else 0

    records.append({
        'race_key':    race_key,
        'year':        year,
        'grade':       str(rdf.iloc[0]['grade']),
        'venue':       str(meta['場所']).strip(),
        'distance':    dist_val,
        'dist_band':   dist_band(dist_val),
        'n_horses':    len(valid),
        'hit':         hit,
        'place_hit':   place_hit,
        'pop1_hit':    pop1_hit,
        'pop1_odds':   pop1_odds,
        'pred_pop':    pred_pop,
        'pred_odds':   pred_odds,
        'pred_finish': pred_finish,
    })

df_res = pd.DataFrame(records)
total_R = len(df_res)
print(f"  完了: 有効レース数 {total_R:,}R")


# ============================================================
# 5. 回収率計算ヘルパー
# ============================================================
def tansho_recovery(df):
    """単勝回収率（%）"""
    payout = df.loc[df['hit'], 'pred_odds'].sum() * BET_UNIT
    total  = len(df) * BET_UNIT
    return payout / total * 100 if total > 0 else 0.0


def place_recovery(df, cap=None):
    """
    複勝回収率推定（%）
    cap: None=上限なし, float=上限オッズ値（例: 8.0）
    """
    sub = df[df['place_hit']].copy()
    est_odds = sub['pred_odds'] * PLACE_ODDS_MULT
    if cap is not None:
        est_odds = est_odds.clip(upper=cap)
    payout = (est_odds * BET_UNIT).sum()
    total  = len(df) * BET_UNIT
    return payout / total * 100 if total > 0 else 0.0


def hit_rate(df):
    return df['hit'].mean() * 100 if len(df) > 0 else 0.0


def place_rate(df):
    return df['place_hit'].mean() * 100 if len(df) > 0 else 0.0


def pop1_recovery(df):
    """1番人気を◎とした場合の単勝回収率（pop1_odds 使用）"""
    payout = df.loc[df['pop1_hit'], 'pop1_odds'].sum() * BET_UNIT
    total  = len(df) * BET_UNIT
    return payout / total * 100 if total > 0 else 0.0


# ============================================================
# 6. 出力
# ============================================================
SEP  = '=' * 62
SEP2 = '─' * 62

def section(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


print()
print(SEP)
print("  COURSE MASTER v7.3  重賞評価レポート")
print(f"  対象: 2015〜2026年  重賞 {total_R:,}R")
print("  エンジン: 7軸重み付き平均 × 4チーム合議（I/O/U/S）")
print(SEP)

# ─────────────────────────────────────────────
# 指標 1〜2: 的中率・回収率（全体）
# ─────────────────────────────────────────────
section("【1】基本的中率")
engine_hit_rate = hit_rate(df_res)
pop1_hit_rate   = df_res['pop1_hit'].mean() * 100
diff            = engine_hit_rate - pop1_hit_rate

print(f"\n  ◎的中率（エンジン） : {engine_hit_rate:6.1f}%")
print(f"  ◎的中率（1番人気）  : {pop1_hit_rate:6.1f}%")
print(f"  差（エンジン優位）  : {diff:+6.1f}%")
print(f"\n  ◎複勝率（3着以内）  : {place_rate(df_res):6.1f}%")

section("【2】単勝・複勝回収率")
t_rec = tansho_recovery(df_res)
p_rec_cap  = place_recovery(df_res, cap=PLACE_ODDS_CAP)
p_rec_full = place_recovery(df_res, cap=None)

print(f"\n  単勝回収率          : {t_rec:6.1f}%")
print(f"  複勝回収率（推定・上限{PLACE_ODDS_CAP:.0f}倍キャップ）: {p_rec_cap:6.1f}%")
print(f"  複勝回収率（推定・上限なし・参考値）   : {p_rec_full:6.1f}%")
print(f"\n  ※ 複勝オッズ = 単勝オッズ × {PLACE_ODDS_MULT}  で推定")
print(f"    実際の複勝オッズは未収録のため精度は参考値")

# ─────────────────────────────────────────────
# 指標 3: 人気帯別
# ─────────────────────────────────────────────
section("【3】◎の人気帯別 的中率・回収率")

df_res['pop_tier_sort'] = df_res['pred_pop'].apply(lambda p: pop_tier(p)[0])
df_res['pop_tier']      = df_res['pred_pop'].apply(lambda p: pop_tier(p)[1])

print(f"\n  {'人気帯':<14} {'R数':>5}  {'選出率':>6}  {'的中率':>6}  "
      f"{'複勝率':>6}  {'単勝回収':>8}  {'複勝回収(上限)':>12}")
print(f"  {SEP2}")

tiers = ['1〜3番人気', '4〜6番人気', '7〜9番人気', '10番人気以上', '不明']
for tier in tiers:
    sub = df_res[df_res['pop_tier'] == tier]
    if len(sub) == 0:
        continue
    pct       = len(sub) / total_R * 100
    hr        = hit_rate(sub)
    pr        = place_rate(sub)
    t_r       = tansho_recovery(sub)
    p_r_cap   = place_recovery(sub, cap=PLACE_ODDS_CAP)
    print(f"  {tier:<14} {len(sub):>5}  {pct:>5.1f}%  {hr:>5.1f}%  "
          f"{pr:>5.1f}%  {t_r:>7.1f}%  {p_r_cap:>11.1f}%")

print(f"  {SEP2}")
print(f"  {'合計':<14} {total_R:>5}  {'100.0':>6}%  {engine_hit_rate:>5.1f}%  "
      f"{place_rate(df_res):>5.1f}%  {t_rec:>7.1f}%  {p_rec_cap:>11.1f}%")

# ─────────────────────────────────────────────
# 指標 4: ◎の平均人気・平均オッズ
# ─────────────────────────────────────────────
section("【4】◎の平均人気・平均オッズ")

valid_pop  = df_res[df_res['pred_pop'] > 0]['pred_pop']
valid_odds = df_res[df_res['pred_odds'] > 0]['pred_odds']

print(f"\n  ◎ 平均人気           : {valid_pop.mean():.1f} 番人気")
print(f"  ◎ 中央値人気         : {valid_pop.median():.0f} 番人気")
print(f"  ◎ 平均単勝オッズ     : {valid_odds.mean():.1f} 倍")
print(f"  ◎ 中央値単勝オッズ   : {valid_odds.median():.1f} 倍")
print(f"\n  ◎人気分布:")
pop_dist_map = defaultdict(int)
for _, row in df_res.iterrows():
    p = row['pred_pop']
    tier_key = pop_tier(p)[1]
    pop_dist_map[tier_key] += 1

for tier in tiers:
    cnt = pop_dist_map.get(tier, 0)
    if cnt == 0:
        continue
    bar = '■' * (cnt * 20 // total_R)
    print(f"    {tier:<14}: {cnt:>5}R ({cnt/total_R*100:5.1f}%)  {bar}")

# ─────────────────────────────────────────────
# 指標 5: 年別的中率推移
# ─────────────────────────────────────────────
section("【5】年別的中率推移（2015〜2026）")

year_df = df_res[df_res['year'] > 0].copy()
year_stats = (year_df.groupby('year')
              .agg(R=('hit', 'count'),
                   hits=('hit', 'sum'),
                   pop1=('pop1_hit', 'sum'),
                   place=('place_hit', 'sum'))
              .assign(engine_pct = lambda x: x['hits'] / x['R'] * 100,
                      pop1_pct   = lambda x: x['pop1'] / x['R'] * 100,
                      place_pct  = lambda x: x['place'] / x['R'] * 100))

print(f"\n  {'年':<6} {'R数':>5}  {'的中率':>6}  {'1人気':>6}  {'差':>6}  {'複勝率':>6}  単勝回収率")
print(f"  {SEP2}")
for yr, row in year_stats.iterrows():
    sub_yr  = year_df[year_df['year'] == yr]
    t_r_yr  = tansho_recovery(sub_yr)
    diff_yr = row['engine_pct'] - row['pop1_pct']
    trend   = '↑' if diff_yr >= 3 else ('↓' if diff_yr <= -3 else '→')
    print(f"  {int(yr):<6} {int(row['R']):>5}  {row['engine_pct']:>5.1f}%  "
          f"{row['pop1_pct']:>5.1f}%  {diff_yr:>+5.1f}%  "
          f"{row['place_pct']:>5.1f}%  {t_r_yr:>8.1f}%  {trend}")

# ─────────────────────────────────────────────
# 指標 6: グレード別
# ─────────────────────────────────────────────
section("【6】グレード別 的中率・回収率")

print(f"\n  {'グレード':<8} {'R数':>5}  {'的中率':>6}  {'1人気':>6}  {'差':>6}  "
      f"{'複勝率':>6}  {'単勝回収':>8}  {'複勝回収(上限)':>12}")
print(f"  {SEP2}")
for g in ['G1', 'G2', 'G3']:
    sub = df_res[df_res['grade'] == g]
    if len(sub) == 0:
        continue
    hr   = hit_rate(sub)
    pop1 = sub['pop1_hit'].mean() * 100
    pr   = place_rate(sub)
    t_r  = tansho_recovery(sub)
    p_r  = place_recovery(sub, cap=PLACE_ODDS_CAP)
    diff_g = hr - pop1
    print(f"  {g:<8} {len(sub):>5}  {hr:>5.1f}%  {pop1:>5.1f}%  {diff_g:>+5.1f}%  "
          f"{pr:>5.1f}%  {t_r:>7.1f}%  {p_r:>11.1f}%")

print(f"  {SEP2}")
hr   = engine_hit_rate
pop1 = pop1_hit_rate
pr   = place_rate(df_res)
t_r  = t_rec
p_r  = p_rec_cap
print(f"  {'合計':<8} {total_R:>5}  {hr:>5.1f}%  {pop1:>5.1f}%  {hr-pop1:>+5.1f}%  "
      f"{pr:>5.1f}%  {t_r:>7.1f}%  {p_r:>11.1f}%")

# ─────────────────────────────────────────────
# 追加: ◎が1番人気に選ばれた割合
# ─────────────────────────────────────────────
section("【付録】◎ = 1番人気の割合（エンジンの独自性確認）")

pop1_selected = (df_res['pred_pop'] == 1).sum()
pop1_selected_pct = pop1_selected / total_R * 100
print(f"\n  ◎が1番人気  : {pop1_selected:,}R / {total_R:,}R  = {pop1_selected_pct:.1f}%")
print(f"  ◎が2番人気  : {(df_res['pred_pop']==2).sum():,}R")
print(f"  ◎が3番人気  : {(df_res['pred_pop']==3).sum():,}R")
print(f"  ◎が4〜6人気 : {df_res['pred_pop'].between(4,6).sum():,}R")
print(f"  ◎が7〜9人気 : {df_res['pred_pop'].between(7,9).sum():,}R")
print(f"  ◎が10人気以上: {(df_res['pred_pop']>=10).sum():,}R")

print(f"\n  ✎ 1番人気を◎に選ぶ割合が高いほど、エンジンは")
print(f"    「市場の評価に近い」選択をしている。")
print(f"    低いほど「独自判断で穴馬を推す」傾向あり。")

# ================================================================
# 【7】「◎が4番人気以上」限定戦略 詳細検証
# ================================================================
section("【7】「◎が4番人気以上」限定戦略 詳細検証")

df_upset = df_res[df_res['pred_pop'] >= 4].copy()
upset_R  = len(df_upset)

# ─── 7-0: 全体指標 ───
print(f"\n  対象: ◎が4番人気以上のレースのみ")
print(f"  {upset_R}R  /  全{total_R}R中 {upset_R/total_R*100:.1f}%")
print()

u_hr   = hit_rate(df_upset)
u_pr   = place_rate(df_upset)
u_tr   = tansho_recovery(df_upset)
u_pr_c = place_recovery(df_upset, cap=PLACE_ODDS_CAP)
u_p1hr = df_upset['pop1_hit'].mean() * 100
u_p1rc = pop1_recovery(df_upset)

u_avg_pop  = df_upset[df_upset['pred_pop'] > 0]['pred_pop'].mean()
u_avg_odds = df_upset[df_upset['pred_odds'] > 0]['pred_odds'].mean()

print(f"  {'指標':<22}  {'エンジン◎':>10}  {'1番人気(比較)':>13}")
print(f"  {SEP2}")
print(f"  {'◎的中率':<22}  {u_hr:>9.1f}%  {u_p1hr:>12.1f}%")
print(f"  {'◎複勝率（3着以内）':<22}  {u_pr:>9.1f}%")
print(f"  {'単勝回収率':<22}  {u_tr:>9.1f}%  {u_p1rc:>12.1f}%")
print(f"  {'複勝回収率（上限{:.0f}倍）'.format(PLACE_ODDS_CAP):<22}  {u_pr_c:>9.1f}%")
print(f"  {'◎平均人気':<22}  {u_avg_pop:>9.1f}番人気")
print(f"  {'◎平均単勝オッズ':<22}  {u_avg_odds:>9.1f}倍")

# ─── 7-1: 年別 ───
print(f"\n  ─ 年別 的中率・回収率（安定性確認）─")
print(f"\n  {'年':<6} {'R数':>4}  {'的中率':>6}  {'1人気比較':>8}  {'単勝回収':>8}  判定")
print(f"  {SEP2}")

year_upset = df_upset[df_upset['year'] > 0].copy()
for yr in sorted(year_upset['year'].unique()):
    sub = year_upset[year_upset['year'] == yr]
    hr_  = hit_rate(sub)
    p1_  = sub['pop1_hit'].mean() * 100
    tr_  = tansho_recovery(sub)
    n    = len(sub)
    diff_ = tr_ - 100
    judge = '◎黒字' if tr_ >= 100 else '  赤字'
    print(f"  {int(yr):<6} {n:>4}  {hr_:>5.1f}%  {p1_:>7.1f}%  {tr_:>7.1f}%  {judge}")

# 安定性サマリー
profitable_years = sum(
    1 for yr in year_upset['year'].unique()
    if tansho_recovery(year_upset[year_upset['year'] == yr]) >= 100
)
total_years = year_upset['year'].nunique()
print(f"\n  回収率100%超: {profitable_years}/{total_years}年  "
      f"（安定性 {profitable_years/total_years*100:.0f}%）")

# ─── 7-2: グレード別 ───
print(f"\n  ─ グレード別 ─")
print(f"\n  {'グレード':<6} {'R数':>4}  {'的中率':>6}  {'1人気比較':>8}  {'単勝回収':>8}  複勝回収")
print(f"  {SEP2}")
for g in ['G1', 'G2', 'G3']:
    sub = df_upset[df_upset['grade'] == g]
    if len(sub) == 0:
        continue
    hr_  = hit_rate(sub)
    p1_  = sub['pop1_hit'].mean() * 100
    tr_  = tansho_recovery(sub)
    pr_  = place_recovery(sub, cap=PLACE_ODDS_CAP)
    print(f"  {g:<6} {len(sub):>4}  {hr_:>5.1f}%  {p1_:>7.1f}%  {tr_:>7.1f}%  {pr_:>7.1f}%")

# ─── 7-3: 会場別 ───
print(f"\n  ─ 会場別 単勝回収率（10R以上の会場のみ）─")
venue_stats = {}
for v in df_upset['venue'].unique():
    sub = df_upset[df_upset['venue'] == v]
    if len(sub) < 5:
        continue
    venue_stats[v] = {
        'R': len(sub), 'hr': hit_rate(sub),
        'tr': tansho_recovery(sub),
        'pr': place_recovery(sub, cap=PLACE_ODDS_CAP),
    }

sorted_venues = sorted(venue_stats.items(), key=lambda x: x[1]['tr'], reverse=True)
all_v = [v for v in sorted_venues if venue_stats[v[0]]['R'] >= 10]

if all_v:
    print(f"\n  【上位5場】")
    print(f"  {'会場':<6} {'R数':>4}  {'的中率':>6}  {'単勝回収':>8}  複勝回収")
    print(f"  {SEP2}")
    for v, s in all_v[:5]:
        print(f"  {v:<6} {s['R']:>4}  {s['hr']:>5.1f}%  {s['tr']:>7.1f}%  {s['pr']:>7.1f}%")

    if len(all_v) > 5:
        print(f"\n  【下位5場】")
        print(f"  {'会場':<6} {'R数':>4}  {'的中率':>6}  {'単勝回収':>8}  複勝回収")
        print(f"  {SEP2}")
        for v, s in all_v[-5:]:
            print(f"  {v:<6} {s['R']:>4}  {s['hr']:>5.1f}%  {s['tr']:>7.1f}%  {s['pr']:>7.1f}%")
else:
    # 10R未満でも全会場を表示
    print(f"\n  {'会場':<6} {'R数':>4}  {'的中率':>6}  {'単勝回収':>8}")
    print(f"  {SEP2}")
    for v, s in sorted_venues:
        print(f"  {v:<6} {s['R']:>4}  {s['hr']:>5.1f}%  {s['tr']:>7.1f}%")

# ─── 7-4: 距離帯別 ───
print(f"\n  ─ 距離帯別 ─")
print(f"\n  {'距離帯':<14} {'R数':>4}  {'的中率':>6}  {'1人気比較':>8}  {'単勝回収':>8}  複勝回収")
print(f"  {SEP2}")
for band in ['〜1400m', '1600〜2000m', '2200m〜']:
    sub = df_upset[df_upset['dist_band'] == band]
    if len(sub) == 0:
        continue
    hr_  = hit_rate(sub)
    p1_  = sub['pop1_hit'].mean() * 100
    tr_  = tansho_recovery(sub)
    pr_  = place_recovery(sub, cap=PLACE_ODDS_CAP)
    print(f"  {band:<14} {len(sub):>4}  {hr_:>5.1f}%  {p1_:>7.1f}%  {tr_:>7.1f}%  {pr_:>7.1f}%")

# ================================================================
# 【8】実用判断サマリー
# ================================================================
section("【8】実用判断サマリー：「◎が4番人気以上の重賞のみ単勝購入」")

# 年間平均ベット数
avg_bets_per_year = upset_R / max(total_years, 1)
# 1万円単位で換算（100円 × bet数 × 回収率）
annual_cost_100   = avg_bets_per_year * BET_UNIT
annual_return_100 = annual_cost_100 * u_tr / 100
annual_profit_100 = annual_return_100 - annual_cost_100

print(f"""
  ┌─────────────────────────────────────────────────┐
  │  戦略: 重賞でエンジン◎が4番人気以上 → 単勝購入  │
  └─────────────────────────────────────────────────┘

  【実績（2015〜2026年 バックテスト）】
  ─────────────────────────────────────
  対象レース数  : {upset_R}R  （年平均 {avg_bets_per_year:.1f}R）
  ◎的中率      : {u_hr:.1f}%
  ◎複勝率      : {u_pr:.1f}%
  単勝回収率   : {u_tr:.1f}%
  安定性       : {profitable_years}/{total_years}年が回収率100%超

  【1ベット = 100円 の場合の年間試算】
  ─────────────────────────────────────
  年間投資      : {annual_cost_100:,.0f}円
  年間期待払戻  : {annual_return_100:,.0f}円
  年間期待収益  : {annual_profit_100:+,.0f}円

  【ベースライン（1番人気購入）との比較】
  ─────────────────────────────────────
  同じ{upset_R}Rに1番人気を購入した場合:
    1番人気的中率  : {u_p1hr:.1f}%
    単勝回収率     : {u_p1rc:.1f}%
    エンジン優位   : 回収率 {u_tr - u_p1rc:+.1f}%

  【リスク評価】
  ─────────────────────────────────────""")

# 最悪年・最良年
yr_results = [
    (yr, tansho_recovery(year_upset[year_upset['year'] == yr]),
     len(year_upset[year_upset['year'] == yr]))
    for yr in sorted(year_upset['year'].unique())
]
best_yr  = max(yr_results, key=lambda x: x[1])
worst_yr = min(yr_results, key=lambda x: x[1])

print(f"  最良年  : {int(best_yr[0])}年  {best_yr[1]:.1f}%  （{best_yr[2]}R）")
print(f"  最悪年  : {int(worst_yr[0])}年  {worst_yr[1]:.1f}%  （{worst_yr[2]}R）")

# ドローダウン試算（最悪年の損失）
dd_cost   = worst_yr[2] * BET_UNIT
dd_return = dd_cost * worst_yr[1] / 100
dd_loss   = dd_return - dd_cost
print(f"\n  最悪年損失試算（100円ベット）: {dd_loss:+,.0f}円 / {worst_yr[2]}R")
print(f"\n  ※ バックテストは過去データへの過学習リスクあり。")
print(f"    実運用では1〜2年の実績確認を推奨。")

print(f"\n{SEP}")
print("  評価完了")
print(SEP)
print()

# ================================================================
# 【9】「◎が4番人気以上 × 長距離（2200m以上）除外」限定戦略
# ================================================================
section("【9】「◎が4番人気以上 × 長距離(2200m〜)除外」限定戦略")

df_filtered = df_upset[df_upset['dist_band'] != '2200m〜'].copy()
flt_R = len(df_filtered)
removed = upset_R - flt_R

print(f"\n  フィルター条件: ◎が4番人気以上  AND  距離 < 2200m")
print(f"  対象: {flt_R}R  （除外: {removed}R 長距離重賞）")
print()

f_hr   = hit_rate(df_filtered)
f_pr   = place_rate(df_filtered)
f_tr   = tansho_recovery(df_filtered)
f_pr_c = place_recovery(df_filtered, cap=PLACE_ODDS_CAP)
f_p1hr = df_filtered['pop1_hit'].mean() * 100
f_p1rc = pop1_recovery(df_filtered)
f_avg_pop  = df_filtered[df_filtered['pred_pop'] > 0]['pred_pop'].mean()
f_avg_odds = df_filtered[df_filtered['pred_odds'] > 0]['pred_odds'].mean()

print(f"  {'指標':<22}  {'長距離除外版':>12}  {'除外前(全体)':>12}  {'1番人気':>8}")
print(f"  {SEP2}")
print(f"  {'◎的中率':<22}  {f_hr:>11.1f}%  {u_hr:>11.1f}%  {f_p1hr:>7.1f}%")
print(f"  {'◎複勝率（3着以内）':<22}  {f_pr:>11.1f}%  {u_pr:>11.1f}%")
print(f"  {'単勝回収率':<22}  {f_tr:>11.1f}%  {u_tr:>11.1f}%  {f_p1rc:>7.1f}%")
print(f"  {'複勝回収率（上限{:.0f}倍）'.format(PLACE_ODDS_CAP):<22}  {f_pr_c:>11.1f}%  {u_pr_c:>11.1f}%")
print(f"  {'◎平均人気':<22}  {f_avg_pop:>10.1f}番人気  {u_avg_pop:>10.1f}番人気")
print(f"  {'◎平均単勝オッズ':<22}  {f_avg_odds:>11.1f}倍  {u_avg_odds:>11.1f}倍")

# ─── 9-1: 年別安定性 ───
print(f"\n  ─ 年別 的中率・回収率（安定性確認）─")
print(f"\n  {'年':<6} {'R数':>4}  {'的中率':>6}  {'1人気比較':>8}  {'単勝回収':>8}  判定")
print(f"  {SEP2}")

year_flt = df_filtered[df_filtered['year'] > 0].copy()
yr_results_f = []
for yr in sorted(year_flt['year'].unique()):
    sub = year_flt[year_flt['year'] == yr]
    hr_  = hit_rate(sub)
    p1_  = sub['pop1_hit'].mean() * 100
    tr_  = tansho_recovery(sub)
    n    = len(sub)
    judge = '◎黒字' if tr_ >= 100 else '  赤字'
    yr_results_f.append((yr, tr_, n))
    print(f"  {int(yr):<6} {n:>4}  {hr_:>5.1f}%  {p1_:>7.1f}%  {tr_:>7.1f}%  {judge}")

profitable_f = sum(1 for _, tr_, _ in yr_results_f if tr_ >= 100)
total_yrs_f  = len(yr_results_f)
best_f  = max(yr_results_f, key=lambda x: x[1])
worst_f = min(yr_results_f, key=lambda x: x[1])

print(f"\n  回収率100%超: {profitable_f}/{total_yrs_f}年  "
      f"（安定性 {profitable_f/total_yrs_f*100:.0f}%）")
print(f"  最良年: {int(best_f[0])}年  {best_f[1]:.1f}%  （{best_f[2]}R）")
print(f"  最悪年: {int(worst_f[0])}年  {worst_f[1]:.1f}%  （{worst_f[2]}R）")

# ─── 9-2: グレード別 ───
print(f"\n  ─ グレード別 ─")
print(f"\n  {'グレード':<6} {'R数':>4}  {'的中率':>6}  {'単勝回収':>8}  複勝回収")
print(f"  {SEP2}")
for g in ['G1', 'G2', 'G3']:
    sub = df_filtered[df_filtered['grade'] == g]
    if len(sub) == 0:
        continue
    hr_  = hit_rate(sub)
    tr_  = tansho_recovery(sub)
    pr_  = place_recovery(sub, cap=PLACE_ODDS_CAP)
    print(f"  {g:<6} {len(sub):>4}  {hr_:>5.1f}%  {tr_:>7.1f}%  {pr_:>7.1f}%")

# ─── 9-3: 距離帯別（確認用） ───
print(f"\n  ─ 距離帯別（長距離除外後の残り）─")
print(f"\n  {'距離帯':<14} {'R数':>4}  {'的中率':>6}  {'単勝回収':>8}  複勝回収")
print(f"  {SEP2}")
for band in ['〜1400m', '1600〜2000m']:
    sub = df_filtered[df_filtered['dist_band'] == band]
    if len(sub) == 0:
        continue
    hr_  = hit_rate(sub)
    tr_  = tansho_recovery(sub)
    pr_  = place_recovery(sub, cap=PLACE_ODDS_CAP)
    print(f"  {band:<14} {len(sub):>4}  {hr_:>5.1f}%  {tr_:>7.1f}%  {pr_:>7.1f}%")

# ─── 実用サマリー ───
avg_bets_f     = flt_R / max(total_yrs_f, 1)
annual_cost_f  = avg_bets_f * BET_UNIT
annual_ret_f   = annual_cost_f * f_tr / 100
annual_prof_f  = annual_ret_f - annual_cost_f
dd_cost_f      = worst_f[2] * BET_UNIT
dd_ret_f       = dd_cost_f * worst_f[1] / 100
dd_loss_f      = dd_ret_f - dd_cost_f

print(f"""
  ─ 実用サマリー ─

  ┌──────────────────────────────────────────────────────────┐
  │  戦略: 重賞◎が4番人気以上 × 距離2200m未満 → 単勝購入  │
  └──────────────────────────────────────────────────────────┘

  【改善効果（除外前 vs 除外後）】
  ─────────────────────────────────────
  単勝回収率   :  除外前 {u_tr:.1f}%  →  除外後 {f_tr:.1f}%  （{f_tr-u_tr:+.1f}%）
  的中率       :  除外前 {u_hr:.1f}%  →  除外後 {f_hr:.1f}%  （{f_hr-u_hr:+.1f}%）
  安定性       :  除外前 {profitable_years}/{total_years}年  →  除外後 {profitable_f}/{total_yrs_f}年

  【1ベット = 100円 の場合の年間試算】
  ─────────────────────────────────────
  年間ベット数  : {avg_bets_f:.1f}R
  年間投資      : {annual_cost_f:,.0f}円
  年間期待払戻  : {annual_ret_f:,.0f}円
  年間期待収益  : {annual_prof_f:+,.0f}円

  【リスク評価】
  最悪年損失試算（100円ベット）: {dd_loss_f:+,.0f}円 / {worst_f[2]}R

  ※ バックテストは過去データへの過学習リスクあり。実運用で慎重に確認を。
""")

print(f"\n{SEP}")
print("  全評価完了")
print(SEP)
print()
