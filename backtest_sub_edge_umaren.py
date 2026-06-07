# -*- coding: utf-8 -*-
"""
backtest_sub_edge_umaren.py
◎未達 × ○▲高エッジ馬連ルール バックテスト

【仮説】
  ◎のエッジが閾値未達（< +0.06）でも、
  ○▲（エンジン2〜9位）にエッジ+0.06以上の馬がいれば
  ◎×該当馬の馬連（各100円）を購入する。

【前回（backtest_circle_edge_rule.py）との差分】
  - 候補馬: ranks 2-5（○のみ）→ ranks 2-9（○▲に拡張）
  - ベット: 最高エッジ1頭のみ → 全qualifying馬に各100円
  - フィルター追加: 10頭以上のレースのみ

対象: 重賞（G1/G2/G3）2024〜2026年 / 10頭以上
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
    os.path.join(BASE_DIR, 'data', 'race', '結果202604110419.csv'),
]

TEMPERATURE    = 5.0
BET_UNIT       = 100
EDGE_THRESHOLD = 0.06
MIN_RUNNERS    = 10        # 10頭以上フィルター
GRADE_PAT      = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
TEST_YEAR_MIN  = 24        # 2024〜 が検証データ

SEP  = "=" * 64
SEP2 = "─" * 56


# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────
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
    if d <= 1400:
        return '〜1400m'
    elif d <= 2000:
        return '1600〜2000m'
    else:
        return '2200m〜'


def estimate_umaren_odds(odds_a, odds_b):
    """馬連オッズ推定（単勝オッズ積 ÷ 3.5）"""
    return max(1.0, (odds_a * odds_b) / 3.5)


# ──────────────────────────────────────────────
# pkl 読み込み
# ──────────────────────────────────────────────
print("■ pkl 読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

sire_stats     = state.get('sire_stats', {})
jockey_stats   = state.get('jockey_stats', {})
distance_stats = state.get('distance_stats', {})
career_penalty = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
odds_mk_table  = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]
print(f"  sire_stats:{len(sire_stats)}件  jockey_stats:{len(jockey_stats)}件")


# ──────────────────────────────────────────────
# CSV 読み込み
# ──────────────────────────────────────────────
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

horse_place_rate = {}
for _, brow in df_blood.iterrows():
    name  = str(brow['馬名']).strip()
    total = int(brow['全成績1着数'] + brow['全成績2着数'] +
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
test_df = grade_df[grade_df['year_2d'] >= TEST_YEAR_MIN].copy()
print(f"\n検証データ（2024〜）: {test_df['race_key'].nunique()}R（フィルター前）")


# ──────────────────────────────────────────────
# スコア計算関数（v7.3 再現）
# ──────────────────────────────────────────────
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

    jockey = row.get('騎手名')
    if pd.notna(jockey) and jockey in jockey_stats:
        axes['JT'] = min(100, jockey_stats[jockey]['win_rate'] * 100)
    else:
        axes['JT'] = 50

    passages = [row.get('通過順1'), row.get('通過順2'),
                row.get('通過順3'), row.get('通過順4')]
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


# ──────────────────────────────────────────────
# バックテスト実行
# ──────────────────────────────────────────────
print("\n■ バックテスト実行中（2024〜2026 重賞 10頭以上）...")
race_groups  = test_df.groupby('race_key')
total_races  = len(race_groups)
baseline_bets  = []   # ◎エッジ+0.06以上 → 単勝
new_rule_bets  = []   # ◎エッジ未達 & ○▲エッジ+0.06以上 → 馬連（全qualifying馬）
skipped_small  = 0

for i, (race_key, rdf) in enumerate(race_groups):
    if i % 100 == 0:
        print(f"  進捗: {i}/{total_races}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < MIN_RUNNERS:   # 10頭以上フィルター
        skipped_small += 1
        continue
    if valid[valid['確定着順'] == 1].empty:
        continue

    year      = int(race_key.split('_')[0])
    grade_lbl = str(rdf.iloc[0]['grade'])
    dist_val  = int(valid.iloc[0]['距離']) if pd.notna(valid.iloc[0]['距離']) else 0
    venue     = str(valid.iloc[0]['場所']).strip()

    scores    = score_race_4teams(valid)
    win_probs = score_to_win_prob(scores, valid)

    # 全馬エッジ計算
    horse_data = []
    for idx, row in valid.iterrows():
        raw_odds = float(row['単勝オッズ_num'])
        if raw_odds <= 0:
            continue
        market_prob = (1.0 / raw_odds) * 0.80
        wp   = win_probs.get(idx, 0.0)
        edge = wp - market_prob
        horse_data.append({
            'idx':        idx,
            'name':       str(row['馬名']).strip(),
            'score':      scores.get(idx, 50.0),
            'win_prob':   wp,
            'odds':       raw_odds,
            'edge':       edge,
            'finish_pos': int(row['確定着順']),
            'pop':        int(row['人気順']),
        })

    if not horse_data:
        continue

    # スコア降順でソート → ◎(rank1) / ○▲(ranks 2-9)
    sorted_h = sorted(horse_data, key=lambda x: x['score'], reverse=True)
    if len(sorted_h) < 2:
        continue

    honmei     = sorted_h[0]           # ◎
    sub_pool   = sorted_h[1:9]         # ○▲（最大8頭）
    top2_names = {h['name'] for h in sorted_h if h['finish_pos'] <= 2}

    # ── ベースライン（◎エッジ+0.06 & 距離2200m未満 → 単勝） ──
    if honmei['edge'] >= EDGE_THRESHOLD and dist_val < 2200:
        hit      = (honmei['finish_pos'] == 1)
        returned = honmei['odds'] * BET_UNIT if hit else 0
        baseline_bets.append({
            'race_key': race_key, 'year': year, 'grade': grade_lbl,
            'dist': dist_val, 'dist_band': dist_band(dist_val),
            'venue': venue, 'horse': honmei['name'],
            'odds': honmei['odds'], 'edge': honmei['edge'],
            'pop': honmei['pop'], 'finish': honmei['finish_pos'],
            'hit': hit, 'invested': BET_UNIT, 'returned': returned,
        })

    # ── 新ルール（◎エッジ未達 & ○▲エッジ+0.06以上 → 馬連×全qualifying馬） ──
    if honmei['edge'] < EDGE_THRESHOLD and dist_val < 2200:
        qualifying = [h for h in sub_pool if h['edge'] >= EDGE_THRESHOLD]
        for cand in qualifying:
            hit      = (honmei['name'] in top2_names) and (cand['name'] in top2_names)
            est_uma  = estimate_umaren_odds(honmei['odds'], cand['odds'])
            returned = est_uma * BET_UNIT if hit else 0
            new_rule_bets.append({
                'race_key':    race_key, 'year': year, 'grade': grade_lbl,
                'dist':        dist_val, 'dist_band': dist_band(dist_val),
                'venue':       venue,
                'honmei':      honmei['name'],
                'honmei_pop':  honmei['pop'],
                'honmei_edge': honmei['edge'],
                'honmei_odds': honmei['odds'],
                'honmei_fin':  honmei['finish_pos'],
                'cand':        cand['name'],
                'cand_pop':    cand['pop'],
                'cand_edge':   cand['edge'],
                'cand_odds':   cand['odds'],
                'cand_rank':   sub_pool.index(cand) + 2,  # 全体rank
                'est_umaren':  est_uma,
                'hit':         hit,
                'invested':    BET_UNIT,
                'returned':    returned,
                'honmei_fin':  honmei['finish_pos'],
                'cand_fin':    cand['finish_pos'],
            })

print(f"\n  10頭未満でスキップ: {skipped_small}R")
print(f"  ベースライン該当:   {len(baseline_bets)}R")
print(f"  新ルール発動:       {test_df['race_key'].nunique() - skipped_small}R中 "
      f"{len(set(b['race_key'] for b in new_rule_bets))}レースで発動 "
      f"（馬連票数: {len(new_rule_bets)}枚）")


# ──────────────────────────────────────────────
# 集計
# ──────────────────────────────────────────────
def summarize(bets, label):
    if not bets:
        print(f"\n【{label}】--- 該当なし ---")
        return {}
    unique_races = len(set(b['race_key'] for b in bets))
    n    = len(bets)
    hits = sum(1 for b in bets if b['hit'])
    inv  = sum(b['invested'] for b in bets)
    ret  = sum(b['returned'] for b in bets)
    roi  = ret / inv * 100 if inv > 0 else 0
    wr   = hits / n * 100
    print(f"\n【{label}】")
    print(f"  対象レース: {unique_races}R  馬券枚数: {n}枚  "
          f"的中: {hits}回  的中率: {wr:.1f}%")
    print(f"  投資: {inv:,}円  払戻: {ret:,.0f}円  回収率: {roi:.1f}%")
    return {'races': unique_races, 'tickets': n, 'hits': hits,
            'hit_rate': wr, 'roi': roi, 'inv': inv, 'ret': ret}

print(f"\n{SEP}")
b_stat = summarize(baseline_bets, "◎単勝エッジルール（ベースライン）")
n_stat = summarize(new_rule_bets,  "◎未達×○▲馬連エッジルール（新ルール）")

# グレード別
print(f"\n■ グレード別（新ルール）")
print(f"  {'G':^4} {'R数':>5} {'枚':>5} {'的中':>4} {'的中率':>6} {'回収率':>8}")
print("  " + SEP2)
for g in ['G1', 'G2', 'G3']:
    sub = [b for b in new_rule_bets if b['grade'] == g]
    if sub:
        hits = sum(1 for b in sub if b['hit'])
        inv  = sum(b['invested'] for b in sub)
        ret  = sum(b['returned'] for b in sub)
        roi  = ret / inv * 100 if inv > 0 else 0
        r    = len(set(b['race_key'] for b in sub))
        flag = " ★" if roi >= 100 else (" ✕" if roi < 50 else "")
        print(f"  {g:^4} {r:>5} {len(sub):>5} {hits:>4} "
              f"{hits/len(sub)*100:>5.1f}% {roi:>7.1f}%{flag}")

# 年別
print(f"\n■ 年別（新ルール）")
print(f"  {'年':^5} {'R数':>5} {'枚':>5} {'的中':>4} {'回収率':>8}  判定")
print("  " + SEP2)
year_map = defaultdict(lambda: {'races': set(), 'n':0,'hits':0,'inv':0,'ret':0})
for b in new_rule_bets:
    y = b['year']
    year_map[y]['races'].add(b['race_key'])
    year_map[y]['n']    += 1
    year_map[y]['hits'] += int(b['hit'])
    year_map[y]['inv']  += b['invested']
    year_map[y]['ret']  += b['returned']
year_results = {}
for y in sorted(year_map):
    d   = year_map[y]
    roi = d['ret'] / d['inv'] * 100 if d['inv'] > 0 else 0
    judge = "○" if roi >= 100 else ("△" if roi >= 70 else "✕")
    print(f"  {y}年  {len(d['races']):>5} {d['n']:>5} {d['hits']:>4} "
          f"{roi:>7.1f}%   {judge}")
    year_results[str(y)] = {'races': len(d['races']), 'tickets': d['n'],
                            'hits': d['hits'], 'roi': round(roi,1)}

# 距離帯別
print(f"\n■ 距離帯別（新ルール）")
print(f"  {'距離帯':^14} {'枚':>5} {'的中':>4} {'回収率':>8}")
print("  " + SEP2)
dist_map = defaultdict(lambda: {'n':0,'hits':0,'inv':0,'ret':0})
for b in new_rule_bets:
    k = b['dist_band']
    dist_map[k]['n']    += 1
    dist_map[k]['hits'] += int(b['hit'])
    dist_map[k]['inv']  += b['invested']
    dist_map[k]['ret']  += b['returned']
for k in ['〜1400m','1600〜2000m']:
    d = dist_map.get(k)
    if d and d['n']:
        roi  = d['ret'] / d['inv'] * 100 if d['inv'] > 0 else 0
        flag = " ★" if roi >= 100 else ""
        print(f"  {k:^14} {d['n']:>5} {d['hits']:>4} {roi:>7.1f}%{flag}")

# ○▲ランク別
print(f"\n■ 候補馬ランク別（新ルール）")
print(f"  {'印':^4} {'枚':>5} {'的中':>4} {'回収率':>8}  (rank2-4=○ / rank5-9=▲)")
print("  " + SEP2)
mark_map = {'○ (2-4)': [], '▲ (5-9)': []}
for b in new_rule_bets:
    if b['cand_rank'] <= 4:
        mark_map['○ (2-4)'].append(b)
    else:
        mark_map['▲ (5-9)'].append(b)
for mark, lst in mark_map.items():
    if lst:
        hits = sum(1 for b in lst if b['hit'])
        inv  = sum(b['invested'] for b in lst)
        ret  = sum(b['returned'] for b in lst)
        roi  = ret / inv * 100 if inv > 0 else 0
        flag = " ★" if roi >= 100 else (" ✕" if roi < 50 else "")
        print(f"  {mark:^10} {len(lst):>5} {hits:>4} {roi:>7.1f}%{flag}")

# 前回比較（○のみ・最高エッジ1頭）
prev_only_best = []
for race_key in set(b['race_key'] for b in new_rule_bets):
    bets_in_race = [b for b in new_rule_bets
                    if b['race_key'] == race_key and b['cand_rank'] <= 4]
    if bets_in_race:
        best = max(bets_in_race, key=lambda x: x['cand_edge'])
        prev_only_best.append(best)

if prev_only_best:
    hits = sum(1 for b in prev_only_best if b['hit'])
    inv  = sum(b['invested'] for b in prev_only_best)
    ret  = sum(b['returned'] for b in prev_only_best)
    roi  = ret / inv * 100 if inv > 0 else 0
    print(f"\n  参考（○のみ×最高エッジ1頭・前回方式）: "
          f"{len(prev_only_best)}枚  的中{hits}回  ROI={roi:.1f}%")

# 誤爆パターン
print(f"\n■ 誤爆パターン（新ルール・不的中）")
miss = [b for b in new_rule_bets if not b['hit']]
pattern = defaultdict(int)
for b in miss:
    h, c = b['honmei_fin'], b['cand_fin']
    if h == 1 and c > 2:
        pat = "◎1着だが候補が3着以下"
    elif c == 1 and h > 2:
        pat = "候補1着だが◎が3着以下"
    elif h <= 2 or c <= 2:
        pat = "片方は2着以内だが組み合わせ違い"
    else:
        pat = "◎も候補も3着以下"
    pattern[pat] += 1
for pat, cnt in sorted(pattern.items(), key=lambda x: -x[1]):
    print(f"  {pat}: {cnt}回 ({cnt/len(miss)*100:.1f}%)")

# 総合判断
print(f"\n{SEP}")
print("■ 総合判断")
print(SEP)
if b_stat and n_stat:
    print(f"  ベースライン（◎単勝）  : {b_stat['races']:3d}R  ROI {b_stat['roi']:6.1f}%")
    print(f"  新ルール（○▲馬連）    : {n_stat['races']:3d}R発動 {n_stat['tickets']:3d}枚  "
          f"ROI {n_stat['roi']:6.1f}%")
    black_years = sum(1 for v in year_results.values() if v['roi'] >= 100)
    total_years = len(year_results)
    print(f"  年別安定性             : {black_years}/{total_years}年が100%超 "
          f"({black_years/total_years*100:.0f}%)")

    if n_stat['roi'] >= 100 and black_years >= 2:
        rec = "★採用推奨（回収率100%超・安定性あり）"
    elif n_stat['roi'] >= 80:
        rec = "△様子見（80〜100%またはサンプル不足）"
    else:
        rec = "✗不採用（回収率低下または安定性なし）"
    print(f"\n  推奨: {rec}")
    print("  ※馬連オッズは推定値（単勝積÷3.5）のため実際払戻と差異あり")


# ──────────────────────────────────────────────
# JSON 保存
# ──────────────────────────────────────────────
out = {
    "meta": {
        "script": "backtest_sub_edge_umaren.py",
        "period": "2024〜2026 Grade（G1/G2/G3）10頭以上",
        "edge_threshold": EDGE_THRESHOLD,
        "sub_pool": "○▲（ranks 2-9）",
        "prev_script": "backtest_circle_edge_rule.py（○のみ・最高1頭・参照）",
        "prev_result": "ROI129.3%・黒字1/3年（不採用）"
    },
    "baseline": b_stat,
    "new_rule": n_stat,
    "by_year": year_results,
    "by_grade": {
        g: {
            'tickets': len([b for b in new_rule_bets if b['grade'] == g]),
            'hits': sum(1 for b in new_rule_bets if b['grade'] == g and b['hit']),
            'roi': (sum(b['returned'] for b in new_rule_bets if b['grade'] == g) /
                    sum(b['invested'] for b in new_rule_bets if b['grade'] == g) * 100
                    if any(b['grade'] == g for b in new_rule_bets) else 0)
        }
        for g in ['G1', 'G2', 'G3']
    },
    "detail_sample": [
        {k: v for k, v in b.items() if k != 'race_key'}
        for b in sorted(new_rule_bets, key=lambda x: x['cand_edge'], reverse=True)[:10]
    ]
}

out_path = os.path.join(BASE_DIR, 'backtest_sub_edge_umaren.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2, default=str)

print(f"\n保存先: {out_path}")
print("=== 完了 ===")
