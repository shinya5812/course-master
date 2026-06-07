# -*- coding: utf-8 -*-
"""
hypothesis_b_test.py  -  仮説B検証: 直近3走トレンドの予測力

【分類】
  W = 1〜3着 / M = 4〜6着 / L = 7着以下
  パターン表記: 最古→最新 例) W-M-L

【データリーク防止】
  訓練パターン辞書: 対象レース直前までの走歴を使用
  検証データには訓練期間外(2024〜)の重賞のみ使用

使い方: python3 hypothesis_b_test.py
"""

import sys, io, os, re, json, pickle
import sqlite3
import numpy as np
import pandas as pd
from collections import defaultdict
from itertools import product

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

GRADE_PATTERN  = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
SEP  = '=' * 66
SEP2 = '─' * 66
BET_UNIT = 100

# ──────────────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────────────
def detect_grade(name):
    if not name: return None
    m = GRADE_PATTERN.search(str(name))
    if not m: return None
    g = m.group()
    if   g[-1] in ('Ⅰ','1','１'): return 'G1'
    elif g[-1] in ('Ⅱ','2','２'): return 'G2'
    elif g[-1] in ('Ⅲ','3','３'): return 'G3'
    return None

def pos_to_label(pos):
    """着順 → W/M/L"""
    if pos <= 0: return None   # 異常値
    if pos <= 3: return 'W'
    if pos <= 6: return 'M'
    return 'L'

def make_pattern(labels):
    """ラベルリスト(3要素) → パターン文字列 or None"""
    if len(labels) < 3 or any(l is None for l in labels):
        return None
    return '-'.join(labels)   # 古い順→最新順

# ──────────────────────────────────────────────────────
# 1. race_results から走歴辞書を構築（全馬・全期間）
#    horse_history[horse_name] = sorted list of (race_date, finish_pos)
# ──────────────────────────────────────────────────────
print("■ race_results から走歴辞書を構築中...")
con = sqlite3.connect(DB_PATH)
df_hist = pd.read_sql_query(
    "SELECT horse_name, race_date, finish_pos FROM race_results WHERE finish_pos > 0 ORDER BY horse_name, race_date",
    con
)
con.close()
print(f"  読み込み: {len(df_hist):,}件")

horse_history = defaultdict(list)
for _, row in df_hist.iterrows():
    horse_history[str(row['horse_name']).strip()].append(
        (str(row['race_date']), int(row['finish_pos']))
    )
# 日付昇順でソート（ORDER BY で済んでいるが念のため）
for h in horse_history:
    horse_history[h].sort(key=lambda x: x[0])
print(f"  ユニーク馬数: {len(horse_history):,}頭")

def get_recent3(horse_name, before_date):
    """
    before_date より前の直近3走を取得し、着順のみのリストを返す（古い順）。
    3走未満の場合は実際にある走数分だけ返す。
    """
    hist = horse_history.get(horse_name, [])
    prior = [(d, p) for d, p in hist if d < before_date]
    return [p for d, p in prior[-3:]]  # 直近3走（古い順）

# ──────────────────────────────────────────────────────
# 2. CSV読み込み・重賞抽出
# ──────────────────────────────────────────────────────
print("\n■ CSV 読み込み中...")
dfs = []
for fp in CSV_FILES:
    if os.path.exists(fp):
        dfs.append(pd.read_csv(fp, encoding='cp932', low_memory=False))
        print(f"  {os.path.basename(fp)}: {len(dfs[-1]):,}件")

df_all = pd.concat(dfs, ignore_index=True)
for col in ['確定着順','人気順','距離']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(int)
df_all['単勝オッズ_num'] = pd.to_numeric(df_all['単勝オッズ'], errors='coerce').fillna(0.0)
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
grade_df = df_all[df_all['grade'].notna()].drop_duplicates(subset=['race_key','馬名']).copy()
print(f"\n  重賞レコード: {len(grade_df):,}件  "
      f"G1:{(grade_df['grade']=='G1').sum():,}  "
      f"G2:{(grade_df['grade']=='G2').sum():,}  "
      f"G3:{(grade_df['grade']=='G3').sum():,}")

train_df = grade_df[grade_df['year_int'] <= 2023].copy()
test_df  = grade_df[grade_df['year_int'] >= 2024].copy()
train_races = list(train_df.groupby('race_key'))
test_races  = list(test_df.groupby('race_key'))
print(f"  訓練重賞: {len(train_races):,}R  /  検証重賞: {len(test_races):,}R")

# ──────────────────────────────────────────────────────
# 共通処理: レースDF → {horse: pattern, ...}
# ──────────────────────────────────────────────────────
def compute_patterns(rdf, race_date):
    result = {}
    for _, row in rdf.iterrows():
        horse = str(row['馬名']).strip()
        recent = get_recent3(horse, race_date)
        labels = [pos_to_label(p) for p in recent]
        pat = make_pattern(labels) if len(labels) >= 3 else None
        result[horse] = pat
    return result

# ──────────────────────────────────────────────────────
# Step 1: パターン別勝率集計（訓練データ）
# ──────────────────────────────────────────────────────
print("\n■ Step1: 訓練データ（2015〜2023）パターン別集計中...")

pat_wins   = defaultdict(int)
pat_places = defaultdict(int)
pat_total  = defaultdict(int)
skip_r = 0

for i, (race_key, rdf) in enumerate(train_races):
    if i % 200 == 0:
        print(f"  進捗 {i}/{len(train_races)}...")
    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3: continue

    race_date  = str(valid.iloc[0]['race_date_str'])
    winner     = str(valid[valid['確定着順']==1].iloc[0]['馬名']).strip() if (valid['確定着順']==1).any() else None
    placed_set = {str(r['馬名']).strip() for _,r in valid[valid['確定着順']<=3].iterrows()}
    if not winner: continue

    patterns = compute_patterns(valid, race_date)
    for horse, pat in patterns.items():
        if pat is None: continue
        pat_total[pat]  += 1
        if horse == winner:       pat_wins[pat]   += 1
        if horse in placed_set:   pat_places[pat] += 1

print(f"  完了: {sum(pat_total.values()):,}頭のパターンを集計")

# 全27パターンを生成（一部未出現あり）
all_patterns = ['-'.join(p) for p in product(['W','M','L'], repeat=3)]

# 勝率・複勝率を計算（サンプル20件以上）
pat_stats = []
for pat in all_patterns:
    n = pat_total[pat]
    if n < 20: continue
    wr = pat_wins[pat]   / n
    pr = pat_places[pat] / n
    pat_stats.append({'pattern': pat, 'n': n, 'wins': pat_wins[pat],
                      'places': pat_places[pat], 'win_rate': wr, 'place_rate': pr})

pat_stats.sort(key=lambda x: x['win_rate'], reverse=True)

# 全パターンの全体勝率（基準値）
total_n    = sum(pat_total.values())
total_wins = sum(pat_wins.values())
base_wr    = total_wins / total_n if total_n > 0 else 0.0

print()
print(SEP)
print("  【Step 1】パターン別勝率（訓練データ: 2015〜2023）")
print(SEP)
print(f"\n  集計対象パターン数: {len(pat_stats)}種（20件以上）/ 全27種")
print(f"  全体基準勝率      : {base_wr*100:.2f}%  （1番人気との比較は Step2 で）")
print()
print(f"  {'パターン':<12} {'N':>5}  {'勝率':>7}  {'複勝率':>7}  傾向")
print(f"  {SEP2}")

TOP_N = 5
BOT_N = 5
top_patterns = {s['pattern'] for s in pat_stats[:TOP_N]}
bot_patterns = {s['pattern'] for s in pat_stats[-BOT_N:]}

print(f"  ─ 上位{TOP_N}パターン（勝率高い順）─")
for s in pat_stats[:TOP_N]:
    diff = s['win_rate'] - base_wr
    bar = '▲' * min(5, int(diff / 0.01))
    print(f"  {s['pattern']:<12} {s['n']:>5}  {s['win_rate']*100:>6.2f}%  "
          f"{s['place_rate']*100:>6.2f}%  {bar} ({diff*100:+.2f}%)")

print(f"\n  ─ 下位{BOT_N}パターン（勝率低い順）─")
for s in pat_stats[-BOT_N:][::-1]:
    diff = s['win_rate'] - base_wr
    bar = '▼' * min(5, int(abs(diff) / 0.005))
    print(f"  {s['pattern']:<12} {s['n']:>5}  {s['win_rate']*100:>6.2f}%  "
          f"{s['place_rate']*100:>6.2f}%  {bar} ({diff*100:+.2f}%)")

print(f"\n  ─ 全パターン一覧（20件以上） ─")
print(f"  {'パターン':<12} {'N':>5}  {'勝率':>7}  {'複勝率':>7}  ランク")
print(f"  {SEP2}")
for rank, s in enumerate(pat_stats, 1):
    tag = f'TOP{rank}' if rank <= TOP_N else (f'BOT{len(pat_stats)-rank+1}' if rank > len(pat_stats)-BOT_N else '')
    print(f"  {s['pattern']:<12} {s['n']:>5}  {s['win_rate']*100:>6.2f}%  "
          f"{s['place_rate']*100:>6.2f}%  {tag}")

# 勝率ランキング辞書（Step2・3で使用）
pat_rank = {s['pattern']: rank+1 for rank, s in enumerate(pat_stats)}  # 1=最高勝率
pat_wr_dict = {s['pattern']: s['win_rate'] for s in pat_stats}

# ──────────────────────────────────────────────────────
# Step 2: 予測力の検証（検証データ: 2024〜2026）
# ──────────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 2】予測力検証（検証データ: 2024〜2026）")
print(SEP)
print("\n■ 検証データ処理中...")

# 検証データでの各統計
trend_pred_hit  = 0   # トレンド◎が1着
trend_pred_R    = 0   # トレンド◎を立てたレース数
pop1_hit        = 0   # 1番人気が1着
pop1_total      = 0

# パターン別の出現数・的中数（検証データ）
test_pat_total  = defaultdict(int)
test_pat_wins   = defaultdict(int)
test_coverage   = 0   # パターン判定できた馬数
test_no_pat     = 0   # パターン判定不能（3走未満）

# カバレッジ別の詳細
no_pat_R = 0          # 全馬パターン不明のレース

for i, (race_key, rdf) in enumerate(test_races):
    if i % 50 == 0:
        print(f"  進捗 {i}/{len(test_races)}...")
    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3: continue

    race_date = str(valid.iloc[0]['race_date_str'])
    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty: continue
    actual_winner = str(winner_rows.iloc[0]['馬名']).strip()

    pop1_rows = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None
    pop1_total += 1
    if pop1_horse == actual_winner: pop1_hit += 1

    patterns = compute_patterns(valid, race_date)

    # パターン別集計（検証）
    for horse, pat in patterns.items():
        if pat:
            test_pat_total[pat] += 1
            test_coverage += 1
            if horse == actual_winner:
                test_pat_wins[pat] += 1
        else:
            test_no_pat += 1

    # トレンド◎を立てる: 既知パターンの中で最高勝率の馬
    best_horse  = None
    best_wr_val = -1.0
    for horse, pat in patterns.items():
        wr_val = pat_wr_dict.get(pat, -1.0) if pat else -1.0
        if wr_val > best_wr_val:
            best_wr_val = wr_val
            best_horse  = horse

    if best_horse and best_wr_val > 0:
        trend_pred_R += 1
        if best_horse == actual_winner:
            trend_pred_hit += 1
    else:
        no_pat_R += 1

trend_pred_wr = trend_pred_hit / trend_pred_R * 100 if trend_pred_R > 0 else 0.0
pop1_wr       = pop1_hit / pop1_total * 100 if pop1_total > 0 else 0.0
ENGINE_HIT    = 35.3
test_total    = len(test_races)

print(f"\n  検証対象: {test_total}R  /  トレンド◎を立てられたR: {trend_pred_R}R")
print(f"  予測不能（全馬パターン不明）: {no_pat_R}R / {test_total}R（{no_pat_R/test_total*100:.1f}%）")
print()
print(f"  {'手法':<38}  {'有効R':>5}  {'的中率':>7}  エンジン比")
print(f"  {SEP2}")
print(f"  {'現行7軸エンジン◎':<38}  {'全R':>5}  {ENGINE_HIT:>6.1f}%  （基準）")
print(f"  {'トレンド最高勝率パターン馬◎':<38}  {trend_pred_R:>5}  {trend_pred_wr:>6.1f}%  "
      f"{trend_pred_wr - ENGINE_HIT:>+6.1f}%")
print(f"  {'1番人気（比較基準）':<38}  {pop1_total:>5}  {pop1_wr:>6.1f}%  "
      f"{pop1_wr - ENGINE_HIT:>+6.1f}%")

# 検証データのパターン別勝率（上位パターンが検証でも有効か）
print(f"\n  ─ 検証データでの上位/下位パターン検証 ─")
print(f"\n  {'パターン':<12} {'訓練勝率':>8}  {'訓練N':>6}  {'検証N':>6}  {'検証勝率':>8}  整合性")
print(f"  {SEP2}")
for s in pat_stats[:TOP_N]:
    pat  = s['pattern']
    tn   = test_pat_total.get(pat, 0)
    tw   = test_pat_wins.get(pat, 0)
    twr  = tw / tn * 100 if tn > 0 else 0.0
    flag = '✓一致' if twr >= base_wr * 100 else '✗逆転'
    print(f"  {pat:<12} {s['win_rate']*100:>7.2f}%  {s['n']:>6}  {tn:>6}  "
          f"{twr:>7.2f}%  {flag}")
print(f"  {SEP2}")
for s in pat_stats[-BOT_N:][::-1]:
    pat  = s['pattern']
    tn   = test_pat_total.get(pat, 0)
    tw   = test_pat_wins.get(pat, 0)
    twr  = tw / tn * 100 if tn > 0 else 0.0
    flag = '✓一致' if twr <= base_wr * 100 else '✗逆転'
    print(f"  {pat:<12} {s['win_rate']*100:>7.2f}%  {s['n']:>6}  {tn:>6}  "
          f"{twr:>7.2f}%  {flag}")

# ──────────────────────────────────────────────────────
# Step 3: 現行エンジンとの組み合わせ効果
# ──────────────────────────────────────────────────────
print()
print(SEP)
print("  【Step 3】現行エンジンとの組み合わせ効果（検証データ）")
print(SEP)
print("\n■ エンジンスコア計算中（pkl + 4チーム合議）...")

# pkl読み込み
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)
sire_stats     = state.get('sire_stats', {})
jockey_stats   = state.get('jockey_stats', {})
distance_stats = state.get('distance_stats', {})
career_penalty = {1:0.70, 2:0.70, 3:0.70, 4:0.85, 5:0.85}
odds_mk_table  = [(0.0,2.0,0.85),(2.0,3.0,0.90),(3.0,999.0,1.00)]

# 血統CSV読み込み
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数','全成績2着数','全成績3着数','全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)

def score_horse_engine(row, team_type='I'):
    axes = {}
    horse_name = str(row['馬名']).strip()
    bi = df_blood[df_blood['馬名'] == horse_name]
    if not bi.empty:
        total = int(bi['全成績1着数'].iloc[0]+bi['全成績2着数'].iloc[0]+
                    bi['全成績3着数'].iloc[0]+bi['全成績着外数'].iloc[0])
        wins  = int(bi['全成績1着数'].iloc[0])
        if total > 0:
            conf = min(1.0, total/10)
            cf   = wins/total*100*conf + 50*(1-conf)
            cf   = min(100, cf)
            pen  = career_penalty.get(total, 1.0)
            if pen < 1.0 and cf > 50: cf = 50+(cf-50)*pen
        else: cf = 20
    else: cf = 20
    axes['CF'] = cf

    agari = row.get('上がり3Fタイム_sec')
    axes['SI'] = max(10,100-(float(agari)-30)*2) if pd.notna(agari) else 50

    jockey = row.get('騎手名')
    axes['JT'] = min(100, jockey_stats[jockey]['win_rate']*100) \
                 if pd.notna(jockey) and jockey in jockey_stats else 50

    passages = [row.get(c) for c in ['通過順1','通過順2','通過順3','通過順4']]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    axes['PD'] = max(10,100-abs(np.mean(passages)-7)*3) if passages else 50

    pop  = int(row['人気順'])
    axes['BL'] = max(10,100-pop*5) if pop > 0 else 50

    dist  = int(row['距離'])
    jikan = row.get('走破時計_sec')
    if dist in distance_stats and pd.notna(jikan):
        ds = distance_stats[dist]
        if ds['std_time'] > 0:
            z = (float(jikan)-ds['avg_time'])/ds['std_time']
            axes['SPD'] = max(10,min(100,50-z*10))
        else: axes['SPD'] = 50
    else: axes['SPD'] = 50

    odds = float(row['単勝オッズ_num']) if pd.notna(row.get('単勝オッズ_num')) else 0.0
    if 1<=pop<=5:   mk = 100-pop*10
    elif 6<=pop<=10: mk = 50-(pop-5)*5
    else:            mk = max(10,30-(pop-10))
    if team_type=='I' and pop>5:  mk+=(pop-5)*2
    elif team_type=='O' and pop<=3: mk+=(4-pop)*5
    if odds>0:
        for lo,hi,mult in odds_mk_table:
            if lo<odds<=hi:
                if mult!=1.0: mk=50+(mk-50)*mult
                break
    axes['MK'] = mk

    W = {'CF':2.0,'SI':2.0,'SPD':2.0,'JT':2.0,'PD':1.0,'BL':0.3,'MK':0.3}
    keys = list(axes.keys())
    vals = [axes[k] for k in keys]
    wts  = [W.get(k,1.0) for k in keys]
    return float(np.average(vals, weights=wts))

def score_race_engine(rdf):
    teams = ['I','O','U','S']
    team_scores = {t:{} for t in teams}
    for t in teams:
        for idx, row in rdf.iterrows():
            try: team_scores[t][idx] = score_horse_engine(row, t)
            except: team_scores[t][idx] = 50.0
    return {idx: np.mean([team_scores[t][idx] for t in teams]) for idx in rdf.index}

# 数値カラム付与（検証データ用）
test_df['上がり3Fタイム_sec'] = pd.to_numeric(test_df['上がり3Fタイム'], errors='coerce')
test_df['走破時計_sec']       = pd.to_numeric(test_df['走破時計'],       errors='coerce')
for col in ['通過順1','通過順2','通過順3','通過順4']:
    test_df[col] = pd.to_numeric(test_df[col], errors='coerce')

# 組み合わせ結果を格納
combo_results = []

for i, (race_key, rdf) in enumerate(test_races):
    if i % 50 == 0:
        print(f"  進捗 {i}/{len(test_races)}...")
    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3: continue

    race_date = str(valid.iloc[0]['race_date_str'])
    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty: continue
    actual_winner = str(winner_rows.iloc[0]['馬名']).strip()

    # エンジンスコアで◎を決定
    try:
        scores = score_race_engine(valid)
    except:
        continue
    best_idx   = max(scores, key=scores.get)
    engine_horse = str(valid.loc[best_idx,'馬名']).strip()
    engine_hit   = (engine_horse == actual_winner)

    # エンジン◎のトレンドパターン
    patterns = compute_patterns(valid, race_date)
    engine_pat = patterns.get(engine_horse)
    engine_rank = pat_rank.get(engine_pat) if engine_pat else None

    # トップパターン馬かどうか（上位半数を「上位」と定義）
    mid_rank = len(pat_stats) // 2
    engine_is_top = (engine_rank is not None and engine_rank <= mid_rank)
    engine_is_bot = (engine_rank is not None and engine_rank > mid_rank)
    engine_no_pat = (engine_pat is None)

    combo_results.append({
        'race_key':    race_key,
        'engine_hit':  engine_hit,
        'engine_pat':  engine_pat,
        'engine_rank': engine_rank,
        'is_top':      engine_is_top,
        'is_bot':      engine_is_bot,
        'no_pat':      engine_no_pat,
        'grade':       str(rdf.iloc[0]['grade']),
        'pop1_hit':    (str(valid[valid['人気順']==1].iloc[0]['馬名']).strip() == actual_winner
                        if (valid['人気順']==1).any() else False),
    })

df_combo = pd.DataFrame(combo_results)
n_combo = len(df_combo)

def hit_rate(df): return df['engine_hit'].mean()*100 if len(df)>0 else 0.0
def r_recovery(df):
    # 単勝回収率を近似（的中時オッズなし→的中率×平均オッズで代替不可）
    # ここでは的中率のみ算出
    return hit_rate(df)

print(f"\n  エンジンスコア計算完了: {n_combo}R")
print()
print(f"  {'条件':<38}  {'R数':>5}  {'的中率':>7}  エンジン全体比")
print(f"  {SEP2}")

# 全体
all_hr = hit_rate(df_combo)
print(f"  {'エンジン◎（全体）':<38}  {n_combo:>5}  {all_hr:>6.1f}%  （基準）")

# トレンド上位パターン
top_df = df_combo[df_combo['is_top']]
top_hr = hit_rate(top_df)
diff_top = top_hr - all_hr
print(f"  {'エンジン◎ × トレンド上位パターン':<38}  {len(top_df):>5}  {top_hr:>6.1f}%  {diff_top:>+6.1f}%")

# トレンド下位パターン
bot_df = df_combo[df_combo['is_bot']]
bot_hr = hit_rate(bot_df)
diff_bot = bot_hr - all_hr
print(f"  {'エンジン◎ × トレンド下位パターン':<38}  {len(bot_df):>5}  {bot_hr:>6.1f}%  {diff_bot:>+6.1f}%")

# パターン不明（3走未満）
nopat_df = df_combo[df_combo['no_pat']]
nopat_hr = hit_rate(nopat_df)
diff_nopat = nopat_hr - all_hr
print(f"  {'エンジン◎ × パターン不明（3走未満）':<38}  {len(nopat_df):>5}  {nopat_hr:>6.1f}%  {diff_nopat:>+6.1f}%")

# 購入戦略シミュレーション
# 「上位なら購入・下位なら見送り・不明は購入」
buy_df = df_combo[~df_combo['is_bot']]  # 下位を見送り
buy_hr = hit_rate(buy_df)
skip_n = len(bot_df)
print(f"\n  ─ 下位パターンを見送った場合の戦略効果 ─")
print(f"  購入対象: {len(buy_df)}R（下位{skip_n}R見送り）  的中率: {buy_hr:.1f}%  "
      f"（変化: {buy_hr-all_hr:+.1f}%）")

# グレード別
print(f"\n  ─ グレード別 ─")
print(f"  {'グレード':<6} {'全体':>6}  {'上位pat':>8}  {'下位pat':>8}  {'不明':>6}")
print(f"  {SEP2}")
for g in ['G1','G2','G3']:
    sub     = df_combo[df_combo['grade']==g]
    sub_top = sub[sub['is_top']]
    sub_bot = sub[sub['is_bot']]
    sub_nop = sub[sub['no_pat']]
    print(f"  {g:<6} {hit_rate(sub):>5.1f}%  {hit_rate(sub_top):>7.1f}%  "
          f"{hit_rate(sub_bot):>7.1f}%  {hit_rate(sub_nop):>5.1f}%")

# ──────────────────────────────────────────────────────
# Step 4: 結論
# ──────────────────────────────────────────────────────
ADOPT_THRESHOLD = 2.0

print()
print(SEP)
print("  【Step 4】結論")
print(SEP)

solo_diff   = trend_pred_wr - ENGINE_HIT
combo_diff  = max(top_hr - all_hr, buy_hr - all_hr)  # どちらが大きいか
solo_adopt  = solo_diff  >= ADOPT_THRESHOLD
combo_adopt = combo_diff >= ADOPT_THRESHOLD

print(f"""
  ┌────────────────────────────────────────────────────────────┐
  │  仮説B「直近3走トレンド」の予測力判定                    │
  └────────────────────────────────────────────────────────────┘

  【A. 単独軸としての有効性】
  ─────────────────────────────────────
  トレンド◎の的中率    : {trend_pred_wr:.1f}%
  現行エンジン◎の的中率 : {ENGINE_HIT:.1f}%
  差                   : {solo_diff:+.1f}%
  判定                 : {'【採用推奨】✓' if solo_adopt else '【採用しない】✗'}

  【B. 補正フラグとしての有効性（エンジン◎との組み合わせ）】
  ─────────────────────────────────────
  エンジン◎（全体）          : {all_hr:.1f}%
  エンジン◎ × 上位パターン   : {top_hr:.1f}%  （{top_hr-all_hr:+.1f}%）
  エンジン◎ × 下位パターン   : {bot_hr:.1f}%  （{bot_hr-all_hr:+.1f}%）
  下位パターン見送り戦略      : {buy_hr:.1f}%  （{buy_hr-all_hr:+.1f}%）
  判定                       : {'【採用推奨】✓' if combo_adopt else '【採用しない】✗'}
""")

# 原因分析
print("  【原因分析】")
if solo_diff < ADOPT_THRESHOLD:
    print("  ■ 単独軸として不十分な理由:")
    print(f"    - カバレッジ: {no_pat_R}R / {test_total}R（{no_pat_R/test_total*100:.0f}%）が3走未満で予測不能")
    print(f"    - 重賞は初挑戦・昇級馬が多く3走実績が存在しないケースが多い")
    coverage = (test_total - no_pat_R) / test_total * 100
    print(f"    - 有効カバレッジ: {coverage:.0f}%")

if combo_diff < ADOPT_THRESHOLD:
    print("\n  ■ 補正フラグとして不十分な理由:")
    print(f"    - 上位パターン ({top_hr:.1f}%) と下位パターン ({bot_hr:.1f}%) の差: "
          f"{top_hr-bot_hr:.1f}%ポイント")
    if top_hr - bot_hr < 5.0:
        print("    - 上位・下位パターンの的中率差が小さく、フィルター効果が限定的")
    print("    - 重賞はレベル・展開変動が大きく直近3走が必ずしも反映されない")
else:
    print("\n  ■ 補正フラグとして有効な理由:")
    if top_hr - all_hr >= 2.0:
        print(f"    - 上位パターンで{top_hr-all_hr:+.1f}%の改善: 信頼度アップフラグとして機能")
    if all_hr - bot_hr >= 2.0:
        print(f"    - 下位パターンで{bot_hr-all_hr:+.1f}%の悪化: 見送りフラグとして機能")

print(f"""
  【次のアクション候補】
  ─────────────────────────────────────
  1) 仮説C: 騎手×コース相性（JT軸改善候補）
  2) 直近1走のみに限定した簡易トレンド（W/非W）
  3) トレンド×人気帯の交差分析（穴馬戦略との組み合わせ）
""")

print(SEP)
print("  検証完了")
print(SEP)
print()
