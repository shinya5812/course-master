# -*- coding: utf-8 -*-
"""
COURSE MASTER v7.3 重賞バックテスト
検証1: 重賞◎的中率（全体・グレード別・会場別・距離帯別・芝ダ別）
検証2: 1番人気ベースラインとの比較
検証3: 9軸の寄与度分析（各軸スコアと着順の相関）
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 設定
# ============================================================
PKL_PATH    = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_FILE  = os.path.join(BASE_DIR, '20260217血統.csv')
CSV_FILES   = [
    os.path.join(BASE_DIR, '2015_2016結果.csv'),
    os.path.join(BASE_DIR, '2017_2018結果.csv'),
    os.path.join(BASE_DIR, '2019_2020結果.csv'),
    os.path.join(BASE_DIR, '2021_2023結果.csv'),
    os.path.join(BASE_DIR, '2024_2026結果.csv'),
    os.path.join(BASE_DIR, '2026結果.csv'),
    os.path.join(BASE_DIR, '202602280331結果.csv'),
]

# grade検出パターン（全角・半角・ローマ数字対応）
GRADE_PATTERN = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')

def detect_grade(race_name):
    """レース名からグレードを検出 → 'G1'/'G2'/'G3'/None"""
    if not race_name:
        return None
    m = GRADE_PATTERN.search(race_name)
    if not m:
        return None
    g = m.group()
    if g[-1] in ('Ⅰ','1','１'):
        return 'G1'
    elif g[-1] in ('Ⅱ','2','２'):
        return 'G2'
    elif g[-1] in ('Ⅲ','3','３'):
        return 'G3'
    return None

def dist_band(d):
    """距離帯ラベル"""
    if d <= 1400:
        return '〜1400m'
    elif d <= 2000:
        return '1600〜2000m'
    else:
        return '2200m〜'

# ============================================================
# 1. pkl読み込み
# ============================================================
print("■ pkl読み込み中...")
with open(PKL_PATH, 'rb') as f:
    state = pickle.load(f)

# エンジンを軽量なNamespaceとして再現（クラスをインポートせずに辞書から直接利用）
sire_stats       = state.get('sire_stats', {})
dam_sire_stats   = state.get('dam_sire_stats', {})
jockey_stats     = state.get('jockey_stats', {})
distance_stats   = state.get('distance_stats', {})
sire_dist_stats  = state.get('sire_dist_stats', {})
bms_dist_stats   = state.get('bms_dist_stats', {})
career_penalty   = {1:0.70, 2:0.70, 3:0.70, 4:0.85, 5:0.85}
odds_mk_table    = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]

print(f"  sire_stats: {len(sire_stats)}件")
print(f"  jockey_stats: {len(jockey_stats)}件")
print(f"  sire_dist_stats: {len(sire_dist_stats)}件")

# ============================================================
# 2. CSV読み込み・前処理
# ============================================================
print("\n■ CSV読み込み中...")
dfs = []
for f in CSV_FILES:
    if os.path.exists(f):
        df = pd.read_csv(f, encoding='cp932', low_memory=False)
        dfs.append(df)
        print(f"  {os.path.basename(f)}: {len(df)}件")

df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all)}件")

# 数値化
df_all['確定着順']       = pd.to_numeric(df_all['確定着順'], errors='coerce').fillna(0).astype(int)
df_all['人気順']         = pd.to_numeric(df_all['人気順'], errors='coerce').fillna(0).astype(int)
df_all['走破時計_sec']   = pd.to_numeric(df_all['走破時計'], errors='coerce')
df_all['単勝オッズ_num'] = pd.to_numeric(df_all['単勝オッズ'], errors='coerce').fillna(0)
df_all['斤量_num']       = pd.to_numeric(df_all['斤量'], errors='coerce')
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
df_all['距離']           = pd.to_numeric(df_all['距離'], errors='coerce').fillna(0).astype(int)
df_all['年齢']           = pd.to_numeric(df_all['年齢'], errors='coerce').fillna(4)
for col in ['通過順1','通過順2','通過順3','通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# 血統データ読み込み・結合（父馬名・母の父馬名補完）
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
print(f"  父馬名マッチ率: {df_all['父馬名'].notna().mean()*100:.1f}%")

# 重賞グレード列を追加
df_all['grade'] = df_all['レース名'].apply(
    lambda x: detect_grade(str(x)) if pd.notna(x) else None
)
grade_df = df_all[df_all['grade'].notna()].copy()
print(f"\n■ 重賞レコード数: {len(grade_df)}件")
print(f"  G1: {(grade_df['grade']=='G1').sum()}件")
print(f"  G2: {(grade_df['grade']=='G2').sum()}件")
print(f"  G3: {(grade_df['grade']=='G3').sum()}件")

# ============================================================
# 3. スコア計算関数（エンジン相当・軸スコアも返す）
# ============================================================
def score_horse_full(row):
    """1頭の9軸スコアを計算。{軸名: スコア} と最終スコアを返す"""
    axes = {}

    # CF: キャリア形成
    horse_name = str(row['馬名']).strip()
    bi = df_blood[df_blood['馬名'] == horse_name]
    if not bi.empty:
        total_races = int(bi['全成績1着数'].iloc[0] + bi['全成績2着数'].iloc[0] +
                          bi['全成績3着数'].iloc[0] + bi['全成績着外数'].iloc[0])
        total_wins = int(bi['全成績1着数'].iloc[0])
        if total_races > 0:
            raw_wr = total_wins / total_races
            conf = min(1.0, total_races / 10)
            cf = raw_wr * 100 * conf + 50 * (1 - conf)
            cf = min(100, cf)
            penalty = career_penalty.get(total_races, 1.0)
            if penalty < 1.0 and cf > 50:
                cf = 50 + (cf - 50) * penalty
        else:
            cf = 20
    else:
        cf = 20
    axes['CF'] = cf

    # BF: 血統適性 ← [Phase 3 Step 5] 除外（相関係数+0.020・逆効果）
    # axes['BF'] は設定しない

    # SI: スピードインデックス（上がり3F）
    agari = row['上がり3Fタイム_sec']
    axes['SI'] = max(10, 100 - (agari - 30) * 2) if pd.notna(agari) else 50

    # JT: ジョッキー
    jockey = row['騎手名']
    if pd.notna(jockey) and jockey in jockey_stats:
        axes['JT'] = min(100, jockey_stats[jockey]['win_rate'] * 100)
    else:
        axes['JT'] = 50

    # PD: ペースデザイン（通過順）
    passages = [row.get('通過順1'), row.get('通過順2'),
                row.get('通過順3'), row.get('通過順4')]
    passages = [p for p in passages if pd.notna(p) and p > 0]
    if passages:
        avg_p = np.mean(passages)
        axes['PD'] = max(10, 100 - abs(avg_p - 7) * 3)
    else:
        axes['PD'] = 50

    # BL: ベース力（人気順）
    pop = int(row['人気順']) if pd.notna(row['人気順']) else 0
    axes['BL'] = max(10, 100 - pop * 5) if pop > 0 else 50

    # HP: ハンディキャップ適応 ← [Phase 3 Step 5] 除外（相関係数-0.030・ほぼ無効）
    # axes['HP'] は設定しない

    # SPD: スピード能力（走破時計z-score）
    dist  = int(row['距離']) if pd.notna(row.get('距離')) else 0
    jikan = row['走破時計_sec']
    if dist in distance_stats and pd.notna(jikan):
        ds_stat = distance_stats[dist]
        if ds_stat['std_time'] > 0:
            z = (float(jikan) - ds_stat['avg_time']) / ds_stat['std_time']
            axes['SPD'] = max(10, min(100, 50 - z * 10))
        else:
            axes['SPD'] = 50
    else:
        axes['SPD'] = 50

    # MK: マーケット（人気順+オッズ帯補正）
    odds = float(row['単勝オッズ_num']) if pd.notna(row.get('単勝オッズ_num')) else 0.0
    if 1 <= pop <= 5:
        mk = 100 - pop * 10
    elif 6 <= pop <= 10:
        mk = 50 - (pop - 5) * 5
    else:
        mk = max(10, 30 - (pop - 10))
    # チームI（Upsetモード）で人気外を加点（合議の代わりに単一チームI相当）
    # バックテストでは4チーム平均の代わりにIチームで代表させる
    if pop > 5:
        mk += (pop - 5) * 2
    if odds > 0:
        for lo, hi, mult in odds_mk_table:
            if lo < odds <= hi:
                if mult != 1.0:
                    mk = 50 + (mk - 50) * mult
                break
    axes['MK'] = mk

    # 重み付き平均（Phase 3 Step 5: 7軸）
    WEIGHTS = {'CF':2.0,'SI':2.0,'SPD':2.0,'JT':2.0,
               'PD':1.0,'BL':0.3,'MK':0.3}
    keys = list(axes.keys())
    vals = [axes[k] for k in keys]
    wts  = [WEIGHTS.get(k, 1.0) for k in keys]
    final_score = float(np.average(vals, weights=wts))
    return axes, final_score

# ============================================================
# 4. レース単位でバックテスト
# ============================================================
print("\n■ バックテスト実行中（重賞レース）...")

# レースキー構築（年月日+場所+日次+レース番号 → 同一レースの馬を束ねる）
# ※ レースID列は馬単位IDのため使用しない
grade_df = grade_df.copy()
grade_df['race_key'] = (
    grade_df['年'].astype(str) + '_' +
    grade_df['月'].astype(str).str.zfill(2) + '_' +
    grade_df['日'].astype(str).str.zfill(2) + '_' +
    grade_df['場所'].astype(str) + '_' +
    grade_df['日次'].astype(str) + '_' +
    grade_df['レース番号'].astype(str).str.zfill(2)
)

# 重複除去（同一race_key+馬名）
grade_df = grade_df.drop_duplicates(subset=['race_key','馬名'])

results = []  # 各レースの結果
axis_rows = []  # 軸スコア分析用

race_groups = grade_df.groupby('race_key')
total_races = len(race_groups)
print(f"  対象レース数: {total_races}R")

for i, (race_key, rdf) in enumerate(race_groups):
    if i % 500 == 0:
        print(f"  進捗: {i}/{total_races}...")

    # 有効な着順が存在するレースのみ
    valid = rdf[rdf['確定着順'] > 0]
    if len(valid) < 3:
        continue

    # 実際の1着馬
    winner_rows = valid[valid['確定着順'] == 1]
    if winner_rows.empty:
        continue
    actual_winner = winner_rows.iloc[0]['馬名']
    if pd.isna(actual_winner):
        continue
    actual_winner = str(actual_winner).strip()

    # 1番人気馬
    pop1_rows = valid[valid['人気順'] == 1]
    pop1_horse = str(pop1_rows.iloc[0]['馬名']).strip() if not pop1_rows.empty else None

    # スコア計算
    scores = {}
    axis_scores_list = {}
    for idx, row in valid.iterrows():
        try:
            ax, sc = score_horse_full(row)
            scores[idx] = sc
            axis_scores_list[idx] = ax
        except Exception:
            scores[idx] = 50.0
            axis_scores_list[idx] = {}

    if not scores:
        continue

    # ◎（最高スコア馬）
    best_idx = max(scores, key=scores.get)
    predicted_winner = str(valid.loc[best_idx, '馬名']).strip()

    hit = (predicted_winner == actual_winner)
    pop1_hit = (pop1_horse == actual_winner) if pop1_horse else False

    # メタ情報
    meta_row = valid.iloc[0]
    grade   = str(meta_row['grade'])
    venue   = str(meta_row['場所']).strip()
    surface = str(meta_row['芝・ダ']).strip()
    dist    = int(meta_row['距離'])
    track   = str(meta_row.get('馬場状態', '')).strip()

    results.append({
        'race_key': race_key,
        'grade': grade,
        'venue': venue,
        'surface': surface,
        'dist': dist,
        'dist_band': dist_band(dist),
        'track': track,
        'n_horses': len(valid),
        'hit': hit,
        'pop1_hit': pop1_hit,
        'predicted': predicted_winner,
        'actual': actual_winner,
        'pop1': pop1_horse,
    })

    # 軸スコア分析用データ
    for idx, row in valid.iterrows():
        ax = axis_scores_list.get(idx, {})
        entry = {
            'race_key': race_key,
            'horse': str(row['馬名']).strip(),
            'finish_pos': int(row['確定着順']),
        }
        entry.update(ax)
        axis_rows.append(entry)

print(f"  完了: 有効レース数 {len(results)}R")

df_res   = pd.DataFrame(results)
df_axis  = pd.DataFrame(axis_rows)

# ============================================================
# 5. 集計・出力
# ============================================================
print("\n" + "="*60)
print("  COURSE MASTER v7.3  重賞バックテスト結果")
print("="*60)

total_R = len(df_res)
engine_hits = df_res['hit'].sum()
pop1_hits   = df_res['pop1_hit'].sum()

print(f"\n【検証1】重賞レース ◎的中率")
print(f"  対象レース数: {total_R:,}R")
print(f"  エンジン的中: {engine_hits:,}R → {engine_hits/total_R*100:.1f}%")
print(f"  1番人気的中: {pop1_hits:,}R → {pop1_hits/total_R*100:.1f}%")

# グレード別
print(f"\n  ─ グレード別 ─")
for g in ['G1','G2','G3']:
    sub = df_res[df_res['grade'] == g]
    if len(sub) == 0:
        continue
    e_h = sub['hit'].sum()
    p_h = sub['pop1_hit'].sum()
    print(f"  {g}: {len(sub):>4}R  エンジン{e_h/len(sub)*100:5.1f}%  1人気{p_h/len(sub)*100:5.1f}%  差{(e_h-p_h)/len(sub)*100:+.1f}%")

# 会場別（上位5・下位5）
print(f"\n  ─ 会場別 ─")
venue_stats = (df_res.groupby('venue')
               .agg(R=('hit','count'), hit=('hit','sum'), pop1=('pop1_hit','sum'))
               .assign(engine_pct=lambda x: x['hit']/x['R']*100,
                       pop1_pct=lambda x: x['pop1']/x['R']*100)
               .query('R >= 10')
               .sort_values('engine_pct', ascending=False))

print(f"  {'会場':<8} {'R':>5} {'エンジン':>8} {'1人気':>7} {'差':>6}")
print(f"  ─ 上位5 ─")
for venue, row in venue_stats.head(5).iterrows():
    diff = row['engine_pct'] - row['pop1_pct']
    print(f"  {venue:<8} {int(row['R']):>5} {row['engine_pct']:>7.1f}% {row['pop1_pct']:>6.1f}% {diff:>+6.1f}%")
print(f"  ─ 下位5 ─")
for venue, row in venue_stats.tail(5).iterrows():
    diff = row['engine_pct'] - row['pop1_pct']
    print(f"  {venue:<8} {int(row['R']):>5} {row['engine_pct']:>7.1f}% {row['pop1_pct']:>6.1f}% {diff:>+6.1f}%")

# 距離帯別
print(f"\n  ─ 距離帯別 ─")
for band in ['〜1400m','1600〜2000m','2200m〜']:
    sub = df_res[df_res['dist_band'] == band]
    if len(sub) == 0:
        continue
    e_h = sub['hit'].sum()
    p_h = sub['pop1_hit'].sum()
    diff = (e_h - p_h) / len(sub) * 100
    print(f"  {band:<12}: {len(sub):>4}R  エンジン{e_h/len(sub)*100:5.1f}%  1人気{p_h/len(sub)*100:5.1f}%  差{diff:>+.1f}%")

# 芝・ダート別
print(f"\n  ─ 芝・ダート別 ─")
for surf in df_res['surface'].unique():
    sub = df_res[df_res['surface'] == surf]
    if len(sub) < 5:
        continue
    e_h = sub['hit'].sum()
    p_h = sub['pop1_hit'].sum()
    diff = (e_h - p_h) / len(sub) * 100
    print(f"  {surf:<4}: {len(sub):>4}R  エンジン{e_h/len(sub)*100:5.1f}%  1人気{p_h/len(sub)*100:5.1f}%  差{diff:>+.1f}%")

# ============================================================
# 検証2: エンジンが1番人気を上回る/下回る条件
# ============================================================
print(f"\n【検証2】エンジンvs1番人気：優位条件・劣位条件")

diff_stats = (df_res.groupby(['grade','surface','dist_band'])
              .agg(R=('hit','count'), e=('hit','sum'), p=('pop1_hit','sum'))
              .assign(e_pct=lambda x: x['e']/x['R']*100,
                      p_pct=lambda x: x['p']/x['R']*100,
                      diff=lambda x: x['e_pct']-x['p_pct'])
              .query('R >= 10')
              .sort_values('diff', ascending=False))

print(f"\n  エンジン優位条件（上位5）:")
print(f"  {'条件':<25} {'R':>5} {'エンジン':>8} {'1人気':>7} {'差':>6}")
for idx, row in diff_stats.head(5).iterrows():
    label = f"{idx[0]} {idx[1]} {idx[2]}"
    print(f"  {label:<25} {int(row['R']):>5} {row['e_pct']:>7.1f}% {row['p_pct']:>6.1f}% {row['diff']:>+6.1f}%")

print(f"\n  エンジン劣位条件（下位5）:")
for idx, row in diff_stats.tail(5).iterrows():
    label = f"{idx[0]} {idx[1]} {idx[2]}"
    print(f"  {label:<25} {int(row['R']):>5} {row['e_pct']:>7.1f}% {row['p_pct']:>6.1f}% {row['diff']:>+6.1f}%")

# ============================================================
# 検証3: 9軸の寄与度分析
# ============================================================
print(f"\n【検証3】9軸の寄与度分析（着順との相関）")
print(f"  ※ 相関係数の符号: 負 = 着順が良い（1着に近い）ほど高スコア → 望ましい")

AXES = ['CF','BF','SI','JT','PD','BL','HP','SPD','MK']
df_ax_valid = df_axis[df_axis['finish_pos'] > 0].copy()

corr_results = []
for ax in AXES:
    if ax not in df_ax_valid.columns:
        continue
    sub = df_ax_valid[['finish_pos', ax]].dropna()
    if len(sub) < 100:
        continue
    corr = sub['finish_pos'].corr(sub[ax])
    corr_results.append((ax, corr, len(sub)))

corr_results.sort(key=lambda x: x[1])

print(f"\n  {'軸':<5} {'相関係数':>8}  {'サンプル':>8}  評価")
for ax, c, n in corr_results:
    bar = '●' * min(10, int(abs(c) * 100 / 3))
    direction = '負→良' if c < -0.05 else ('正→逆効果' if c > 0.05 else '中立')
    print(f"  {ax:<5} {c:>+8.4f}  {n:>8,}  {direction}  {bar}")

# 軸別の◎選出貢献度（その軸が最高値だった場合に◎が一致する率）
print(f"\n  ─ 軸単独で◎を選んだ場合の的中率 ─")
axis_hit = []
for ax in AXES:
    if ax not in df_ax_valid.columns:
        continue
    hits, total = 0, 0
    for rk, grp in df_ax_valid.groupby('race_key'):
        grp = grp.dropna(subset=[ax])
        if grp.empty:
            continue
        best_horse = grp.loc[grp[ax].idxmax(), 'horse']
        winner = grp[grp['finish_pos'] == 1]
        if winner.empty:
            continue
        actual = str(winner.iloc[0]['horse']).strip()
        if str(best_horse).strip() == actual:
            hits += 1
        total += 1
    if total > 0:
        axis_hit.append((ax, hits/total*100, total))

axis_hit.sort(key=lambda x: -x[1])
print(f"  {'軸':<5} {'的中率':>8}  {'レース数':>8}")
for ax, pct, n in axis_hit:
    print(f"  {ax:<5} {pct:>7.1f}%  {n:>8,}")

print(f"\n  ─ 9軸エンジン: {engine_hits/total_R*100:.1f}%  1番人気: {pop1_hits/total_R*100:.1f}% ─")

# ============================================================
# 年別推移
# ============================================================
print(f"\n【補足】年別的中率推移")
if '年' in grade_df.columns:
    df_res_year = df_res.copy()
    # race_keyから年を取得
    year_map = grade_df.drop_duplicates(subset=['race_key']).set_index('race_key')['年'].to_dict()
    df_res_year['year'] = df_res_year['race_key'].map(year_map)
    year_stats = (df_res_year.groupby('year')
                  .agg(R=('hit','count'), e=('hit','sum'), p=('pop1_hit','sum'))
                  .assign(e_pct=lambda x: x['e']/x['R']*100,
                          p_pct=lambda x: x['p']/x['R']*100))
    print(f"  {'年':<6} {'R':>5} {'エンジン':>8} {'1人気':>7}")
    for yr, row in year_stats.iterrows():
        print(f"  {yr:<6} {int(row['R']):>5} {row['e_pct']:>7.1f}% {row['p_pct']:>6.1f}%")

print("\n■ 完了")
