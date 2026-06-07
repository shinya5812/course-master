# -*- coding: utf-8 -*-
"""
backtest_utils.py
時系列分離バックテスト用ユーティリティ

主要関数:
  get_stats_for_race(race_date)
      レース日付（'YYYY-MM-DD' 形式）に応じた統計マスターを返す。
      stats/ ディレクトリの JSON をキャッシュ付きで読み込む。

  score_horse_v73(row, stats, blood_dict)
      7軸スコアを計算して返す（v7.3 エンジン互換）。
      JT 軸・SPD 軸は stats から取得（時系列リーク排除済み）。
      CF 軸は blood_dict（血統CSV）から取得。

マッピング（get_stats_for_race）:
  2022年以前のレース → stats_cutoff_2021.json（訓練期間〜2021）
  2023年のレース     → stats_cutoff_2022.json（訓練期間〜2022）
  2024年のレース     → stats_cutoff_2023.json（訓練期間〜2023）
  2025年以降のレース → stats_cutoff_2024.json（訓練期間〜2024）
"""

import os
import json
import numpy as np
import pandas as pd

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
STATS_DIR = os.path.join(BASE_DIR, 'stats')

CAREER_PENALTY = {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
ODDS_MK_TABLE  = [(0.0, 2.0, 0.85), (2.0, 3.0, 0.90), (3.0, 999.0, 1.00)]
WEIGHTS = {
    'CF': 2.0, 'SI': 2.0, 'SPD': 2.0, 'JT': 2.0,
    'PD': 1.0, 'BL': 0.3,  'MK': 0.3,
}

# ロード済み統計マスターのキャッシュ（cutoff_year → dict）
_stats_cache: dict = {}


def _cutoff_for_year(race_year: int) -> int:
    """レース年から使用するカットオフ年を返す"""
    if race_year <= 2022:
        return 2021
    elif race_year == 2023:
        return 2022
    elif race_year == 2024:
        return 2023
    else:
        return 2024


def get_stats_for_race(race_date: str) -> dict:
    """
    レース日付に応じた統計マスターを返す（キャッシュ付き）。

    Parameters
    ----------
    race_date : str
        'YYYY-MM-DD' 形式（先頭4文字が年として使用される）

    Returns
    -------
    dict
        {cutoff_year, training_records,
         sire_stats, jockey_stats, trainer_stats,
         distance_stats（int キー）, track_stats}

    Raises
    ------
    FileNotFoundError
        stats/ に JSON が存在しない場合（generate_stats_cutoffs.py を先に実行する）
    """
    race_year = int(str(race_date)[:4])
    cutoff    = _cutoff_for_year(race_year)

    if cutoff not in _stats_cache:
        path = os.path.join(STATS_DIR, f'stats_cutoff_{cutoff}.json')
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"統計ファイルが見つかりません: {path}\n"
                f"先に generate_stats_cutoffs.py を実行してください。"
            )
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # distance_stats のキーを str → int に変換（JSON は文字列キーのみ）
        data['distance_stats'] = {int(k): v for k, v in data['distance_stats'].items()}
        _stats_cache[cutoff] = data

    return _stats_cache[cutoff]


def score_horse_v73(row, stats: dict, blood_dict: dict | None = None,
                    use_horse_stats: bool = True) -> float:
    """
    7軸スコアを計算して返す（v7.3 エンジン互換）。

    Parameters
    ----------
    row             : pd.Series
        レース結果の 1 行（各軸に必要なカラムを含む）
    stats           : dict
        get_stats_for_race() の返り値
        JT 軸・SPD 軸の統計として使用
    blood_dict      : dict | None
        {馬名: (total_races, total_wins)} 血統 CSV 由来
        use_horse_stats=False の場合のフォールバック（本番予測・条件B比較用）
    use_horse_stats : bool
        True（デフォルト）の場合、CF 軸を stats['horse_stats'] から取得（時系列分離・条件C）
        False の場合、CF 軸を blood_dict から取得（血統CSVスナップショット・条件B）

    Returns
    -------
    float
        重み付き平均スコア
    """
    axes: dict = {}

    # ── CF: キャリア形成（時系列分離stats優先 / 血統CSVフォールバック） ──────
    horse_name  = str(row.get('馬名', '') or '').strip()
    horse_stats = stats.get('horse_stats', {}) if use_horse_stats else {}

    if horse_name in horse_stats:
        # 条件C: カットオフ時点のキャリア統計（時系列リーク排除済み）
        hs      = horse_stats[horse_name]
        total_r = hs['total_races']
        total_w = hs['total_wins']
    elif blood_dict and horse_name in blood_dict:
        # 条件B / 本番予測: 血統CSVスナップショット（2026-02-17時点・全期間込み）
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

    # ── SI: スピードインデックス（上がり3F） ──────────────────────────
    agari = row.get('上がり3Fタイム_sec')
    axes['SI'] = (max(10.0, 100 - (float(agari) - 30) * 2)
                  if pd.notna(agari) else 50.0)

    # ── JT: ジョッキー勝率（時系列分離済み統計） ───────────────────────
    jockey       = row.get('騎手名')
    jockey_stats = stats.get('jockey_stats', {})
    if pd.notna(jockey) and str(jockey) in jockey_stats:
        axes['JT'] = min(100.0, jockey_stats[str(jockey)]['win_rate'] * 100)
    else:
        axes['JT'] = 50.0

    # ── PD: ペースデザイン（通過順） ──────────────────────────────────
    passages = [row.get(f'通過順{i}') for i in range(1, 5)]
    passages = [float(p) for p in passages if pd.notna(p) and float(p) > 0]
    if passages:
        axes['PD'] = max(10.0, 100 - abs(float(np.mean(passages)) - 7) * 3)
    else:
        axes['PD'] = 50.0

    # ── BL: ベース力（人気順） ────────────────────────────────────────
    pop = int(row.get('人気順', 0) or 0)
    axes['BL'] = max(10.0, 100 - pop * 5) if pop > 0 else 50.0

    # ── SPD: スピード能力（走破時計 z-score、時系列分離済み統計） ───────
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

    # ── MK: マーケット（人気順 + オッズ帯補正） ───────────────────────
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

    # ── 重み付き平均 ──────────────────────────────────────────────────
    keys = list(axes.keys())
    vals = [axes[k] for k in keys]
    wts  = [WEIGHTS.get(k, 1.0) for k in keys]
    return float(np.average(vals, weights=wts))
