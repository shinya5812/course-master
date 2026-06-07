# -*- coding: utf-8 -*-
"""
backtest_jockey_course_2024.py
騎手×場所×距離帯コース相性補正の有効性検証

テスト期間 : 2024年 Grade (G1/G2/G3) レース
評価指標   : ◎的中率（1着）・単勝回収率（100円単勝◎のみ）
比較       : JT補正なし（現行） vs JT補正あり（新規）

採否基準   : 的中率改善幅 +1% 以上 → 採用
出力       : output/backtest_jockey_course_2024.csv
"""

import os
import sys
import io
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
STATS_PATH = os.path.join(BASE_DIR, 'output', 'jockey_course_stats.json')
OUT_DIR    = os.path.join(BASE_DIR, 'output')

sys.path.insert(0, BASE_DIR)
from backtest_utils import get_stats_for_race, score_horse_v73, WEIGHTS

GRADE_PATTERN = re.compile(r'[GＧ][ⅠⅡⅢ123１２３]')

CSV_FILES = [
    os.path.join(RACE_DIR, '2024_2026結果.csv'),
    os.path.join(RACE_DIR, '2026結果.csv'),
    os.path.join(RACE_DIR, '202602280331結果.csv'),
    os.path.join(RACE_DIR, '結果202603070405.csv'),
    os.path.join(RACE_DIR, '結果202604110419.csv'),
    os.path.join(RACE_DIR, '結果202604250510.csv'),
    os.path.join(RACE_DIR, '結果202605160524.csv'),
]


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


def dist_to_cat(dist):
    d = int(dist or 0)
    if d <= 1400:
        return 'sprint'
    elif d <= 1800:
        return 'mile'
    elif d <= 2200:
        return 'middle'
    else:
        return 'long'


def score_horse_with_correction(row, stats, jcs):
    """
    score_horse_v73 の JT 軸にコース相性係数を乗算して返す。
    jcs : jockey_course_stats dict（キーがなければ係数1.0 = 変化なし）
    """
    # JT 基本スコア（現行と同じ計算）
    jockey       = str(row.get('騎手名', '') or '').strip()
    jockey_stats = stats.get('jockey_stats', {})
    jt_base = (min(100.0, jockey_stats[jockey]['win_rate'] * 100)
               if jockey and jockey in jockey_stats else 50.0)

    # コース相性係数
    coef = 1.0
    if jockey and jcs:
        venue    = str(row.get('場所', '') or '')
        surface  = str(row.get('芝・ダ', '') or '')
        surf_key = 'ダ' if 'ダ' in surface else '芝'
        dist_cat = dist_to_cat(row.get('距離', 0))
        key = f"{jockey}|{venue}|{surf_key}|{dist_cat}"
        if key in jcs:
            coef = jcs[key]['lift']   # すでに 0.5〜2.0 にクリップ済み

    if coef == 1.0:
        return score_horse_v73(row, stats)

    jt_adj = min(100.0, jt_base * coef)

    # 7軸を再集計（JT だけ差し替え）
    # まず全軸を取得するため score_horse_v73 の内部コードを参照
    # 簡易実装: base_score + JT_WEIGHT×(jt_adj - jt_base) / total_weight
    base_score = score_horse_v73(row, stats)

    # 重み合計（現行 7 軸: CF2+SI2+SPD2+JT2+PD1+BL0.3+MK0.3 = 9.6）
    total_w = sum(WEIGHTS.values())
    jt_w    = WEIGHTS.get('JT', 2.0)

    # JT の差分だけ修正
    adjusted = base_score + jt_w * (jt_adj - jt_base) / total_w
    return adjusted


# ─────────────────────────────────────────────────────────
# データ読み込み
# ─────────────────────────────────────────────────────────
print("■ CSVデータ読み込み中...")
dfs = []
for f in CSV_FILES:
    if os.path.exists(f):
        dfs.append(pd.read_csv(f, encoding='cp932', low_memory=False))
df_all = pd.concat(dfs, ignore_index=True)
print(f"  合計: {len(df_all):,}件")

# 数値化
df_all['確定着順']           = pd.to_numeric(df_all['確定着順'],  errors='coerce').fillna(0).astype(int)
df_all['人気順']             = pd.to_numeric(df_all['人気順'],    errors='coerce').fillna(0).astype(int)
df_all['走破時計_sec']       = pd.to_numeric(df_all['走破時計'],  errors='coerce')
df_all['単勝オッズ_num']     = pd.to_numeric(df_all['単勝オッズ'], errors='coerce').fillna(0)
df_all['上がり3Fタイム_sec'] = pd.to_numeric(df_all['上がり3Fタイム'], errors='coerce')
df_all['距離']               = pd.to_numeric(df_all['距離'],      errors='coerce').fillna(0).astype(int)
df_all['年']                 = pd.to_numeric(df_all['年'],        errors='coerce').fillna(0).astype(int)
df_all['月']                 = pd.to_numeric(df_all['月'],        errors='coerce').fillna(0).astype(int)
df_all['日']                 = pd.to_numeric(df_all['日'],        errors='coerce').fillna(0).astype(int)
df_all['年4']                = df_all['年'].apply(lambda y: 2000 + y if 0 < y < 100 else y)
for col in ['通過順1', '通過順2', '通過順3', '通過順4']:
    df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

# 2024年に絞る
df_2024 = df_all[df_all['年4'] == 2024].copy()
print(f"  2024年: {len(df_2024):,}件")

# Grade判定
df_2024['grade'] = df_2024['レース名'].apply(detect_grade)
df_grade = df_2024[df_2024['grade'].notna()].copy()
print(f"  2024年 Grade: {len(df_grade):,}件")

# 血統データ読み込み
print("\n■ 血統データ読み込み中...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
    df_blood[col] = pd.to_numeric(df_blood[col], errors='coerce').fillna(0).astype(int)
df_blood['total_races'] = (df_blood['全成績1着数'] + df_blood['全成績2着数']
                           + df_blood['全成績3着数'] + df_blood['全成績着外数'])
blood_dict = {}
for _, br in df_blood.iterrows():
    hn = str(br.get('馬名', '') or '').strip()
    if hn:
        blood_dict[hn] = (int(br['total_races']), int(br['全成績1着数']))

# コース相性統計読み込み
print("\n■ コース相性統計読み込み中...")
with open(STATS_PATH, 'r', encoding='utf-8') as f:
    jcs = json.load(f)
print(f"  {len(jcs):,}件")

# ─────────────────────────────────────────────────────────
# グルーピング（レース単位で処理）
# ─────────────────────────────────────────────────────────
race_key_cols = ['年4', '月', '日', '場所', '芝・ダ', '距離', 'レース名', 'grade']
grouped = df_grade.groupby(race_key_cols)

print(f"\n■ バックテスト開始（{grouped.ngroups}レース）...")

records      = []
before_hits  = 0
after_hits   = 0
total_races  = 0
before_invest = 0
before_return = 0
after_invest  = 0
after_return  = 0

for keys, grp in grouped:
    year4, month, day, venue, surface, distance, race_name, grade = keys

    # 10頭未満は除外
    if len(grp) < 10:
        continue

    # 確定着順 0 = 競走除外馬を除く
    grp_valid = grp[grp['確定着順'] > 0].copy()
    if len(grp_valid) < 5:
        continue

    race_date = f"{int(year4)}-{int(month):02d}-{int(day):02d}"
    try:
        stats = get_stats_for_race(race_date)
    except FileNotFoundError:
        continue

    # 各馬スコア算出
    before_scores = {}
    after_scores  = {}
    for _, row in grp_valid.iterrows():
        try:
            sb = score_horse_v73(row, stats, blood_dict=blood_dict)
            sa = score_horse_with_correction(row, stats, jcs)
        except Exception:
            sb = sa = 50.0
        hn = str(row.get('馬名', ''))
        before_scores[hn] = sb
        after_scores[hn]  = sa

    if not before_scores:
        continue

    # ◎（最高スコア馬）を決定
    honmei_before = max(before_scores, key=before_scores.get)
    honmei_after  = max(after_scores,  key=after_scores.get)

    # 1着馬と単勝オッズを取得
    winner_row = grp_valid[grp_valid['確定着順'] == 1]
    if len(winner_row) == 0:
        continue
    winner     = str(winner_row.iloc[0]['馬名'])
    winner_odds = float(winner_row.iloc[0]['単勝オッズ_num'] or 0)

    # ◎が何番人気・オッズかも記録
    def get_pop_odds(hn):
        r = grp_valid[grp_valid['馬名'] == hn]
        if len(r) == 0:
            return 0, 0.0
        return int(r.iloc[0]['人気順']), float(r.iloc[0]['単勝オッズ_num'] or 0)

    b_pop, b_odds = get_pop_odds(honmei_before)
    a_pop, a_odds = get_pop_odds(honmei_after)

    b_hit = (honmei_before == winner)
    a_hit = (honmei_after  == winner)

    before_hits   += int(b_hit)
    after_hits    += int(a_hit)
    total_races   += 1

    before_invest += 100
    after_invest  += 100
    if b_hit and b_odds > 0:
        before_return += int(b_odds * 100)
    if a_hit and a_odds > 0:
        after_return  += int(a_odds * 100)

    # ◎が同じかどうか
    same = (honmei_before == honmei_after)

    records.append({
        'race_date':      race_date,
        'venue':          venue,
        'surface':        surface,
        'distance':       distance,
        'race_name':      race_name,
        'grade':          grade,
        'winner':         winner,
        'winner_odds':    winner_odds,
        'before_honmei':  honmei_before,
        'before_pop':     b_pop,
        'before_odds':    b_odds,
        'before_hit':     b_hit,
        'after_honmei':   honmei_after,
        'after_pop':      a_pop,
        'after_odds':     a_odds,
        'after_hit':      a_hit,
        'honmei_changed': not same,
    })

# ─────────────────────────────────────────────────────────
# 結果集計
# ─────────────────────────────────────────────────────────
print(f"\n  処理完了: {total_races}レース\n")

b_hitrate = before_hits / total_races * 100 if total_races > 0 else 0
a_hitrate = after_hits  / total_races * 100 if total_races > 0 else 0
b_roi     = before_return / before_invest * 100 if before_invest > 0 else 0
a_roi     = after_return  / after_invest  * 100 if after_invest  > 0 else 0

changed_count = sum(1 for r in records if r['honmei_changed'])

print('=' * 60)
print('  JT コース相性補正 バックテスト結果（2024年 Grade）')
print('=' * 60)
print(f"  対象レース数  : {total_races}R")
print(f"  ◎変更レース数 : {changed_count}R  ({changed_count/total_races*100:.1f}%)")
print()
print(f"  {'':20s}  {'補正なし':>10s}  {'補正あり':>10s}  {'差':>8s}")
print('  ' + '-' * 56)
print(f"  {'◎1着的中数':20s}  {before_hits:>10}  {after_hits:>10}  "
      f"  {after_hits - before_hits:+d}")
print(f"  {'◎1着的中率':20s}  {b_hitrate:>9.1f}%  {a_hitrate:>9.1f}%  "
      f"{a_hitrate - b_hitrate:+8.1f}%")
print(f"  {'単勝ROI':20s}  {b_roi:>9.1f}%  {a_roi:>9.1f}%  "
      f"{a_roi - b_roi:+8.1f}%")
print('=' * 60)

# グレード別集計
print("\n  【グレード別】")
print(f"  {'':6s}  {'補正なし':>10s}  {'補正あり':>10s}  {'差':>8s}  レース数")
for g in ['G1', 'G2', 'G3']:
    g_recs = [r for r in records if r['grade'] == g]
    n = len(g_recs)
    if n == 0:
        continue
    bh = sum(1 for r in g_recs if r['before_hit'])
    ah = sum(1 for r in g_recs if r['after_hit'])
    print(f"  {g:6s}  {bh/n*100:>9.1f}%  {ah/n*100:>9.1f}%  "
          f"{(ah-bh)/n*100:+8.1f}%  {n:>5}R")

# 採否判定
diff = a_hitrate - b_hitrate
print()
print('─' * 60)
if diff >= 1.0:
    verdict = f"✅ 採用（的中率 {diff:+.1f}%改善・基準+1%以上）"
elif diff > 0:
    verdict = f"🟡 効果軽微（的中率 {diff:+.1f}%・基準+1%未達）→ 見送り"
elif diff == 0:
    verdict = "🟡 変化なし → 見送り"
else:
    verdict = f"❌ 悪化（的中率 {diff:+.1f}%）→ 見送り"
print(f"  採否判定: {verdict}")
print('─' * 60)

# CSV保存
os.makedirs(OUT_DIR, exist_ok=True)
df_out = pd.DataFrame(records)
out_path = os.path.join(OUT_DIR, 'backtest_jockey_course_2024.csv')
df_out.to_csv(out_path, index=False, encoding='utf-8-sig')
print(f"\n  CSV保存完了: {out_path}")
print(f"  ({len(df_out)}行)")
