# -*- coding: utf-8 -*-
"""
leaktest_grade_races.py
時系列リーク検証: 統計マスターの全期間 vs 事前データ比較

条件A（現行）   : 全期間統計（2015〜2026）で 2024〜2026 重賞を予測
条件B（時系列分離）: 2023-12-31 以前の統計のみで 2024〜2026 重賞を予測

リーク対象軸:
  JT  (騎手勝率)    : jockey_stats を再集計
  SPD (走破時計Z)   : distance_stats を再集計
  CF  (キャリア形成): 条件A=血統CSV累計(未来含む) / 条件B=2023以前race_results集計

非リーク軸 (両条件で同一):
  SI/PD/BL/MK: レース結果行の実測値を直接使用するため未来情報なし

出力:
  leaktest_stats_pre2024.json  条件B用統計サマリー
  leaktest_result.json         比較結果
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
CSV_FILES  = [
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

GRADE_PATTERN = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
CAREER_PENALTY = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
ODDS_MK_TABLE  = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]
WEIGHTS = {'CF': 2.0, 'SI': 2.0, 'SPD': 2.0, 'JT': 2.0,
           'PD': 1.0, 'BL': 0.3, 'MK': 0.3}

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
    if g[-1] in ('Ⅱ', '2', '２'):
        return 'G2'
    if g[-1] in ('Ⅲ', '3', '３'):
        return 'G3'
    return None


# ============================================================
# 1. データ読み込み
# ============================================================
print("■ CSVデータ読み込み中...")
dfs = []
for f in CSV_FILES:
    if os.path.exists(f):
        df = pd.read_csv(f, encoding='cp932', low_memory=False)
        dfs.append(df)
        print(f"  {os.path.basename(f)}: {len(df):,}件")
df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}件")

# 数値化
df_all['確定着順']           = pd.to_numeric(df_all['確定着順'], errors='coerce').fillna(0).astype(int)
df_all['人気順']             = pd.to_numeric(df_all['人気順'], errors='coerce').fillna(0).astype(int)
df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'], errors='coerce')
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'], errors='coerce').fillna(0)
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
df_all['距離']               = pd.to_numeric(df_all['距離'], errors='coerce').fillna(0).astype(int)
df_all['年']                 = pd.to_numeric(df_all['年'], errors='coerce').fillna(0).astype(int)
# 年列は2桁西暦（15=2015, 26=2026）のため4桁に変換
df_all['年4'] = df_all['年'].apply(lambda y: 2000 + y if 0 < y < 100 else y)
for col in ['通過順1', '通過順2', '通過順3', '通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

print("\n■ 血統データ読み込み中...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)

# 血統結合（父馬名補完）
blood_slim = df_blood[['血統登録番号', '種牡馬名', '母の父名']].copy()
blood_slim.columns = ['血統登録番号', '父馬名_b', '母の父馬名_b']
df_all = df_all.merge(blood_slim, on='血統登録番号', how='left')
df_all['父馬名']     = df_all['父馬名'].fillna(df_all['父馬名_b'])
df_all['母の父馬名'] = df_all['母の父馬名'].fillna(df_all['母の父馬名_b'])
df_all.drop(['父馬名_b', '母の父馬名_b'], axis=1, inplace=True)
print(f"  父馬名マッチ率: {df_all['父馬名'].notna().mean()*100:.1f}%")

df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None
)

# 血統CSVの馬別lookup dict（条件A CF用）
blood_horse_dict = {}
for _, row in df_blood.iterrows():
    name = str(row.get('馬名', '') or '').strip()
    if not name:
        continue
    total_r = int(row['全成績1着数'] + row['全成績2着数'] +
                  row['全成績3着数'] + row['全成績着外数'])
    total_w = int(row['全成績1着数'])
    blood_horse_dict[name] = (total_r, total_w)
print(f"  血統CSV馬名辞書: {len(blood_horse_dict):,}件")


# ============================================================
# 2. 統計マスター構築（条件A=全期間、条件B=2023以前）
# ============================================================
def build_stats(df_source, label):
    """騎手統計・距離統計・馬別統計を構築"""
    print(f"\n■ 統計マスター構築 [{label}] ({len(df_source):,}件)")

    # 騎手統計 (JT軸)
    jockey_stats = {}
    for jockey, grp in df_source.groupby('騎手名'):
        n = len(grp)
        if n < 50:
            continue
        wins = (grp['確定着順'] == 1).sum()
        jockey_stats[str(jockey)] = {
            'races': int(n),
            'wins': int(wins),
            'win_rate': float(wins / n),
        }
    print(f"  騎手統計: {len(jockey_stats):,}件")

    # 距離別統計 (SPD軸)
    distance_stats = {}
    for dist, grp in df_source.groupby('距離'):
        valid_t = grp['走破時計_sec'].dropna()
        if len(valid_t) < 10:
            continue
        distance_stats[int(dist)] = {
            'n': int(len(grp)),
            'avg_time': float(valid_t.mean()),
            'std_time': float(valid_t.std()) if len(valid_t) > 1 else 0.0,
        }
    print(f"  距離統計: {len(distance_stats):,}件")

    # 馬別キャリア統計 (CF軸・時系列フィルター済み)
    horse_stats = {}
    for horse, grp in df_source.groupby('馬名'):
        n = len(grp)
        wins = (grp['確定着順'] == 1).sum()
        horse_stats[str(horse).strip()] = {
            'races': int(n),
            'wins': int(wins),
            'win_rate': float(wins / n) if n > 0 else 0.0,
        }
    print(f"  馬別統計: {len(horse_stats):,}件")

    return jockey_stats, distance_stats, horse_stats


df_pre2024 = df_all[df_all['年4'] <= 2023].copy()

jockey_A, distance_A, horse_A = build_stats(df_all,     "A: 全期間 2015-2026")
jockey_B, distance_B, horse_B = build_stats(df_pre2024, "B: 2023以前のみ")

print(f"\n  統計期間別レコード数: 全期間={len(df_all):,} / 2023以前={len(df_pre2024):,}")


# ============================================================
# 3. スコア計算関数
# ============================================================
def calc_cf_from_blood(horse_name):
    """条件A: 血統CSV累計成績からCFスコアを計算（未来データ含む）"""
    if horse_name in blood_horse_dict:
        total_r, total_w = blood_horse_dict[horse_name]
        if total_r > 0:
            wr   = total_w / total_r
            conf = min(1.0, total_r / 10)
            cf   = wr * 100 * conf + 50 * (1 - conf)
            cf   = min(100.0, cf)
            pen  = CAREER_PENALTY.get(total_r, 1.0)
            if pen < 1.0 and cf > 50:
                cf = 50 + (cf - 50) * pen
            return cf
    return 20.0  # 未登録または0走


def calc_cf_from_history(horse_name, horse_stats):
    """条件B: 事前レース結果集計からCFスコアを計算（未来データ含まず）"""
    if horse_name in horse_stats:
        hs   = horse_stats[horse_name]
        n    = hs['races']
        wr   = hs['win_rate']
        conf = min(1.0, n / 10)
        cf   = wr * 100 * conf + 50 * (1 - conf)
        cf   = min(100.0, cf)
        pen  = CAREER_PENALTY.get(n, 1.0)
        if pen < 1.0 and cf > 50:
            cf = 50 + (cf - 50) * pen
        return cf
    return 20.0  # 2023以前に出走歴なし


def score_horse(row, jockey_stats, distance_stats, horse_stats, use_horse_stats):
    """
    1頭のスコアを計算。
    use_horse_stats=False → CF に血統CSV累計を使用（条件A）
    use_horse_stats=True  → CF に事前レース結果集計を使用（条件B）
    """
    axes = {}

    # CF: キャリア形成
    horse_name = str(row['馬名']).strip()
    if use_horse_stats:
        axes['CF'] = calc_cf_from_history(horse_name, horse_stats)
    else:
        axes['CF'] = calc_cf_from_blood(horse_name)

    # SI: スピードインデックス（上がり3F）— 実測値・リークなし
    agari = row['上がり3Fタイム_sec']
    axes['SI'] = max(10.0, 100 - (float(agari) - 30) * 2) if pd.notna(agari) else 50.0

    # JT: ジョッキー勝率
    jockey = row.get('騎手名')
    if pd.notna(jockey) and str(jockey) in jockey_stats:
        axes['JT'] = min(100.0, jockey_stats[str(jockey)]['win_rate'] * 100)
    else:
        axes['JT'] = 50.0

    # PD: ペースデザイン（通過順）— 実測値・リークなし
    passages = [row.get(f'通過順{i}') for i in range(1, 5)]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    if passages:
        avg_p = float(np.mean(passages))
        axes['PD'] = max(10.0, 100 - abs(avg_p - 7) * 3)
    else:
        axes['PD'] = 50.0

    # BL: ベース力（人気順）— 実測値・リークなし
    pop = int(row['人気順']) if pd.notna(row.get('人気順')) and int(row['人気順']) > 0 else 0
    axes['BL'] = max(10.0, 100 - pop * 5) if pop > 0 else 50.0

    # SPD: スピード能力（走破時計z-score）
    dist  = int(row['距離']) if pd.notna(row.get('距離')) else 0
    jikan = row['走破時計_sec']
    if dist in distance_stats and pd.notna(jikan):
        ds = distance_stats[dist]
        if ds['std_time'] > 0:
            z = (float(jikan) - ds['avg_time']) / ds['std_time']
            axes['SPD'] = max(10.0, min(100.0, 50 - z * 10))
        else:
            axes['SPD'] = 50.0
    else:
        axes['SPD'] = 50.0

    # MK: マーケット（人気＋オッズ帯補正）— 実測値・リークなし
    odds = float(row.get('単勝オッズ_num') or 0)
    if 1 <= pop <= 5:
        mk = float(100 - pop * 10)
    elif 6 <= pop <= 10:
        mk = float(50 - (pop - 5) * 5)
    else:
        mk = max(10.0, float(30 - (pop - 10)))
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
    wts  = [WEIGHTS.get(k, 1.0) for k in keys]
    return float(np.average(vals, weights=wts))


# ============================================================
# 4. テストレース（2024〜2026 Grade 10頭以上）
# ============================================================
print("\n■ テストレース絞り込み中...")
test_df = df_all[(df_all['年4'] >= 2024) & (df_all['grade'].notna())].copy()
test_df['race_key'] = (
    test_df['年4'].astype(str) + '_' +
    test_df['月'].astype(str).str.zfill(2) + '_' +
    test_df['日'].astype(str).str.zfill(2) + '_' +
    test_df['場所'].astype(str) + '_' +
    test_df['日次'].astype(str) + '_' +
    test_df['レース番号'].astype(str).str.zfill(2)
)
test_df = test_df.drop_duplicates(subset=['race_key', '馬名'])
print(f"  グレード行数: {len(test_df):,}件")

results = []
race_groups = list(test_df.groupby('race_key'))
total_rg    = len(race_groups)
print(f"  ユニークレース数（10頭フィルター前）: {total_rg}R")

for i, (rk, rdf) in enumerate(race_groups):
    if i % 100 == 0:
        print(f"  進捗: {i}/{total_rg}...")

    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 10:  # 10頭以上限定
        continue

    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_1st = str(winner_rows.iloc[0]['馬名']).strip()
    actual_top3 = {str(h).strip() for h in valid[valid['確定着順'] <= 3]['馬名']}

    pop1_rows  = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None

    scores_A, scores_B = {}, {}
    for idx, row in valid.iterrows():
        try:
            scores_A[idx] = score_horse(row, jockey_A, distance_A, horse_A,
                                        use_horse_stats=False)
            scores_B[idx] = score_horse(row, jockey_B, distance_B, horse_B,
                                        use_horse_stats=True)
        except Exception:
            scores_A[idx] = 50.0
            scores_B[idx] = 50.0

    if not scores_A:
        continue

    best_A_idx = max(scores_A, key=scores_A.get)
    best_B_idx = max(scores_B, key=scores_B.get)
    pred_A = str(valid.loc[best_A_idx, '馬名']).strip()
    pred_B = str(valid.loc[best_B_idx, '馬名']).strip()

    odds_A = float(valid.loc[best_A_idx, '単勝オッズ_num'] or 0)
    odds_B = float(valid.loc[best_B_idx, '単勝オッズ_num'] or 0)

    meta  = valid.iloc[0]
    grade = str(meta['grade'])
    year  = int(meta['年4'])

    results.append({
        'race_key':  rk,
        'grade':     grade,
        'year':      year,
        'n_horses':  len(valid),
        'actual_1st': actual_1st,
        'pop1_horse': pop1_horse,
        'pred_A':    pred_A,
        'hit_A':     pred_A == actual_1st,
        'place_A':   pred_A in actual_top3,
        'odds_A':    odds_A,
        'pred_A_same_as_B': pred_A == pred_B,
        'pred_B':    pred_B,
        'hit_B':     pred_B == actual_1st,
        'place_B':   pred_B in actual_top3,
        'odds_B':    odds_B,
        'pop1_hit':  pop1_horse == actual_1st if pop1_horse else False,
    })

print(f"\n■ 予測完了: 有効レース数 {len(results)}R (10頭以上の重賞)")


# ============================================================
# 5. 集計・表示
# ============================================================
df_res  = pd.DataFrame(results)
total_R = len(df_res)


def calc_roi(df_sub, hit_col, odds_col):
    """100円単勝投資の回収率（%）"""
    paid_in  = len(df_sub) * 100
    paid_out = (df_sub[hit_col] * df_sub[odds_col] * 100).sum()
    return float(paid_out / paid_in * 100) if paid_in > 0 else 0.0


hit_A    = int(df_res['hit_A'].sum())
hit_B    = int(df_res['hit_B'].sum())
place_A  = int(df_res['place_A'].sum())
place_B  = int(df_res['place_B'].sum())
pop1_hit = int(df_res['pop1_hit'].sum())
roi_A    = calc_roi(df_res, 'hit_A', 'odds_A')
roi_B    = calc_roi(df_res, 'hit_B', 'odds_B')
same_pred = int(df_res['pred_A_same_as_B'].sum())

print("\n" + "=" * 65)
print("  時系列リーク検証結果")
print("=" * 65)
print(f"  対象期間: 2024〜2026 / 対象レース: {total_R}R")
print(f"  条件A vs B で同一◎選出: {same_pred}R / {total_R}R ({same_pred/total_R*100:.1f}%)")
print()
print(f"  {'指標':<22} {'条件A(全期間)':>13} {'条件B(2023以前)':>15} {'差(A-B)':>9}")
print(f"  {'─' * 62}")
ha_pct  = hit_A   / total_R * 100
hb_pct  = hit_B   / total_R * 100
pa_pct  = place_A / total_R * 100
pb_pct  = place_B / total_R * 100
pop_pct = pop1_hit / total_R * 100
print(f"  {'◎的中率（単勝）':<22} {ha_pct:>11.2f}%  {hb_pct:>13.2f}%  {ha_pct-hb_pct:>+8.2f}%")
print(f"  {'◎複勝率（3着以内）':<22} {pa_pct:>11.2f}%  {pb_pct:>13.2f}%  {pa_pct-pb_pct:>+8.2f}%")
print(f"  {'単勝ROI（100円）':<22} {roi_A:>11.1f}%  {roi_B:>13.1f}%  {roi_A-roi_B:>+8.1f}%")
print(f"  {'1番人気的中率':<22} {pop_pct:>11.2f}%  {'(基準)':>13}  {'—':>9}")

# グレード別
print(f"\n  ─ グレード別 ─")
print(f"  {'グレード':<8} {'R':>5} {'A的中%':>8} {'B的中%':>8} {'差':>7} "
      f"{'A ROI%':>8} {'B ROI%':>8}")
for g in ['G1', 'G2', 'G3']:
    sub = df_res[df_res['grade'] == g]
    n = len(sub)
    if n == 0:
        continue
    hA = sub['hit_A'].sum()
    hB = sub['hit_B'].sum()
    rA = calc_roi(sub, 'hit_A', 'odds_A')
    rB = calc_roi(sub, 'hit_B', 'odds_B')
    diff = (hA - hB) / n * 100
    print(f"  {g:<8} {n:>5} {hA/n*100:>7.1f}% {hB/n*100:>7.1f}% "
          f"{diff:>+6.1f}% {rA:>7.1f}% {rB:>7.1f}%")

# 年別
print(f"\n  ─ 年別 ─")
print(f"  {'年':>5} {'R':>5} {'A的中%':>8} {'B的中%':>8} {'差':>7}")
for yr in sorted(df_res['year'].unique()):
    sub = df_res[df_res['year'] == yr]
    n = len(sub)
    hA = sub['hit_A'].sum()
    hB = sub['hit_B'].sum()
    print(f"  {yr:>5} {n:>5} {hA/n*100:>7.1f}% {hB/n*100:>7.1f}% "
          f"{(hA-hB)/n*100:>+6.1f}%")

# 予測一致度詳細
diff_races = df_res[df_res['pred_A'] != df_res['pred_B']]
print(f"\n  ─ 条件A vs B で◎が異なるレース ({len(diff_races)}R) ─")
if len(diff_races) > 0:
    hit_both     = int((diff_races['hit_A'] & diff_races['hit_B']).sum())
    hit_A_only   = int((diff_races['hit_A'] & ~diff_races['hit_B']).sum())
    hit_B_only   = int((~diff_races['hit_A'] & diff_races['hit_B']).sum())
    hit_neither  = int((~diff_races['hit_A'] & ~diff_races['hit_B']).sum())
    print(f"    両方的中: {hit_both}R / A的中・B外れ: {hit_A_only}R / "
          f"B的中・A外れ: {hit_B_only}R / 両方外れ: {hit_neither}R")
    roi_diff_A = calc_roi(diff_races, 'hit_A', 'odds_A')
    roi_diff_B = calc_roi(diff_races, 'hit_B', 'odds_B')
    print(f"    差異レースのROI: 条件A={roi_diff_A:.1f}% / 条件B={roi_diff_B:.1f}%")

print()
print("  [注意] CF軸の差異:")
print("    条件A: 血統CSV（2026-02-17スナップショット）の累計成績 → 未来データ含む")
print("    条件B: race_resultsの2023以前集計 → 未来データなし")
print("  [注意] JT/SPD軸:")
print("    条件A: 全期間（2015-2026）統計 / 条件B: 2023以前統計のみ")


# ============================================================
# 6. JSON保存
# ============================================================
stats_pre2024_summary = {
    'cutoff_date': '2023-12-31',
    'training_records': int(len(df_pre2024)),
    'jockey_stats_count': len(jockey_B),
    'distance_stats_count': len(distance_B),
    'horse_stats_count': len(horse_B),
    'vs_full_period': {
        'jockey_stats_count_A': len(jockey_A),
        'distance_stats_count_A': len(distance_A),
        'horse_stats_count_A': len(horse_A),
    },
}
pre2024_path = os.path.join(BASE_DIR, 'leaktest_stats_pre2024.json')
with open(pre2024_path, 'w', encoding='utf-8') as f:
    json.dump(stats_pre2024_summary, f, ensure_ascii=False, indent=2)
print(f"  → {pre2024_path}")

result_json = {
    'created': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
    'test_period': '2024-2026',
    'condition_A': '全期間統計（2015-2026）+ 血統CSV CF',
    'condition_B': '2023以前統計のみ（時系列分離）+ race_results CF',
    'n_races': total_R,
    'overall': {
        'hit_rate_A':   round(ha_pct,  2),
        'hit_rate_B':   round(hb_pct,  2),
        'place_rate_A': round(pa_pct,  2),
        'place_rate_B': round(pb_pct,  2),
        'roi_A':        round(roi_A,   1),
        'roi_B':        round(roi_B,   1),
        'pop1_hit_rate': round(pop_pct, 2),
        'diff_hit':     round(ha_pct - hb_pct, 2),
        'diff_place':   round(pa_pct - pb_pct, 2),
        'diff_roi':     round(roi_A  - roi_B,  1),
        'same_pred_pct': round(same_pred / total_R * 100, 1),
    },
    'by_grade': {},
    'by_year':  {},
    'diff_races': {
        'n': len(diff_races),
        'hit_A_only': hit_A_only   if len(diff_races) > 0 else 0,
        'hit_B_only': hit_B_only   if len(diff_races) > 0 else 0,
        'roi_A':      round(roi_diff_A, 1) if len(diff_races) > 0 else 0.0,
        'roi_B':      round(roi_diff_B, 1) if len(diff_races) > 0 else 0.0,
    },
    'notes': [
        'CF軸（キャリア形成）: 条件A=血統CSVスナップショット累計（2026-02-17・未来含む）'
        ' / 条件B=race_resultsの2023以前集計（未来除外）',
        'JT軸（ジョッキー）: 条件A=全期間勝率 / 条件B=2023以前勝率',
        'SPD軸（スピード）: 条件A=全期間距離統計 / 条件B=2023以前距離統計',
        'SI/PD/BL/MK軸: レース結果行の実測値のため両条件で同一（リーク対象外）',
    ],
}
for g in ['G1', 'G2', 'G3']:
    sub = df_res[df_res['grade'] == g]
    n = len(sub)
    if n == 0:
        continue
    result_json['by_grade'][g] = {
        'n': n,
        'hit_rate_A': round(sub['hit_A'].sum() / n * 100, 2),
        'hit_rate_B': round(sub['hit_B'].sum() / n * 100, 2),
        'place_rate_A': round(sub['place_A'].sum() / n * 100, 2),
        'place_rate_B': round(sub['place_B'].sum() / n * 100, 2),
        'roi_A': round(calc_roi(sub, 'hit_A', 'odds_A'), 1),
        'roi_B': round(calc_roi(sub, 'hit_B', 'odds_B'), 1),
    }
for yr in sorted(df_res['year'].unique()):
    sub = df_res[df_res['year'] == yr]
    n = len(sub)
    result_json['by_year'][str(yr)] = {
        'n': n,
        'hit_rate_A': round(sub['hit_A'].sum() / n * 100, 2),
        'hit_rate_B': round(sub['hit_B'].sum() / n * 100, 2),
        'roi_A': round(calc_roi(sub, 'hit_A', 'odds_A'), 1),
        'roi_B': round(calc_roi(sub, 'hit_B', 'odds_B'), 1),
    }

result_path = os.path.join(BASE_DIR, 'leaktest_result.json')
with open(result_path, 'w', encoding='utf-8') as f:
    json.dump(result_json, f, ensure_ascii=False, indent=2)
print(f"  → {result_path}")

print("\n■ 完了")
