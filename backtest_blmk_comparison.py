# -*- coding: utf-8 -*-
"""
backtest_blmk_comparison.py
BL/MK軸 依存度検証: 4パターン比較バックテスト

背景:
  「BL/MK軸が人気の代理変数化しており、エンジンが市場を追認する構造」
  という外部レビュー指摘を受け、BL/MK有無による影響を定量化する。

比較パターン:
  P1（現行）: 全7軸（CF/SI/JT/SPD/PD/BL/MK）
  P2（BL除外）: BLなし（MKは残す）
  P3（MK除外）: MKなし（BLは残す）
  P4（両除外）: BL・MK両方除外

条件:
  期間: 2024〜2026年 Grade（G1/G2/G3） 10頭以上
  統計: 2023以前のみ（時系列分離済み・leaktest条件Bと同一）
  CF軸: race_results 2023以前集計（未来データなし）

集計指標:
  ◎的中率 / ◎複勝率 / 単勝ROI / ◎の平均人気順（市場相関確認）

出力:
  ターミナルに比較表 + backtest_blmk_comparison.json
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

# 4パターンの重み定義（除外軸は辞書から削除）
PATTERNS = {
    'P1_全軸':   {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0, 'BL': 0.3, 'MK': 0.3},
    'P2_BL除外': {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0,             'MK': 0.3},
    'P3_MK除外': {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0, 'BL': 0.3            },
    'P4_両除外': {'CF': 2.0, 'SI': 2.0, 'JT': 2.0, 'SPD': 2.0, 'PD': 1.0                        },
}
PATTERN_NAMES = list(PATTERNS.keys())


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

blood_slim = df_blood[['血統登録番号', '種牡馬名', '母の父名']].copy()
blood_slim.columns = ['血統登録番号', '父馬名_b', '母の父馬名_b']
df_all = df_all.merge(blood_slim, on='血統登録番号', how='left')
df_all['父馬名']     = df_all['父馬名'].fillna(df_all['父馬名_b'])
df_all['母の父馬名'] = df_all['母の父馬名'].fillna(df_all['母の父馬名_b'])
df_all.drop(['父馬名_b', '母の父馬名_b'], axis=1, inplace=True)

df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(x) if pd.notna(x) else None
)


# ============================================================
# 2. 統計マスター構築（2023以前のみ・時系列分離済み）
# ============================================================
print("\n■ 統計マスター構築（2023以前・時系列分離）...")
df_pre2024 = df_all[df_all['年4'] <= 2023].copy()
print(f"  訓練レコード数: {len(df_pre2024):,}件")

jockey_stats = {}
for jockey, grp in df_pre2024.groupby('騎手名'):
    n = len(grp)
    if n < 50:
        continue
    wins = (grp['確定着順'] == 1).sum()
    jockey_stats[str(jockey)] = {'races': int(n), 'wins': int(wins),
                                  'win_rate': float(wins / n)}
print(f"  騎手統計: {len(jockey_stats):,}件")

distance_stats = {}
for dist, grp in df_pre2024.groupby('距離'):
    valid_t = grp['走破時計_sec'].dropna()
    if len(valid_t) < 10:
        continue
    distance_stats[int(dist)] = {
        'n': int(len(grp)),
        'avg_time': float(valid_t.mean()),
        'std_time': float(valid_t.std()) if len(valid_t) > 1 else 0.0,
    }
print(f"  距離統計: {len(distance_stats):,}件")

horse_stats = {}
for horse, grp in df_pre2024.groupby('馬名'):
    n = len(grp)
    wins = (grp['確定着順'] == 1).sum()
    horse_stats[str(horse).strip()] = {
        'races': int(n), 'wins': int(wins),
        'win_rate': float(wins / n) if n > 0 else 0.0,
    }
print(f"  馬別統計: {len(horse_stats):,}件")


# ============================================================
# 3. スコア計算関数（weights を引数で受け取る）
# ============================================================
def calc_cf(horse_name):
    """CF軸: race_results 2023以前集計（時系列分離済み）"""
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
    return 20.0


def score_horse(row, weights):
    """
    7軸スコアを weights で制御して計算する。
    weights に含まれない軸はスコア計算から除外される。
    """
    axes = {}

    if 'CF' in weights:
        horse_name = str(row.get('馬名', '') or '').strip()
        axes['CF'] = calc_cf(horse_name)

    if 'SI' in weights:
        agari = row.get('上がり3Fタイム_sec')
        axes['SI'] = (max(10.0, 100 - (float(agari) - 30) * 2)
                      if pd.notna(agari) else 50.0)

    if 'JT' in weights:
        jockey = row.get('騎手名')
        if pd.notna(jockey) and str(jockey) in jockey_stats:
            axes['JT'] = min(100.0, jockey_stats[str(jockey)]['win_rate'] * 100)
        else:
            axes['JT'] = 50.0

    if 'PD' in weights:
        passages = [row.get(f'通過順{i}') for i in range(1, 5)]
        passages = [float(p) for p in passages if pd.notna(p) and float(p) > 0]
        axes['PD'] = (max(10.0, 100 - abs(float(np.mean(passages)) - 7) * 3)
                      if passages else 50.0)

    if 'BL' in weights:
        pop = int(row.get('人気順', 0) or 0)
        axes['BL'] = max(10.0, 100 - pop * 5) if pop > 0 else 50.0

    if 'SPD' in weights:
        dist  = int(row.get('距離', 0) or 0)
        jikan = row.get('走破時計_sec')
        if dist in distance_stats and pd.notna(jikan):
            ds = distance_stats[dist]
            if ds.get('std_time', 0) > 0:
                z = (float(jikan) - ds['avg_time']) / ds['std_time']
                axes['SPD'] = max(10.0, min(100.0, 50 - z * 10))
            else:
                axes['SPD'] = 50.0
        else:
            axes['SPD'] = 50.0

    if 'MK' in weights:
        pop  = int(row.get('人気順', 0) or 0)
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
    wts  = [weights[k] for k in keys]
    return float(np.average(vals, weights=wts))


# ============================================================
# 4. テストレース絞り込み（2024〜2026 Grade 10頭以上）
# ============================================================
print("\n■ テストレース絞り込み中（2024〜2026 Grade 10頭以上）...")
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

race_groups = list(test_df.groupby('race_key'))
print(f"  ユニークレース数（フィルター前）: {len(race_groups)}R")


# ============================================================
# 5. バックテスト実行（4パターン同時）
# ============================================================
print("■ バックテスト実行中（4パターン）...")
results = []
total_rg = len(race_groups)

for i, (rk, rdf) in enumerate(race_groups):
    if i % 100 == 0:
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

    meta  = valid.iloc[0]
    grade = str(meta['grade'])
    year  = int(meta['年4'])

    # 4パターン分のスコアを計算
    pattern_results = {}
    for pat, weights in PATTERNS.items():
        scores = {}
        for idx, row in valid.iterrows():
            try:
                scores[idx] = score_horse(row, weights)
            except Exception:
                scores[idx] = 50.0

        if not scores:
            continue

        best_idx  = max(scores, key=scores.get)
        pred_name = str(valid.loc[best_idx, '馬名']).strip()
        pred_odds = float(valid.loc[best_idx, '単勝オッズ_num'] or 0)
        pred_pop  = int(valid.loc[best_idx, '人気順'] or 0)

        pattern_results[pat] = {
            'pred':    pred_name,
            'hit':     pred_name == actual_1st,
            'place':   pred_name in actual_top3,
            'odds':    pred_odds,
            'pop':     pred_pop,
        }

    rec = {
        'race_key':   rk,
        'grade':      grade,
        'year':       year,
        'n_horses':   len(valid),
        'actual_1st': actual_1st,
        'pop1_horse': pop1_horse,
        'pop1_hit':   pop1_horse == actual_1st if pop1_horse else False,
    }
    for pat, pr in pattern_results.items():
        rec[f'{pat}_pred']  = pr['pred']
        rec[f'{pat}_hit']   = pr['hit']
        rec[f'{pat}_place'] = pr['place']
        rec[f'{pat}_odds']  = pr['odds']
        rec[f'{pat}_pop']   = pr['pop']
    results.append(rec)

print(f"  完了: 有効レース数 {len(results)}R (10頭以上)")


# ============================================================
# 6. 集計
# ============================================================
df_res  = pd.DataFrame(results)
total_R = len(df_res)
pop1_hit_rate = df_res['pop1_hit'].mean() * 100


def calc_roi(df_sub, hit_col, odds_col):
    paid_in  = len(df_sub) * 100
    paid_out = (df_sub[hit_col] * df_sub[odds_col] * 100).sum()
    return float(paid_out / paid_in * 100) if paid_in > 0 else 0.0


def summarize_pattern(df_sub, pat):
    n = len(df_sub)
    if n == 0:
        return {'n': 0, 'hit_rate': 0, 'place_rate': 0, 'roi': 0, 'avg_pop': 0}
    return {
        'n':          n,
        'hit_rate':   round(df_sub[f'{pat}_hit'].mean()   * 100, 2),
        'place_rate': round(df_sub[f'{pat}_place'].mean() * 100, 2),
        'roi':        round(calc_roi(df_sub, f'{pat}_hit', f'{pat}_odds'), 1),
        'avg_pop':    round(df_sub[f'{pat}_pop'].mean(), 2),
    }


# 全体サマリー
summary = {pat: summarize_pattern(df_res, pat) for pat in PATTERN_NAMES}

# グレード別
by_grade = {}
for g in ['G1', 'G2', 'G3']:
    sub = df_res[df_res['grade'] == g]
    by_grade[g] = {pat: summarize_pattern(sub, pat) for pat in PATTERN_NAMES}

# 年別
by_year = {}
for yr in sorted(df_res['year'].unique()):
    sub = df_res[df_res['year'] == yr]
    by_year[str(yr)] = {pat: summarize_pattern(sub, pat) for pat in PATTERN_NAMES}


# ============================================================
# 7. 表示
# ============================================================
print("\n" + "=" * 78)
print("  BL/MK軸 依存度検証（backtest_blmk_comparison.py）")
print("=" * 78)
print(f"  対象: 2024〜2026年 Grade（G1/G2/G3） 10頭以上 / {total_R}R")
print(f"  統計: 2023以前のみ（時系列分離済み・leaktest条件Bと同一）")
print(f"  1番人気的中率: {pop1_hit_rate:.2f}%（基準）")
print()

hdr = f"  {'指標':<16}"
for pat in PATTERN_NAMES:
    short = pat.replace('_', ' ')
    hdr += f"  {short:>14}"
print(hdr)
print("  " + "─" * (16 + 16 * len(PATTERN_NAMES)))

metrics = [
    ('◎的中率',    'hit_rate',   '%'),
    ('◎複勝率',    'place_rate', '%'),
    ('単勝ROI',    'roi',        '%'),
    ('◎平均人気順', 'avg_pop',    '位'),
]
for label, key, unit in metrics:
    row_str = f"  {label:<16}"
    for pat in PATTERN_NAMES:
        val = summary[pat][key]
        row_str += f"  {val:>12.2f}{unit}"
    print(row_str)

# BL/MK除外による変化量（P1基準）
print()
print(f"  ─ P1（現行）との差 ─")
base_pat = 'P1_全軸'
for label, key, unit in metrics:
    row_str = f"  {label:<16}"
    for pat in PATTERN_NAMES:
        diff = summary[pat][key] - summary[base_pat][key]
        if pat == base_pat:
            row_str += f"  {'（基準）':>13}"
        else:
            row_str += f"  {diff:>+12.2f}{unit}"
    print(row_str)

# グレード別
print(f"\n  ─ グレード別 単勝ROI ─")
g_hdr = f"  {'G':<6}"
for pat in PATTERN_NAMES:
    short = pat.replace('_', ' ')
    g_hdr += f"  {short:>14}"
print(g_hdr)
for g in ['G1', 'G2', 'G3']:
    row_str = f"  {g:<6}"
    for pat in PATTERN_NAMES:
        v = by_grade[g][pat]
        row_str += f"  {v['roi']:>12.1f}%  " if v['n'] > 0 else f"  {'—':>14}"
    print(row_str)

# 年別 ◎的中率
print(f"\n  ─ 年別 ◎的中率 ─")
y_hdr = f"  {'年':>5}"
for pat in PATTERN_NAMES:
    short = pat.replace('_', ' ')
    y_hdr += f"  {short:>14}"
print(y_hdr)
for yr in sorted(by_year.keys()):
    row_str = f"  {yr:>5}"
    for pat in PATTERN_NAMES:
        v = by_year[yr][pat]
        row_str += f"  {v['hit_rate']:>12.1f}%  " if v['n'] > 0 else f"  {'—':>14}"
    print(row_str)

# 判断基準との照合
p1 = summary['P1_全軸']
p4 = summary['P4_両除外']
print()
print("  ─ 判断基準との照合 ─")
roi_diff = p4['roi'] - p1['roi']
pop_diff = p4['avg_pop'] - p1['avg_pop']
if roi_diff > 0:
    print(f"  ROI: BL/MK除外で{roi_diff:+.1f}% → 市場追認バイアスあり・除外を検討")
elif roi_diff < 0:
    print(f"  ROI: BL/MK除外で{roi_diff:+.1f}% → 市場情報が有効に機能・現行維持")
else:
    print(f"  ROI: BL/MK除外で変化なし → 両方向の効果が相殺")
if pop_diff > 0:
    print(f"  ◎平均人気: 除外で{pop_diff:+.2f}位 → 穴馬寄り・高人気依存が減少（逆張り強化）")
elif pop_diff < 0:
    print(f"  ◎平均人気: 除外で{pop_diff:+.2f}位 → 本命寄り・高人気依存が増加")
else:
    print(f"  ◎平均人気: 変化なし")
print()


# ============================================================
# 8. JSON保存
# ============================================================
output = {
    'created':      pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
    'test_period':  '2024-2026',
    'n_races':      total_R,
    'stats_used':   '2023以前（時系列分離・leaktest条件Bと同一）',
    'pop1_hit_rate': round(pop1_hit_rate, 2),
    'patterns': {
        'P1_全軸':   '全7軸（CF/SI/JT/SPD/PD/BL/MK）',
        'P2_BL除外': 'BLなし（CF/SI/JT/SPD/PD/MK）',
        'P3_MK除外': 'MKなし（CF/SI/JT/SPD/PD/BL）',
        'P4_両除外': 'BL・MK除外（CF/SI/JT/SPD/PD）',
    },
    'overall':   {pat: summary[pat] for pat in PATTERN_NAMES},
    'by_grade':  {g: {pat: by_grade[g][pat] for pat in PATTERN_NAMES}
                  for g in ['G1', 'G2', 'G3']},
    'by_year':   {yr: {pat: by_year[yr][pat] for pat in PATTERN_NAMES}
                  for yr in sorted(by_year.keys())},
    'judgment': {
        'roi_p4_vs_p1': round(roi_diff, 1),
        'avg_pop_p4_vs_p1': round(pop_diff, 2),
    },
}

out_path = os.path.join(BASE_DIR, 'backtest_blmk_comparison.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"  → {out_path}")
print("■ 完了")
