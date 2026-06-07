# -*- coding: utf-8 -*-
"""
generate_stats_cutoffs.py
年次カットオフ別統計マスターを stats/ ディレクトリに生成する。

生成ファイル:
  stats/stats_cutoff_2021.json  (〜2021-12-31以前のデータで集計)
  stats/stats_cutoff_2022.json  (〜2022-12-31以前のデータで集計)
  stats/stats_cutoff_2023.json  (〜2023-12-31以前のデータで集計)
  stats/stats_cutoff_2024.json  (〜2024-12-31以前のデータで集計)

集計統計種:
  sire_stats    : 種牡馬別勝率 (10走以上)
  jockey_stats  : 騎手別勝率   (50走以上)
  trainer_stats : 調教師別勝率 (50走以上)
  distance_stats: 距離別走破時計分布 (10本以上)
  track_stats   : 場所×馬場別勝率   (50走以上)

注意: 既存の PKL・cm_stats_v72.json は一切上書きしない
"""

import sys
import io
import os
import json

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
RACE_DIR  = os.path.join(BASE_DIR, 'data', 'race')
PED_DIR   = os.path.join(BASE_DIR, 'data', 'pedigree')
STATS_DIR = os.path.join(BASE_DIR, 'stats')
os.makedirs(STATS_DIR, exist_ok=True)

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

CUTOFFS            = [2021, 2022, 2023, 2024]
MIN_SIRE_RACES     = 10
MIN_JOCKEY_RACES   = 50
MIN_TRAINER_RACES  = 50
MIN_DIST_TIMES     = 10
MIN_TRACK_RACES    = 50

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
df_all['確定着順']     = pd.to_numeric(df_all['確定着順'], errors='coerce').fillna(0).astype(int)
df_all['走破時計_sec'] = pd.to_numeric(df_all['走破時計'], errors='coerce')
df_all['距離']         = pd.to_numeric(df_all['距離'], errors='coerce').fillna(0).astype(int)
df_all['年']           = pd.to_numeric(df_all['年'], errors='coerce').fillna(0).astype(int)
# 年列は2桁西暦（15=2015, 26=2026）→ 4桁に変換
df_all['年4']          = df_all['年'].apply(lambda y: 2000 + y if 0 < y < 100 else y)

print("\n■ 血統データ読み込み中...")
df_blood = pd.read_csv(BLOOD_FILE, encoding='cp932', low_memory=False)
blood_slim = df_blood[['血統登録番号', '種牡馬名', '母の父名']].copy()
blood_slim.columns = ['血統登録番号', '父馬名_b', '母の父馬名_b']
df_all = df_all.merge(blood_slim, on='血統登録番号', how='left')
df_all['父馬名']     = df_all['父馬名'].fillna(df_all['父馬名_b'])
df_all['母の父馬名'] = df_all['母の父馬名'].fillna(df_all['母の父馬名_b'])
df_all.drop(['父馬名_b', '母の父馬名_b'], axis=1, inplace=True)
print(f"  父馬名マッチ率: {df_all['父馬名'].notna().mean()*100:.1f}%")


# ============================================================
# 2. 統計マスター構築関数
# ============================================================
def build_stats(df_src, cutoff_year):
    """指定カットオフ年以前のデータから統計マスターを構築して返す"""
    n_records = len(df_src)
    print(f"\n  [cutoff={cutoff_year}] 訓練レコード数={n_records:,}件")

    stats = {
        'cutoff_year':       cutoff_year,
        'created':           pd.Timestamp.now().strftime('%Y-%m-%d %H:%M'),
        'training_records':  int(n_records),
        'sire_stats':        {},
        'jockey_stats':      {},
        'trainer_stats':     {},
        'distance_stats':    {},
        'track_stats':       {},
    }

    # 種牡馬別勝率
    for sire, grp in df_src.groupby('父馬名'):
        n = len(grp)
        if n < MIN_SIRE_RACES or pd.isna(sire):
            continue
        wins   = int((grp['確定着順'] == 1).sum())
        places = int((grp['確定着順'] <= 3).sum())
        stats['sire_stats'][str(sire)] = {
            'races': int(n), 'wins': wins, 'places': places,
            'win_rate':   float(wins / n),
            'place_rate': float(places / n),
        }

    # 騎手別勝率
    if '騎手名' in df_src.columns:
        for jockey, grp in df_src.groupby('騎手名'):
            n = len(grp)
            if n < MIN_JOCKEY_RACES or pd.isna(jockey):
                continue
            wins   = int((grp['確定着順'] == 1).sum())
            places = int((grp['確定着順'] <= 3).sum())
            stats['jockey_stats'][str(jockey)] = {
                'races': int(n), 'wins': wins, 'places': places,
                'win_rate':   float(wins / n),
                'place_rate': float(places / n),
            }

    # 調教師別勝率
    if '調教師' in df_src.columns:
        for trainer, grp in df_src.groupby('調教師'):
            n = len(grp)
            if n < MIN_TRAINER_RACES or pd.isna(trainer):
                continue
            wins   = int((grp['確定着順'] == 1).sum())
            places = int((grp['確定着順'] <= 3).sum())
            stats['trainer_stats'][str(trainer)] = {
                'races': int(n), 'wins': wins, 'places': places,
                'win_rate':   float(wins / n),
                'place_rate': float(places / n),
            }

    # 距離別統計（走破時計の平均・標準偏差）
    for dist, grp in df_src.groupby('距離'):
        valid_t = grp['走破時計_sec'].dropna()
        if len(valid_t) < MIN_DIST_TIMES:
            continue
        # JSONはstr key必須のため文字列で保存（load時にintへ変換）
        stats['distance_stats'][str(int(dist))] = {
            'n':        int(len(grp)),
            'avg_time': float(valid_t.mean()),
            'std_time': float(valid_t.std()) if len(valid_t) > 1 else 0.0,
        }

    # 場所×芝ダ別勝率（track_stats）
    if '場所' in df_src.columns and '芝・ダ' in df_src.columns:
        for (venue, surface), grp in df_src.groupby(['場所', '芝・ダ']):
            n = len(grp)
            if n < MIN_TRACK_RACES:
                continue
            wins   = int((grp['確定着順'] == 1).sum())
            places = int((grp['確定着順'] <= 3).sum())
            key = f"{venue}_{surface}"
            stats['track_stats'][key] = {
                'races': int(n), 'wins': wins, 'places': places,
                'win_rate':   float(wins / n),
                'place_rate': float(places / n),
            }

    print(f"    種牡馬:{len(stats['sire_stats']):>4}件 "
          f"騎手:{len(stats['jockey_stats']):>4}件 "
          f"調教師:{len(stats['trainer_stats']):>4}件 "
          f"距離:{len(stats['distance_stats']):>3}件 "
          f"会場:{len(stats['track_stats']):>3}件")
    return stats


# ============================================================
# 3. 4カットオフを生成・保存
# ============================================================
print("\n■ 年次カットオフ別統計マスター生成中...")
for cutoff in CUTOFFS:
    df_sub   = df_all[df_all['年4'] <= cutoff].copy()
    stats    = build_stats(df_sub, cutoff)
    out_path = os.path.join(STATS_DIR, f'stats_cutoff_{cutoff}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"    → 保存: {os.path.basename(out_path)} ({size_kb:.0f}KB)")


# ============================================================
# 4. Verify: 生成確認
# ============================================================
print("\n■ Verify: 生成ファイル確認")
prev_sire_n = None
all_ok = True
for cutoff in CUTOFFS:
    path = os.path.join(STATS_DIR, f'stats_cutoff_{cutoff}.json')
    if not os.path.exists(path):
        print(f"  ✗ NOT FOUND: {os.path.basename(path)}")
        all_ok = False
        continue
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    size_kb = os.path.getsize(path) / 1024
    sire_n   = len(data['sire_stats'])
    jockey_n = len(data['jockey_stats'])
    dist_n   = len(data['distance_stats'])
    track_n  = len(data['track_stats'])
    trend = ""
    if prev_sire_n is not None:
        trend = "↑" if sire_n > prev_sire_n else "→"
    print(f"  ✓ stats_cutoff_{cutoff}.json {size_kb:>5.0f}KB "
          f"| 種牡馬={sire_n:>4} {trend} 騎手={jockey_n:>4} "
          f"距離={dist_n:>3} 会場={track_n:>3}")
    prev_sire_n = sire_n

print(f"\n{'■ すべて正常に生成されました' if all_ok else '■ エラー: 一部ファイルが未生成'}")
print("■ 完了")
