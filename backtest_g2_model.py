# -*- coding: utf-8 -*-
"""
backtest_g2_model.py
G2専用モデル検討バックテスト

Step1: G2の構造分析（G1/G3との比較）
Step2: 仮説A/B/C検証（採用・棄却・継続観察を判定）
Step3: 補正案X/Y/Zバックテスト

テスト期間: 2022〜2026年 Grade（G1/G2/G3） 10頭以上
統計: 時系列分離済み（backtest_utils.get_stats_for_race を使用）
真のベースライン: 条件C（全軸リーク排除）= 的中率28.06% / ROI133.1%

出力: ターミナル + backtest_g2_model.json
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

# ベースライン参照値（条件C 全期間）
BASELINE_HIT_RATE = 28.06
BASELINE_ROI      = 133.1


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
    total_r = int(brow['全成績1着数'] + brow['全成績2着数'] +
                  brow['全成績3着数'] + brow['全成績着外数'])
    total_w = int(brow['全成績1着数'])
    blood_dict[name] = (total_r, total_w)
print(f"  血統CSV: {len(blood_dict):,}件")

df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None
)

# ============================================================
# 2. 統計マスター（時系列分離）のインポート
# ============================================================
sys.path.insert(0, BASE_DIR)
from backtest_utils import get_stats_for_race, score_horse_v73, WEIGHTS

# ============================================================
# 3. スコア計算ヘルパー（重み差し替え版）
# ============================================================
def score_horse_custom(row, stats, blood_dict, weights):
    """
    backtest_utils.score_horse_v73 と同じロジックだが、
    WEIGHTS を任意の weights dict で上書きできるバージョン。
    """
    axes = {}

    # CF軸（時系列分離統計優先）
    horse_name  = str(row.get('馬名', '') or '').strip()
    horse_stats = stats.get('horse_stats', {})
    if horse_name in horse_stats:
        hs      = horse_stats[horse_name]
        total_r = hs['total_races']
        total_w = hs['total_wins']
    elif blood_dict and horse_name in blood_dict:
        total_r, total_w = blood_dict[horse_name]
    else:
        total_r, total_w = 0, 0

    if total_r > 0:
        wr   = total_w / total_r
        conf = min(1.0, total_r / 10)
        cf   = wr * 100 * conf + 50 * (1 - conf)
        cf   = min(100.0, cf)
        pen  = CAREER_PENALTY.get(total_r, 1.0)
        if pen < 1.0 and cf > 50:
            cf = 50 + (cf - 50) * pen
    else:
        cf = 20.0
    axes['CF'] = cf

    # SI軸
    agari = row.get('上がり3Fタイム_sec')
    axes['SI'] = (max(10.0, 100 - (float(agari) - 30) * 2)
                  if pd.notna(agari) else 50.0)

    # JT軸
    jockey       = row.get('騎手名')
    jockey_stats = stats.get('jockey_stats', {})
    if pd.notna(jockey) and str(jockey) in jockey_stats:
        axes['JT'] = min(100.0, jockey_stats[str(jockey)]['win_rate'] * 100)
    else:
        axes['JT'] = 50.0

    # PD軸
    passages = [row.get(f'通過順{i}') for i in range(1, 5)]
    passages = [float(p) for p in passages if pd.notna(p) and float(p) > 0]
    axes['PD'] = (max(10.0, 100 - abs(float(np.mean(passages)) - 7) * 3)
                  if passages else 50.0)

    # BL軸
    pop = int(row.get('人気順', 0) or 0)
    axes['BL'] = max(10.0, 100 - pop * 5) if pop > 0 else 50.0

    # SPD軸
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

    # MK軸
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
    vals = [axes[k] for k in keys]
    wts  = [weights.get(k, 0.0) for k in keys]
    return float(np.average(vals, weights=wts))


# ============================================================
# 4. エッジ値計算（softmax T=5.0 で勝率推定）
# ============================================================
def compute_edge(scores_dict, row, target_idx):
    """
    target_idxの馬のエッジ値を返す。
    エッジ値 = softmax勝率推定 - 市場確率(1/オッズ×0.80)
    """
    score_vals = np.array(list(scores_dict.values()), dtype=float)
    T = 5.0
    exp_v = np.exp((score_vals - score_vals.mean()) / T)
    probs = exp_v / exp_v.sum()
    idx_list = list(scores_dict.keys())
    pos = idx_list.index(target_idx)
    est_prob = float(probs[pos])

    odds = float(row.get('単勝オッズ_num', 0) or 0)
    market_prob = (1.0 / odds * 0.80) if odds > 0 else 0.0
    return est_prob - market_prob


# ============================================================
# 5. 簡易ADI計算（バックテスト用・3要素 or オッズ分散のみ）
# ============================================================
def calc_simple_adi(valid_df):
    """
    簡易荒れ指数: オッズ分散を主指標とした0〜100の指数。
    1番人気オッズと3番人気オッズの比（ratio）から逆算。
    """
    sorted_by_pop = valid_df[valid_df['人気順'] > 0].sort_values('人気順')
    if len(sorted_by_pop) < 3:
        return 50.0

    pop1_odds = float(sorted_by_pop.iloc[0]['単勝オッズ_num'] or 0)
    pop3_odds = float(sorted_by_pop.iloc[2]['単勝オッズ_num'] or 0)

    if pop1_odds <= 0 or pop3_odds <= 0:
        return 50.0

    ratio = pop1_odds / pop3_odds
    if ratio >= 1.0:
        chaos_a = 0.0
    else:
        chaos_a = min(100.0, (1.0 - ratio) * 200.0)

    # 出走頭数多いほど荒れやすい補正
    n = len(sorted_by_pop)
    chaos_b = min(100.0, max(0.0, (n - 8) * 5.0))

    return round(0.7 * chaos_a + 0.3 * chaos_b, 1)


# ============================================================
# 6. テスト対象絞り込み（2022〜2026 Grade 10頭以上）
# ============================================================
test_df = df_all[(df_all['年4'] >= 2022) & (df_all['grade'].notna())].copy()
test_df['race_key'] = (
    test_df['年4'].astype(str) + '_' +
    test_df['月'].astype(str).str.zfill(2) + '_' +
    test_df['日'].astype(str).str.zfill(2) + '_' +
    test_df['場所'].astype(str) + '_' +
    test_df['日次'].astype(str) + '_' +
    test_df['レース番号'].astype(str).str.zfill(2)
)
test_df = test_df.drop_duplicates(subset=['race_key', '馬名'])
print(f"\n■ テスト対象: {len(test_df.groupby('race_key'))}R (2022-2026 Grade, 10頭フィルター前)")

# ============================================================
# 7. バックテスト本体
#    ベースライン（条件C）+ 補正案Y（BL/MK×0.1）を同時計算
#    ※補正案X（エッジ閾値）・補正案Z（穴馬戦略）はベースラインスコアから判定
# ============================================================
print("■ バックテスト実行中...")

WEIGHTS_BASE   = {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0, 'BL': 0.3, 'MK': 0.3}
WEIGHTS_Y      = {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0, 'BL': 0.1, 'MK': 0.1}
WEIGHTS_Y_FULL = {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0, 'BL': 0.0, 'MK': 0.0}

EDGE_THRESHOLD_STD = 0.06
EDGE_THRESHOLD_X   = 0.07
ANABA_POP_MIN      = 4

results = []
race_groups = list(test_df.groupby('race_key'))
total_rg    = len(race_groups)

for i, (rk, rdf) in enumerate(race_groups):
    if i % 200 == 0:
        print(f"  進捗: {i}/{total_rg}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 10:
        continue

    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_1st  = str(winner_rows.iloc[0]['馬名']).strip()
    actual_top3 = {str(h).strip() for h in valid[valid['確定着順'] <= 3]['馬名']}

    pop1_rows  = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None

    meta      = valid.iloc[0]
    year4     = int(meta['年4'])
    month     = int(meta['月'])
    day       = int(meta['日'])
    grade     = str(meta['grade'])
    dist      = int(meta['距離'])
    surface   = str(meta.get('トラック種別', meta.get('芝ダ', '不明')))
    race_date = f"{year4:04d}-{month:02d}-{day:02d}"

    try:
        sep_stats = get_stats_for_race(race_date)
    except FileNotFoundError:
        continue

    # ── ベースライン（条件C・標準重み）スコア計算 ──────────
    scores_base = {}
    for idx, row in valid.iterrows():
        try:
            scores_base[idx] = score_horse_custom(row, sep_stats, blood_dict, WEIGHTS_BASE)
        except Exception:
            scores_base[idx] = 50.0

    if not scores_base:
        continue

    best_idx_base  = max(scores_base, key=scores_base.get)
    pred_base      = str(valid.loc[best_idx_base, '馬名']).strip()
    odds_base      = float(valid.loc[best_idx_base, '単勝オッズ_num'] or 0)
    pop_base       = int(valid.loc[best_idx_base, '人気順'] or 0)

    # ベースラインのエッジ値
    edge_base = compute_edge(scores_base, valid.loc[best_idx_base], best_idx_base)

    # ── 補正案Y: BL/MK重み×0.1 スコア計算 ──────────────────
    scores_y = {}
    for idx, row in valid.iterrows():
        try:
            scores_y[idx] = score_horse_custom(row, sep_stats, blood_dict, WEIGHTS_Y)
        except Exception:
            scores_y[idx] = 50.0

    best_idx_y = max(scores_y, key=scores_y.get)
    pred_y     = str(valid.loc[best_idx_y, '馬名']).strip()
    odds_y     = float(valid.loc[best_idx_y, '単勝オッズ_num'] or 0)
    pop_y      = int(valid.loc[best_idx_y, '人気順'] or 0)
    edge_y     = compute_edge(scores_y, valid.loc[best_idx_y], best_idx_y)

    # ── 補正案Y完全除外: BL/MK重み=0 ────────────────────────
    scores_y0 = {}
    for idx, row in valid.iterrows():
        try:
            scores_y0[idx] = score_horse_custom(row, sep_stats, blood_dict, WEIGHTS_Y_FULL)
        except Exception:
            scores_y0[idx] = 50.0

    best_idx_y0 = max(scores_y0, key=scores_y0.get)
    pred_y0     = str(valid.loc[best_idx_y0, '馬名']).strip()
    odds_y0     = float(valid.loc[best_idx_y0, '単勝オッズ_num'] or 0)
    pop_y0      = int(valid.loc[best_idx_y0, '人気順'] or 0)

    # ── ADI（簡易） ──────────────────────────────────────────
    adi = calc_simple_adi(valid)

    # ── 補正案Xの判定（エッジ閾値+0.07適用でベット可否） ─────
    # ベースライン◎のエッジが+0.07以上ならベット（G2のみ適用）
    bet_x = edge_base >= EDGE_THRESHOLD_X

    # ── 補正案Zの判定（穴馬戦略優先: ◎が4番人気以上ならベット） ─
    bet_z = pop_base >= ANABA_POP_MIN

    results.append({
        'race_key':   rk,
        'grade':      grade,
        'year':       year4,
        'distance':   dist,
        'surface':    surface,
        'n_horses':   len(valid),
        'adi':        adi,
        # 実際の結果
        'actual_1st': actual_1st,
        'actual_pop': int(winner_rows.iloc[0]['人気順']),
        'actual_odds': float(winner_rows.iloc[0]['単勝オッズ_num'] or 0),
        # 1番人気
        'pop1_horse': pop1_horse,
        'pop1_hit':   pop1_horse == actual_1st if pop1_horse else False,
        # ベースライン（条件C）
        'pred_base':  pred_base,
        'hit_base':   pred_base == actual_1st,
        'place_base': pred_base in actual_top3,
        'odds_base':  odds_base,
        'pop_base':   pop_base,
        'edge_base':  round(edge_base, 4),
        # 補正案X（エッジ閾値+0.07・G2専用）
        'bet_x':      bet_x,
        'hit_x':      (pred_base == actual_1st) if bet_x else False,
        'odds_x':     odds_base if bet_x else 0,
        # 補正案Y（BL/MK×0.1）
        'pred_y':     pred_y,
        'hit_y':      pred_y == actual_1st,
        'place_y':    pred_y in actual_top3,
        'odds_y':     odds_y,
        'pop_y':      pop_y,
        'edge_y':     round(edge_y, 4),
        # 補正案Y完全除外（BL/MK=0）
        'pred_y0':    pred_y0,
        'hit_y0':     pred_y0 == actual_1st,
        'place_y0':   pred_y0 in actual_top3,
        'odds_y0':    odds_y0,
        'pop_y0':     pop_y0,
        # 補正案Z（穴馬戦略優先: ◎4番人気以上ならベット）
        'bet_z':      bet_z,
        'hit_z':      (pred_base == actual_1st) if bet_z else False,
        'odds_z':     odds_base if bet_z else 0,
    })

print(f"  完了: 有効レース数 {len(results)}R (10頭以上)")

df_res  = pd.DataFrame(results)
total_R = len(df_res)

# ============================================================
# 8. Step1: G2構造分析
# ============================================================
print("\n" + "=" * 80)
print("  ■ Step1: G2構造分析（G1/G3との比較）")
print("=" * 80)
print(f"  テスト期間: 2022〜2026年 / 対象レース: {total_R}R（10頭以上 Grade）")
print()

struct_data = {}
for g in ['G1', 'G2', 'G3']:
    sub = df_res[df_res['grade'] == g]
    n   = len(sub)
    if n == 0:
        continue

    # ◎の平均人気・オッズ（ベースライン）
    avg_pop_pred   = sub['pop_base'].mean()
    avg_odds_pred  = sub['odds_base'].mean()

    # 1着馬の平均人気・オッズ
    avg_pop_winner  = sub['actual_pop'].mean()
    avg_odds_winner = sub['actual_odds'].mean()

    # ADI分布
    adi_mean   = sub['adi'].mean()
    adi_median = sub['adi'].median()
    adi_q25    = sub['adi'].quantile(0.25)
    adi_q75    = sub['adi'].quantile(0.75)

    # ◎が1番人気と一致する割合
    pop1_match = (sub['pop_base'] == 1).mean() * 100

    # 的中率・ROI
    hit_rate = sub['hit_base'].mean() * 100
    roi      = calc_roi(sub, 'hit_base', 'odds_base')

    struct_data[g] = {
        'n': n,
        'avg_pop_pred':   round(avg_pop_pred, 2),
        'avg_odds_pred':  round(avg_odds_pred, 2),
        'avg_pop_winner': round(avg_pop_winner, 2),
        'avg_odds_winner':round(avg_odds_winner, 2),
        'adi_mean':       round(adi_mean, 1),
        'adi_median':     round(adi_median, 1),
        'adi_q25':        round(adi_q25, 1),
        'adi_q75':        round(adi_q75, 1),
        'pop1_match_pct': round(pop1_match, 1),
        'hit_rate':       round(hit_rate, 2),
        'roi':            round(roi, 1),
    }

    print(f"  【{g}】 {n}R")
    print(f"    ◎平均人気: {avg_pop_pred:.2f}位  ◎平均オッズ: {avg_odds_pred:.1f}倍")
    print(f"    1着馬 平均人気: {avg_pop_winner:.2f}位  平均オッズ: {avg_odds_winner:.1f}倍")
    print(f"    ADI 平均:{adi_mean:.1f} 中央値:{adi_median:.1f}  [Q25={adi_q25:.1f} Q75={adi_q75:.1f}]")
    print(f"    ◎が1番人気と一致: {pop1_match:.1f}%")
    print(f"    的中率: {hit_rate:.2f}%  単勝ROI: {roi:.1f}%")
    print()

# G2との差分サマリー
g1d = struct_data.get('G1', {})
g2d = struct_data.get('G2', {})
g3d = struct_data.get('G3', {})
print("  ─ G2 vs G1/G3 差分 ─")
print(f"  ◎平均人気:     G2={g2d['avg_pop_pred']:.2f} / G1={g1d['avg_pop_pred']:.2f} / G3={g3d['avg_pop_pred']:.2f}  "
      f"(G2-G1={g2d['avg_pop_pred']-g1d['avg_pop_pred']:+.2f}  G2-G3={g2d['avg_pop_pred']-g3d['avg_pop_pred']:+.2f})")
print(f"  1着馬 平均人気:G2={g2d['avg_pop_winner']:.2f} / G1={g1d['avg_pop_winner']:.2f} / G3={g3d['avg_pop_winner']:.2f}  "
      f"(G2-G1={g2d['avg_pop_winner']-g1d['avg_pop_winner']:+.2f}  G2-G3={g2d['avg_pop_winner']-g3d['avg_pop_winner']:+.2f})")
print(f"  ADI平均:       G2={g2d['adi_mean']:.1f}  / G1={g1d['adi_mean']:.1f}  / G3={g3d['adi_mean']:.1f}  "
      f"(G2-G1={g2d['adi_mean']-g1d['adi_mean']:+.1f}   G2-G3={g2d['adi_mean']-g3d['adi_mean']:+.1f})")
print(f"  ◎1番人気一致:  G2={g2d['pop1_match_pct']:.1f}% / G1={g1d['pop1_match_pct']:.1f}% / G3={g3d['pop1_match_pct']:.1f}%  "
      f"(G2-G1={g2d['pop1_match_pct']-g1d['pop1_match_pct']:+.1f}%  G2-G3={g2d['pop1_match_pct']-g3d['pop1_match_pct']:+.1f}%)")
print(f"  的中率:        G2={g2d['hit_rate']:.2f}% / G1={g1d['hit_rate']:.2f}% / G3={g3d['hit_rate']:.2f}%")
print(f"  ROI:           G2={g2d['roi']:.1f}% / G1={g1d['roi']:.1f}% / G3={g3d['roi']:.1f}%")

# ── G2の距離・トラック分布 ──
df_g2 = df_res[df_res['grade'] == 'G2'].copy()
print(f"\n  ─ G2 距離帯別内訳 ─")
dist_bins  = [0, 1400, 1800, 2200, 9999]
dist_labels = ['〜1400m', '1401〜1800m', '1801〜2200m', '2201m〜']
df_g2['dist_band'] = pd.cut(df_g2['distance'], bins=dist_bins, labels=dist_labels, right=True)
for band, grp in df_g2.groupby('dist_band', observed=False):
    n_band = len(grp)
    if n_band == 0:
        continue
    hit_b  = grp['hit_base'].mean() * 100
    roi_b  = calc_roi(grp, 'hit_base', 'odds_base')
    print(f"    {band:<14} {n_band:>4}R  的中率{hit_b:.1f}%  ROI{roi_b:.1f}%")

# ============================================================
# 9. Step2: 仮説検証
# ============================================================
print("\n" + "=" * 80)
print("  ■ Step2: 仮説検証")
print("=" * 80)

hypotheses = {}

# ── 仮説A: G2は荒れやすく、エンジンが堅い予測に偏っている ──
# 検証：ADI平均（G2 > G1/G3?）、◎平均人気（G2 < G1/G3 = 本命寄り?）
adi_diff_g2g1 = g2d['adi_mean'] - g1d['adi_mean']
adi_diff_g2g3 = g2d['adi_mean'] - g3d['adi_mean']
pop_diff_g2g1 = g2d['avg_pop_pred'] - g1d['avg_pop_pred']
pop_diff_g2g3 = g2d['avg_pop_pred'] - g3d['avg_pop_pred']

# 荒れやすい = G2のADIがG1より高い or G3より高い
is_g2_more_chaotic = (adi_diff_g2g1 > 2.0) or (adi_diff_g2g3 > 2.0)
# 堅い予測 = G2の◎平均人気がG1/G3より小さい（本命寄り）
is_g2_more_favorite = (pop_diff_g2g1 < -0.3) or (pop_diff_g2g3 < -0.3)
# 1着馬の平均人気がG2で高い（実際は荒れている）
is_winner_higher_pop = g2d['avg_pop_winner'] > g1d['avg_pop_winner']

hyp_a_verdict = '棄却'
if is_g2_more_chaotic and is_g2_more_favorite:
    hyp_a_verdict = '採用'
elif is_g2_more_chaotic or (is_g2_more_favorite and is_winner_higher_pop):
    hyp_a_verdict = '継続観察'

print(f"\n  【仮説A】G2は荒れやすく、エンジンが堅い予測に偏っている")
print(f"    ADI平均差（G2-G1）: {adi_diff_g2g1:+.1f}  （G2-G3）: {adi_diff_g2g3:+.1f}")
print(f"    ◎平均人気差（G2-G1）: {pop_diff_g2g1:+.2f}  （G2-G3）: {pop_diff_g2g3:+.2f}")
print(f"    1着馬平均人気 G2={g2d['avg_pop_winner']:.2f} vs G1={g1d['avg_pop_winner']:.2f} vs G3={g3d['avg_pop_winner']:.2f}")
print(f"    G2のADIがG1より高い: {is_g2_more_chaotic}")
print(f"    G2の◎が本命寄り（低人気数値）: {is_g2_more_favorite}")
print(f"    → 判定: 【{hyp_a_verdict}】")
hypotheses['A'] = {'verdict': hyp_a_verdict, 'adi_diff_g2g1': adi_diff_g2g1, 'adi_diff_g2g3': adi_diff_g2g3,
                   'pop_diff_g2g1': pop_diff_g2g1, 'pop_diff_g2g3': pop_diff_g2g3}

# ── 仮説B: G2は特定距離/トラックに偏りがあり統計サンプルが薄い ──
g2_n_total = len(df_g2)
dist_band_counts = df_g2['dist_band'].value_counts()
max_band_pct = (dist_band_counts.max() / g2_n_total * 100) if g2_n_total > 0 else 0

# サンプル数を距離帯別に確認（ROIの極端な偏りで判定）
roi_by_dist = {}
for band, grp in df_g2.groupby('dist_band', observed=False):
    n_band = len(grp)
    if n_band < 10:
        continue
    roi_b = calc_roi(grp, 'hit_base', 'odds_base')
    roi_by_dist[str(band)] = {'n': n_band, 'roi': round(roi_b, 1)}

roi_values = [v['roi'] for v in roi_by_dist.values()]
roi_range = max(roi_values) - min(roi_values) if len(roi_values) >= 2 else 0

hyp_b_verdict = '棄却'
if roi_range > 80.0 and max_band_pct > 50:
    hyp_b_verdict = '採用'
elif roi_range > 50.0 or max_band_pct > 50:
    hyp_b_verdict = '継続観察'

print(f"\n  【仮説B】G2は特定距離に偏りがあり統計サンプルが薄い")
print(f"    G2総レース数: {g2_n_total}R")
print(f"    最大距離帯集中率: {max_band_pct:.1f}%")
print(f"    距離帯別ROI幅: {roi_range:.1f}%pt")
for band, v in roi_by_dist.items():
    print(f"      {band}: {v['n']}R / ROI {v['roi']:.1f}%")
print(f"    → 判定: 【{hyp_b_verdict}】")
hypotheses['B'] = {'verdict': hyp_b_verdict, 'roi_range': round(roi_range, 1),
                   'max_band_pct': round(max_band_pct, 1), 'by_distance': roi_by_dist}

# ── 仮説C: G2はBL/MK軸の影響が強く、市場追認バイアスが出やすい ──
# 検証: ◎の平均人気（BL/MK除外で変化するか）、BL/MK除外でROIが改善するか
avg_pop_base_g2 = df_g2['pop_base'].mean()
avg_pop_y_g2    = df_g2['pop_y'].mean()
roi_base_g2     = calc_roi(df_g2, 'hit_base', 'odds_base')
roi_y_g2        = calc_roi(df_g2, 'hit_y', 'odds_y')
roi_y0_g2       = calc_roi(df_g2, 'hit_y0', 'odds_y0')

pop_change_g2  = avg_pop_y_g2 - avg_pop_base_g2
roi_change_g2  = roi_y_g2 - roi_base_g2
roi_change_y0  = roi_y0_g2 - roi_base_g2

# G1/G3での同じ変化量と比較
df_g1   = df_res[df_res['grade'] == 'G1']
df_g3   = df_res[df_res['grade'] == 'G3']
roi_change_g1 = calc_roi(df_g1, 'hit_y', 'odds_y') - calc_roi(df_g1, 'hit_base', 'odds_base')
roi_change_g3 = calc_roi(df_g3, 'hit_y', 'odds_y') - calc_roi(df_g3, 'hit_base', 'odds_base')

# G2でBL/MK除外のROI改善がG1/G3より大きければ仮説C支持
roi_improvement_g2_vs_avg = roi_change_g2 - ((roi_change_g1 + roi_change_g3) / 2)

hyp_c_verdict = '棄却'
if roi_change_g2 > 5.0 and roi_improvement_g2_vs_avg > 3.0:
    hyp_c_verdict = '採用'
elif roi_change_g2 > 0 and (roi_change_g2 > roi_change_g1 or roi_change_g2 > roi_change_g3):
    hyp_c_verdict = '継続観察'

print(f"\n  【仮説C】G2はBL/MK軸の影響が強く、市場追認バイアスが出やすい")
print(f"    G2 ◎平均人気 ベースライン→BL/MK×0.1: {avg_pop_base_g2:.2f}→{avg_pop_y_g2:.2f} ({pop_change_g2:+.2f}位)")
print(f"    G2 ROI変化（BL/MK×0.1）: {roi_base_g2:.1f}% → {roi_y_g2:.1f}% ({roi_change_g2:+.1f}%pt)")
print(f"    G2 ROI変化（BL/MK=0）:   {roi_base_g2:.1f}% → {roi_y0_g2:.1f}% ({roi_change_y0:+.1f}%pt)")
print(f"    G1 ROI変化（BL/MK×0.1）: {roi_change_g1:+.1f}%pt")
print(f"    G3 ROI変化（BL/MK×0.1）: {roi_change_g3:+.1f}%pt")
print(f"    G2のROI改善量 vs G1/G3平均: {roi_improvement_g2_vs_avg:+.1f}%pt")
print(f"    → 判定: 【{hyp_c_verdict}】")
hypotheses['C'] = {'verdict': hyp_c_verdict, 'roi_base': round(roi_base_g2, 1),
                   'roi_y': round(roi_y_g2, 1), 'roi_y0': round(roi_y0_g2, 1),
                   'roi_change_g2': round(roi_change_g2, 1),
                   'roi_change_g1': round(roi_change_g1, 1),
                   'roi_change_g3': round(roi_change_g3, 1)}

# ============================================================
# 10. Step3: G2補正案バックテスト
# ============================================================
print("\n" + "=" * 80)
print("  ■ Step3: G2補正案バックテスト（G1/G3への影響ゼロ確認込み）")
print("=" * 80)
print(f"  真のベースライン: 的中率{BASELINE_HIT_RATE:.2f}% / ROI{BASELINE_ROI:.1f}%")
print()

# G2のみ対象
df_g2_sub = df_res[df_res['grade'] == 'G2'].copy()
n_g2 = len(df_g2_sub)

# ── ベースライン（G2のみ） ────────────────────────────────
hit_base_g2  = df_g2_sub['hit_base'].mean() * 100
roi_base_g2  = calc_roi(df_g2_sub, 'hit_base', 'odds_base')
plc_base_g2  = df_g2_sub['place_base'].mean() * 100

print(f"  【ベースライン（条件C）】 G2 {n_g2}R")
print(f"    的中率: {hit_base_g2:.2f}%  複勝率: {plc_base_g2:.2f}%  ROI: {roi_base_g2:.1f}%")
print(f"    参考: 真のベースライン全体 = 的中率{BASELINE_HIT_RATE:.2f}% / ROI{BASELINE_ROI:.1f}%")
print()

# ── 補正案X: G2エッジ閾値+0.07 ──────────────────────────
bet_x_df  = df_g2_sub[df_g2_sub['bet_x']]
skip_x_df = df_g2_sub[~df_g2_sub['bet_x']]
n_bet_x   = len(bet_x_df)
n_skip_x  = len(skip_x_df)

if n_bet_x > 0:
    hit_x_rate = bet_x_df['hit_base'].mean() * 100
    roi_x      = calc_roi(bet_x_df, 'hit_base', 'odds_base')
    plc_x_rate = bet_x_df['place_base'].mean() * 100
else:
    hit_x_rate = roi_x = plc_x_rate = 0.0

print(f"  【補正案X】G2エッジ閾値+0.07（現行+0.06から引き上げ）")
print(f"    ベット対象: {n_bet_x}R（スキップ: {n_skip_x}R / 全体{n_g2}Rの{n_bet_x/n_g2*100:.1f}%）")
print(f"    的中率: {hit_x_rate:.2f}%  複勝率: {plc_x_rate:.2f}%  ROI: {roi_x:.1f}%")
print(f"    ROI変化: {roi_x - roi_base_g2:+.1f}%pt vs G2ベースライン")
print(f"    G1/G3への影響: なし（G2専用適用）")
print()

# ── 補正案Y: G2 BL/MK重み×0.1 ───────────────────────────
hit_y_g2  = df_g2_sub['hit_y'].mean() * 100
roi_y_g2  = calc_roi(df_g2_sub, 'hit_y', 'odds_y')
plc_y_g2  = df_g2_sub['place_y'].mean() * 100
avg_pop_y_g2_step3 = df_g2_sub['pop_y'].mean()

# BL/MK=0のバリアントも
hit_y0_g2 = df_g2_sub['hit_y0'].mean() * 100
roi_y0_g2 = calc_roi(df_g2_sub, 'hit_y0', 'odds_y0')
plc_y0_g2 = df_g2_sub['place_y0'].mean() * 100

print(f"  【補正案Y】G2 BL/MK軸重み×0.1（現行×0.3から削減）")
print(f"    的中率: {hit_y_g2:.2f}%  複勝率: {plc_y_g2:.2f}%  ROI: {roi_y_g2:.1f}%")
print(f"    ◎平均人気: {avg_pop_y_g2_step3:.2f}位（ベースライン{df_g2_sub['pop_base'].mean():.2f}位）")
print(f"    ROI変化: {roi_y_g2 - roi_base_g2:+.1f}%pt vs G2ベースライン")
print(f"  【補正案Y完全除外】G2 BL/MK=0")
print(f"    的中率: {hit_y0_g2:.2f}%  複勝率: {plc_y0_g2:.2f}%  ROI: {roi_y0_g2:.1f}%")
print(f"    ROI変化: {roi_y0_g2 - roi_base_g2:+.1f}%pt vs G2ベースライン")
# G1/G3への影響
hit_y_g1 = df_g1['hit_y'].mean() * 100 if len(df_g1) > 0 else 0
roi_y_g1 = calc_roi(df_g1, 'hit_y', 'odds_y') if len(df_g1) > 0 else 0
hit_y_g3 = df_g3['hit_y'].mean() * 100 if len(df_g3) > 0 else 0
roi_y_g3 = calc_roi(df_g3, 'hit_y', 'odds_y') if len(df_g3) > 0 else 0
print(f"    G1への影響 → 的中率:{hit_y_g1:.2f}% / ROI:{roi_y_g1:.1f}%（ベースライン:{g1d['hit_rate']:.2f}%/{g1d['roi']:.1f}%）")
print(f"    G3への影響 → 的中率:{hit_y_g3:.2f}% / ROI:{roi_y_g3:.1f}%（ベースライン:{g3d['hit_rate']:.2f}%/{g3d['roi']:.1f}%）")
print()

# ── 補正案Z: G2穴馬戦略優先（◎4番人気以上ならベット） ──────
bet_z_df  = df_g2_sub[df_g2_sub['bet_z']]
skip_z_df = df_g2_sub[~df_g2_sub['bet_z']]
n_bet_z   = len(bet_z_df)
n_skip_z  = len(skip_z_df)

if n_bet_z > 0:
    hit_z_rate = bet_z_df['hit_base'].mean() * 100
    roi_z      = calc_roi(bet_z_df, 'hit_base', 'odds_base')
    plc_z_rate = bet_z_df['place_base'].mean() * 100
else:
    hit_z_rate = roi_z = plc_z_rate = 0.0

print(f"  【補正案Z】G2 穴馬戦略優先（◎4番人気以上のみベット）")
print(f"    ベット対象: {n_bet_z}R（スキップ: {n_skip_z}R / 全体{n_g2}Rの{n_bet_z/n_g2*100:.1f}%）")
print(f"    的中率: {hit_z_rate:.2f}%  複勝率: {plc_z_rate:.2f}%  ROI: {roi_z:.1f}%")
print(f"    ROI変化: {roi_z - roi_base_g2:+.1f}%pt vs G2ベースライン")
print(f"    G1/G3への影響: なし（G2専用適用）")
print()

# ── 総合比較 ──────────────────────────────────────────────
print("  ─ 補正案 総合比較（G2のみ） ─")
print(f"  {'案':<20} {'対象R':>6} {'的中率':>8} {'複勝率':>8} {'ROI':>8} {'ROI差':>8}")
print(f"  {'─' * 66}")
rows_summary = [
    ('ベースライン',   n_g2,    hit_base_g2,  plc_base_g2,  roi_base_g2,  0.0),
    ('X: エッジ+0.07',n_bet_x,  hit_x_rate,   plc_x_rate,   roi_x,        roi_x  - roi_base_g2),
    ('Y: BL/MK×0.1',  n_g2,    hit_y_g2,     plc_y_g2,     roi_y_g2,     roi_y_g2 - roi_base_g2),
    ('Y: BL/MK=0',    n_g2,    hit_y0_g2,    plc_y0_g2,    roi_y0_g2,    roi_y0_g2 - roi_base_g2),
    ('Z: 穴馬優先',   n_bet_z,  hit_z_rate,   plc_z_rate,   roi_z,        roi_z  - roi_base_g2),
]
for name, n, hit, plc, roi, diff in rows_summary:
    diff_str = f'{diff:+.1f}%pt' if diff != 0.0 else '（基準）'
    print(f"  {name:<20} {n:>6} {hit:>7.2f}% {plc:>7.2f}% {roi:>7.1f}% {diff_str:>10}")

# ── 採用判定 ──────────────────────────────────────────────
print()
print("  ─ 採用判定 ─")
corrections = {
    'X_エッジ閾値+0.07': {'roi': roi_x,   'n': n_bet_x,  'roi_diff': roi_x   - roi_base_g2},
    'Y_BL/MK×0.1':      {'roi': roi_y_g2, 'n': n_g2,     'roi_diff': roi_y_g2 - roi_base_g2},
    'Y_BL/MK=0':         {'roi': roi_y0_g2,'n': n_g2,     'roi_diff': roi_y0_g2 - roi_base_g2},
    'Z_穴馬戦略優先':    {'roi': roi_z,   'n': n_bet_z,  'roi_diff': roi_z   - roi_base_g2},
}
for name, v in corrections.items():
    if v['roi_diff'] > 20.0 and v['n'] >= 10:
        verdict = '★★★ 採用推奨'
    elif v['roi_diff'] > 5.0 and v['n'] >= 10:
        verdict = '★★  採用検討'
    elif v['roi_diff'] > 0:
        verdict = '★   継続観察'
    else:
        verdict = '✗   不採用'
    print(f"    補正案{name}: ROI差{v['roi_diff']:+.1f}%pt / {v['n']}R → {verdict}")

# ── 年別 G2 内訳 ──────────────────────────────────────────
print(f"\n  ─ 年別 G2 ROI（ベースライン vs 補正案Y） ─")
print(f"  {'年':>5} {'R':>4} {'Base ROI':>10} {'Y ROI':>10} {'Y0 ROI':>10}")
for yr in sorted(df_g2_sub['year'].unique()):
    sub_yr  = df_g2_sub[df_g2_sub['year'] == yr]
    n_yr    = len(sub_yr)
    roi_yr  = calc_roi(sub_yr, 'hit_base', 'odds_base')
    roi_yr_y = calc_roi(sub_yr, 'hit_y', 'odds_y')
    roi_yr_y0 = calc_roi(sub_yr, 'hit_y0', 'odds_y0')
    print(f"  {yr:>5} {n_yr:>4} {roi_yr:>9.1f}% {roi_yr_y:>9.1f}% {roi_yr_y0:>9.1f}%")

print("\n■ 完了")

# ============================================================
# 11. JSON保存
# ============================================================
output = {
    'created':    pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
    'test_period': '2022-2026',
    'n_races':    total_R,
    'baseline': {
        'note': '条件C（全軸リーク排除）真のベースライン',
        'hit_rate': BASELINE_HIT_RATE,
        'roi':      BASELINE_ROI,
    },
    'step1_structure': struct_data,
    'step2_hypotheses': hypotheses,
    'step3_corrections': {
        'g2_baseline': {
            'n': n_g2,
            'hit_rate': round(hit_base_g2, 2),
            'place_rate': round(plc_base_g2, 2),
            'roi': round(roi_base_g2, 1),
        },
        'X_edge_007': {
            'n_bet': n_bet_x,
            'n_skip': n_skip_x,
            'hit_rate': round(hit_x_rate, 2),
            'place_rate': round(plc_x_rate, 2),
            'roi': round(roi_x, 1),
            'roi_diff': round(roi_x - roi_base_g2, 1),
        },
        'Y_blmk_01': {
            'n': n_g2,
            'hit_rate': round(hit_y_g2, 2),
            'place_rate': round(plc_y_g2, 2),
            'roi': round(roi_y_g2, 1),
            'roi_diff': round(roi_y_g2 - roi_base_g2, 1),
        },
        'Y_blmk_00': {
            'n': n_g2,
            'hit_rate': round(hit_y0_g2, 2),
            'place_rate': round(plc_y0_g2, 2),
            'roi': round(roi_y0_g2, 1),
            'roi_diff': round(roi_y0_g2 - roi_base_g2, 1),
        },
        'Z_anaba_strategy': {
            'n_bet': n_bet_z,
            'n_skip': n_skip_z,
            'hit_rate': round(hit_z_rate, 2),
            'place_rate': round(plc_z_rate, 2),
            'roi': round(roi_z, 1),
            'roi_diff': round(roi_z - roi_base_g2, 1),
        },
    },
}

out_path = os.path.join(BASE_DIR, 'backtest_g2_model.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n  → {out_path}")
