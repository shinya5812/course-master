# -*- coding: utf-8 -*-
"""
hypothesis_a_test.py  -  仮説A検証: 同コース・同距離実績の予測力

【検証内容】
  Step1: 各馬の同コース×同距離での過去成績集計（10走以上の馬対象）
  Step2: 重賞訓練データ（2015〜2023）で予測力を検証
  Step3: 重賞検証データ（2024〜2026）で現行エンジン◎と比較
  Step4: 結論（採用基準: 現行比+2%以上）

【使い方】
  python3 hypothesis_a_test.py
"""

import sys
import io
import os
import re
import sqlite3
import pandas as pd
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')
CSV_FILES = [
    os.path.join(BASE_DIR, 'data', 'race', '2015_2016結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2017_2018結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2019_2020結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2021_2023結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2024_2026結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '2026結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '202602280331結果.csv'),
    os.path.join(BASE_DIR, 'data', 'race', '結果202603070405.csv'),
]

GRADE_PATTERN = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')
SEP  = '=' * 64
SEP2 = '─' * 64

# ──────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────
def detect_grade(race_name):
    if not race_name:
        return None
    m = GRADE_PATTERN.search(str(race_name))
    if not m:
        return None
    g = m.group()
    if   g[-1] in ('Ⅰ', '1', '１'): return 'G1'
    elif g[-1] in ('Ⅱ', '2', '２'): return 'G2'
    elif g[-1] in ('Ⅲ', '3', '３'): return 'G3'
    return None

def venue_code(venue_str):
    """場所文字列を正規化（スペース除去）"""
    return str(venue_str).strip()

# ──────────────────────────────────────────
# 1. CSV読み込み（全期間）
# ──────────────────────────────────────────
print("■ CSV読み込み中...")
dfs = []
for fp in CSV_FILES:
    if os.path.exists(fp):
        dfs.append(pd.read_csv(fp, encoding='cp932', low_memory=False))
        print(f"  {os.path.basename(fp)}: {len(dfs[-1]):,}件")

df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}件")

# 数値変換
for col in ['確定着順', '人気順', '距離']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce').fillna(0).astype(int)
df_all['単勝オッズ_num'] = pd.to_numeric(df_all['単勝オッズ'], errors='coerce').fillna(0.0)
df_all['場所'] = df_all['場所'].astype(str).str.strip()

# 年カラムは西暦下2桁（例: 15=2015, 26=2026）→ 4桁に変換
df_all['year_int'] = df_all['年'].astype(int) + 2000

# レースキー
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

# 重賞のみ
grade_df = df_all[df_all['grade'].notna()].copy()
grade_df = grade_df.drop_duplicates(subset=['race_key', '馬名'])
print(f"  重賞レコード: {len(grade_df):,}件  "
      f"G1:{(grade_df['grade']=='G1').sum():,}  "
      f"G2:{(grade_df['grade']=='G2').sum():,}  "
      f"G3:{(grade_df['grade']=='G3').sum():,}")

# ──────────────────────────────────────────
# 2. race_results から同コース×同距離実績を集計（訓練期間のみ）
#    訓練期間: 〜2023年 / 検証期間: 2024〜2026
#    ※ データリーク防止のため実績辞書は訓練期間のレースのみで構築
# ──────────────────────────────────────────
print("\n■ race_results から同コース×同距離実績を集計中（訓練期間: 〜2023年）...")
con = sqlite3.connect(DB_PATH)

# 訓練期間（2015〜2023年）のみで実績を集計
q = """
SELECT
    horse_name,
    venue,
    distance,
    COUNT(*)                                         AS runs,
    SUM(CASE WHEN finish_pos = 1 THEN 1 ELSE 0 END)   AS wins,
    SUM(CASE WHEN finish_pos <= 3 THEN 1 ELSE 0 END)   AS places
FROM race_results
WHERE finish_pos > 0
  AND race_date < '2024-01-01'
GROUP BY horse_name, venue, distance
"""
df_course_stats = pd.read_sql_query(q, con)

# 全期間版（Step1の基礎集計用）
q_all = """
SELECT
    horse_name,
    venue,
    distance,
    COUNT(*)                                         AS runs,
    SUM(CASE WHEN finish_pos = 1 THEN 1 ELSE 0 END)   AS wins,
    SUM(CASE WHEN finish_pos <= 3 THEN 1 ELSE 0 END)   AS places
FROM race_results
WHERE finish_pos > 0
GROUP BY horse_name, venue, distance
"""
df_course_stats_all = pd.read_sql_query(q_all, con)
con.close()

print(f"  訓練期間集計: {len(df_course_stats):,}レコード（〜2023年）")
print(f"  全期間集計  : {len(df_course_stats_all):,}レコード（Step1用）")

# ──────────────────────────────────────────
# Step 1: 基礎集計（10走以上の馬）
# ──────────────────────────────────────────
print()
print(SEP)
print("  【Step 1】基礎集計（同コース×同距離・10走以上の馬）")
print(SEP)

df_10plus = df_course_stats_all[df_course_stats_all['runs'] >= 10].copy()
df_10plus['win_rate']   = df_10plus['wins']   / df_10plus['runs']
df_10plus['place_rate'] = df_10plus['places'] / df_10plus['runs']

print(f"\n  同コース×同距離 10走以上の集計レコード数: {len(df_10plus):,}")
print(f"  対象ユニーク馬数                        : {df_10plus['horse_name'].nunique():,}")
print(f"  対象ユニークコース数（venue×distance）  : {df_course_stats_all[['venue','distance']].drop_duplicates().shape[0]:,}")

# 勝率・複勝率の分布
print(f"\n  【勝率分布（10走以上）】")
wr_bins = [0, 0.05, 0.10, 0.20, 0.30, 1.01]
wr_labels = ['0〜5%', '5〜10%', '10〜20%', '20〜30%', '30%超']
df_10plus['wr_band'] = pd.cut(df_10plus['win_rate'], bins=wr_bins, labels=wr_labels, right=False)
wr_dist = df_10plus['wr_band'].value_counts().sort_index()
for band, cnt in wr_dist.items():
    bar = '■' * (cnt * 30 // len(df_10plus))
    print(f"    {band:<8}: {cnt:>5}件  {bar}")

# 走数別分布
print(f"\n  【走数帯別レコード数（上位5帯）】")
runs_bins = [10, 20, 30, 50, 100, 9999]
runs_labels = ['10〜19走', '20〜29走', '30〜49走', '50〜99走', '100走以上']
df_10plus['runs_band'] = pd.cut(df_10plus['runs'], bins=runs_bins, labels=runs_labels, right=False)
for band, cnt in df_10plus['runs_band'].value_counts().sort_index().items():
    print(f"    {band}: {cnt:,}件")

# ──────────────────────────────────────────
# Step 2: 予測力検証（訓練データ: 2015〜2023）
# ──────────────────────────────────────────
print()
print(SEP)
print("  【Step 2】予測力検証（訓練データ: 2015〜2023）")
print(SEP)

# 訓練期間の重賞レースを抽出
train_df = grade_df[grade_df['year_int'] <= 2023].copy()
train_races = train_df.groupby('race_key')

# 同コース×同距離実績を辞書化（高速参照用）
# key: (horse_name, venue, distance) → {runs, wins, places}
stats_dict = {}
for _, row in df_course_stats.iterrows():
    k = (str(row['horse_name']).strip(),
         str(row['venue']).strip(),
         int(row['distance']))
    stats_dict[k] = {
        'runs':   int(row['runs']),
        'wins':   int(row['wins']),
        'places': int(row['places']),
    }

print(f"\n  訓練データ重賞レース数: {train_races.ngroups:,}R")

# 各レースで各馬に同コース×同距離実績フラグを付与し、
# 「勝利経験あり / 複勝経験あり / 経験なし」のカテゴリ別に
# 実際の1着率を集計
cat_wins   = defaultdict(int)  # カテゴリ → 実際に1着になった数
cat_total  = defaultdict(int)  # カテゴリ → 出走頭数

# また各レースで「同コース実績が最も高い馬」を◎にした場合の的中率も算出
pred_hit   = 0  # 同コース◎が1着
pred_total = 0  # レース数（有効）
pop1_hit   = 0  # 1番人気が1着
pop1_total = 0

for race_key, rdf in train_races:
    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3:
        continue

    venue    = str(valid.iloc[0]['場所']).strip()
    distance = int(valid.iloc[0]['距離'])

    # 1着馬・1番人気馬
    winner_rows  = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_winner = str(winner_rows.iloc[0]['馬名']).strip()
    pop1_rows = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None

    # 1番人気的中カウント
    pop1_total += 1
    if pop1_horse and pop1_horse == actual_winner:
        pop1_hit += 1

    # 各馬の同コース実績を取得して分類
    best_horse = None
    best_wr    = -1.0

    for _, row in valid.iterrows():
        horse = str(row['馬名']).strip()
        k = (horse, venue, distance)
        s = stats_dict.get(k, {'runs': 0, 'wins': 0, 'places': 0})
        runs, wins, places = s['runs'], s['wins'], s['places']

        # カテゴリ判定
        if wins > 0:
            cat = 'win_exp'      # 勝利経験あり
        elif places > 0:
            cat = 'place_exp'    # 複勝経験あり
        elif runs > 0:
            cat = 'exp_only'     # 出走経験あり（掲示板外）
        else:
            cat = 'no_exp'       # 経験なし

        cat_total[cat] += 1
        if horse == actual_winner:
            cat_wins[cat] += 1

        # 同コース◎: 最も勝率が高い馬（1走以上の実績あり）
        wr = wins / runs if runs > 0 else 0.0
        if wr > best_wr:
            best_wr    = wr
            best_horse = horse

    # 同コース◎的中判定
    if best_horse is not None and best_wr > 0:
        pred_total += 1
        if best_horse == actual_winner:
            pred_hit += 1

# カテゴリ別の実際の勝率
cats_order = [
    ('win_exp',   '同コース・同距離 勝利経験あり'),
    ('place_exp', '同コース・同距離 複勝経験あり（勝なし）'),
    ('exp_only',  '同コース・同距離 出走経験あり（複勝なし）'),
    ('no_exp',    '同コース・同距離 経験なし'),
]

print(f"\n  {'カテゴリ':<36}  {'出走数':>6}  {'1着数':>5}  {'実際の勝率':>9}  比較")
print(f"  {SEP2}")
pop1_wr = pop1_hit / pop1_total * 100 if pop1_total > 0 else 0.0
for cat_key, cat_label in cats_order:
    total = cat_total[cat_key]
    wins_ = cat_wins[cat_key]
    wr    = wins_ / total * 100 if total > 0 else 0.0
    diff  = wr - pop1_wr
    flag  = '↑' if diff >= 3 else ('↓' if diff <= -3 else '→')
    print(f"  {cat_label:<36}  {total:>6,}  {wins_:>5,}  {wr:>8.2f}%  {flag}（vs 1人気 {pop1_wr:.1f}%）")

print(f"  {SEP2}")
print(f"  1番人気の実際の勝率（基準値）             {pop1_total:>6,}  {pop1_hit:>5,}  {pop1_wr:>8.2f}%")

# 同コース◎の的中率
pred_wr = pred_hit / pred_total * 100 if pred_total > 0 else 0.0
print(f"\n  【同コース◎（最高勝率馬）の的中率】")
print(f"  対象: {pred_total:,}R（実績ゼロのレースは除外）")
print(f"  的中: {pred_hit:,}R  /  的中率: {pred_wr:.2f}%  （1番人気基準: {pop1_wr:.2f}%  差: {pred_wr-pop1_wr:+.2f}%）")

# ──────────────────────────────────────────
# Step 3: 現行エンジンとの比較（検証データ: 2024〜2026）
# ──────────────────────────────────────────
print()
print(SEP)
print("  【Step 3】検証データ（2024〜2026）での現行エンジン比較")
print(SEP)

test_df    = grade_df[grade_df['year_int'] >= 2024].copy()
test_races = test_df.groupby('race_key')
test_total = test_races.ngroups

print(f"\n  検証対象重賞レース数: {test_total:,}R（2024〜2026）")

test_pred_hit  = 0  # 同コース◎的中
test_pop1_hit  = 0  # 1番人気的中
test_pred_valid = 0  # 有効レース（実績データあり）

# 各テストレースで同コース最高勝率馬を予測
for race_key, rdf in test_races:
    valid = rdf[rdf['確定着順'] > 0].copy()
    if len(valid) < 3:
        continue

    venue    = str(valid.iloc[0]['場所']).strip()
    distance = int(valid.iloc[0]['距離'])

    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_winner = str(winner_rows.iloc[0]['馬名']).strip()

    pop1_rows = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None
    if pop1_horse == actual_winner:
        test_pop1_hit += 1

    best_horse = None
    best_wr    = -1.0
    for _, row in valid.iterrows():
        horse = str(row['馬名']).strip()
        k = (horse, venue, distance)
        s = stats_dict.get(k, {'runs': 0, 'wins': 0, 'places': 0})
        runs_, wins_ = s['runs'], s['wins']
        wr = wins_ / runs_ if runs_ > 0 else 0.0
        if wr > best_wr:
            best_wr    = wr
            best_horse = horse

    if best_horse is not None and best_wr > 0:
        test_pred_valid += 1
        if best_horse == actual_winner:
            test_pred_hit += 1

test_pop1_wr  = test_pop1_hit  / test_total     * 100 if test_total > 0 else 0.0
test_pred_wr  = test_pred_hit  / test_pred_valid * 100 if test_pred_valid > 0 else 0.0
ENGINE_HIT    = 35.3  # 現行7軸エンジンの検証データ的中率

print(f"\n  {'手法':<40}  {'有効R':>6}  {'的中率':>8}  {'1人気比':>8}  エンジン比")
print(f"  {SEP2}")
print(f"  {'現行7軸エンジン◎':<40}  {'—':>6}  {ENGINE_HIT:>7.1f}%  "
      f"{ENGINE_HIT - test_pop1_wr:>+7.1f}%  {'（基準）':>10}")
print(f"  {'同コース・同距離 最高勝率馬◎':<40}  {test_pred_valid:>6,}  "
      f"{test_pred_wr:>7.1f}%  {test_pred_wr - test_pop1_wr:>+7.1f}%  "
      f"{test_pred_wr - ENGINE_HIT:>+7.1f}%")
print(f"  {'1番人気（比較基準）':<40}  {test_total:>6,}  "
      f"{test_pop1_wr:>7.1f}%  {'(基準)':>8}")

# 実績ゼロレース（同コース経験馬ゼロ）の割合
no_exp_R = test_total - test_pred_valid
print(f"\n  ※ 同コース実績ゼロで予測不能なレース: {no_exp_R}R / {test_total}R "
      f"（{no_exp_R/test_total*100:.1f}%）")

# ──────────────────────────────────────────
# Step 4: 結論
# ──────────────────────────────────────────
print()
print(SEP)
print("  【Step 4】結論")
print(SEP)

diff_vs_engine = test_pred_wr - ENGINE_HIT
adopt_threshold = 2.0  # 採用基準: +2%以上

print(f"""
  ┌───────────────────────────────────────────────────────────┐
  │  仮説A「同コース・同距離実績」の予測力判定               │
  └───────────────────────────────────────────────────────────┘

  【検証データ（2024〜2026重賞）結果】
  ─────────────────────────────────────
  同コース◎の的中率       : {test_pred_wr:.1f}%
  現行エンジン◎の的中率   : {ENGINE_HIT:.1f}%  （採用基準）
  差（同コース − エンジン）: {diff_vs_engine:+.1f}%

  採用基準（+{adopt_threshold:.0f}%以上）: {'【採用推奨】' if diff_vs_engine >= adopt_threshold else '【採用しない】'}
""")

if diff_vs_engine >= adopt_threshold:
    print("  ■ 判定: 有効")
    print("    同コース・同距離実績は現行エンジンより予測力が高い。")
    print("    新軸（TR軸再設計）として採用を推奨。")
else:
    print("  ■ 判定: 予測力として単独では不十分")
    print()
    print("  【原因分析】")
    # 勝利経験ありの実際の勝率
    wr_win   = cat_wins['win_exp'] / cat_total['win_exp'] * 100 if cat_total['win_exp'] > 0 else 0
    wr_place = cat_wins['place_exp'] / cat_total['place_exp'] * 100 if cat_total['place_exp'] > 0 else 0
    wr_noexp = cat_wins['no_exp'] / cat_total['no_exp'] * 100 if cat_total['no_exp'] > 0 else 0

    print(f"    a) 「勝利経験あり」の実際の勝率: {wr_win:.2f}%  "
          f"（1人気基準 {pop1_wr:.1f}% との差: {wr_win-pop1_wr:+.2f}%）")
    print(f"    b) 「複勝経験あり」の実際の勝率: {wr_place:.2f}%")
    print(f"    c) 「経験なし」の実際の勝率    : {wr_noexp:.2f}%")
    print()
    if wr_win > pop1_wr:
        print("    → 勝利経験は個別傾向として有効。")
        print("      ただし「最高勝率馬=次も勝つ」は過去の累積に依存しすぎる。")
        print("      （強い馬が特定コースに繰り返し出走するため自己相関が発生）")
    else:
        print("    → 同コース実績の高い馬が次レースで勝つ相関が弱い。")
        print("      重賞は毎回出走馬のレベルが変動するため固定実績が効きにくい。")
    print()
    print("  【代替案】")
    print("    1) 同コース実績を「勝利経験あり/なし」の2値フラグとして補助的に使用")
    print("    2) 同コース実績 × 直近3走以内に限定（古い実績を除外）")
    print("    3) 同コース実績を別軸（TR軸）ではなく、既存CF軸の補正係数として組込み")

print()
print(SEP)
print("  検証完了")
print(SEP)
print()
