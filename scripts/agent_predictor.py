# -*- coding: utf-8 -*-
"""
scripts/agent_predictor.py - 予測エージェント

candidates_{date}.json からレース情報を読み込み、
race_results テーブルで全馬データを復元してエンジン予測を実行する。
出力: predictions_{date}.json
"""

import os
import sys
import json
import sqlite3
import argparse
from datetime import date as dt_date, datetime

# Windows環境での日本語出力
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np

DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')
PKL_PATH = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_CSV = os.path.join(BASE_DIR, 'data', 'pedigree', '血統_0410.csv')


# ─────────────────────────────────────────────────────────
def load_engine():
    from course_master_v73_engine import CourseMASTERv73
    engine = CourseMASTERv73()
    engine.load(PKL_PATH)
    engine.df_blood = pd.read_csv(BLOOD_CSV, encoding='cp932')
    print(f'  [predictor] エンジン読み込み完了（{len(engine.df_blood):,}馬）')
    return engine


def fetch_race_horses(con, venue, race_date, race_no):
    """race_results から特定レースの全馬を取得する。"""
    query = """
        SELECT horse_name, sire_name, finish_pos, popularity, tansho_odds,
               surface, distance, track_cond, venue
        FROM race_results
        WHERE venue = ? AND race_date = ? AND race_no = ?
        ORDER BY popularity ASC
    """
    cur = con.cursor()
    cur.execute(query, (venue, race_date, race_no))
    rows = cur.fetchall()
    return rows


def build_race_dict(venue, race_date, race_no, rows):
    """DB取得行 → grade_race_predictor 互換の race dict を構築する。"""
    if not rows:
        return None

    # race_date を YYYYMMDD 形式のレースIDに変換（簡易）
    date_part = race_date.replace('-', '')
    race_name = f'{venue}{race_no}R（復元データ）'

    # surface/distance/track_condは全馬共通なので最初の行から取得
    _, _, _, _, _, surface, distance, track_cond, _ = rows[0]

    horses = []
    for horse_name, sire, finish_pos, popularity, odds, *_ in rows:
        horses.append({
            'horse_name': horse_name or '',
            'jockey':     '',
            'sire':       sire or '',
            'dam_sire':   '',
            'age':        4,
            'weight':     56.0,
            'popularity': int(popularity) if popularity else 0,
            'odds':       float(odds) if odds else 0.0,
            'body_weight': 0,
        })

    return {
        'race_name':  race_name,
        'venue':      venue,
        'surface':    surface or '芝',
        'distance':   int(distance) if distance else 0,
        'track_cond': track_cond or '良',
        'class_code': 800,
        'horses':     horses,
    }


def calc_chaos_index(race):
    """荒れ指数を3要素加重平均で算出（0〜100）。"""
    horses = race.get('horses', [])
    odds_list = sorted([h['odds'] for h in horses if h['odds'] > 0])
    if len(odds_list) < 3:
        return {'score': 50.0, 'A': 50.0, 'B': 50.0, 'C': 20.0}

    score_a = min(100.0, (odds_list[0] / odds_list[2]) * 100)

    total_inv = sum(1 / o for o in odds_list if o > 0)
    support = (1 / odds_list[0]) / total_inv if total_inv > 0 else 0.5
    score_b = max(0.0, min(100.0, (0.50 - support) / 0.20 * 100))

    cond_map = {'良': 20.0, '稍重': 50.0, '重': 80.0, '不良': 100.0}
    score_c = cond_map.get(race.get('track_cond', '良'), 20.0)

    score = score_a * 0.4 + score_b * 0.4 + score_c * 0.2
    return {'score': round(score, 1), 'A': round(score_a, 1),
            'B': round(score_b, 1), 'C': round(score_c, 1)}


def run_prediction_for_race(engine, race):
    """1レース分の予測を実行し、上位結果を返す。"""
    from grade_race_predictor import build_race_df

    df = build_race_df(race)
    if df is None or len(df) == 0:
        return None

    try:
        scored    = engine.score_race(df)                        # {idx: score}
        win_probs = engine.score_to_win_prob(scored, df)         # {idx: win_prob}
    except Exception as e:
        print(f'  [predictor] score_race エラー: {e}')
        return None

    odds_map = {h['horse_name']: float(h.get('odds', 0)) for h in race['horses']}
    sorted_entries = sorted(scored.items(), key=lambda x: x[1], reverse=True)

    top5 = []
    for idx, score in sorted_entries[:5]:
        horse_name  = df.loc[idx, '馬名']
        win_prob    = win_probs.get(idx, 0.0)
        odds        = odds_map.get(horse_name, 0.0)
        market_prob = (1 / odds * 0.80) if odds > 0 else 0.0
        edge        = round(float(win_prob) - market_prob, 4)
        pop_val     = df.loc[idx, '人気順']
        top5.append({
            'horse_name': horse_name,
            'score':      round(float(score), 2),
            'win_prob':   round(float(win_prob), 4),
            'popularity': int(pop_val) if pop_val else 0,
            'odds':       odds,
            'edge':       edge,
        })

    chaos  = calc_chaos_index(race)
    honmei = top5[0] if top5 else {}

    return {
        'horse_count': len(race['horses']),
        'honmei':      honmei,
        'chaos_index': chaos['score'],
        'top5':        top5,
    }


# ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='予測エージェント')
    parser.add_argument('--date', default=dt_date.today().isoformat(),
                        help='対象日（YYYY-MM-DD）')
    args = parser.parse_args()
    target_date = args.date

    date_nodash     = target_date.replace('-', '')
    candidates_path = os.path.join(BASE_DIR, f'candidates_{date_nodash}.json')
    output_path     = os.path.join(BASE_DIR, f'predictions_{date_nodash}.json')

    print(f'[predictor] 開始 date={target_date}')

    if not os.path.exists(candidates_path):
        result = {'date': target_date, 'error': f'candidates not found: {candidates_path}',
                  'races': []}
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'[predictor] candidates が見つかりません: {candidates_path}')
        sys.exit(0)

    with open(candidates_path, encoding='utf-8') as f:
        cands = json.load(f)

    venue = cands.get('venue', '')
    raw_candidates = cands.get('candidates', [])

    # (race_no) ごとにユニーク化
    race_nos = sorted(set(c[0] for c in raw_candidates))
    print(f'[predictor] 対象レース: {venue} {race_nos}')

    # エンジン読み込み
    engine = load_engine()

    races_output = []
    con = sqlite3.connect(DB_PATH)

    for race_no in race_nos:
        rows = fetch_race_horses(con, venue, target_date, race_no)
        if not rows:
            print(f'  [predictor] {venue}{race_no}R: race_results にデータなし → スキップ')
            races_output.append({'race_no': race_no, 'error': 'no data in race_results'})
            continue

        race = build_race_dict(venue, target_date, race_no, rows)
        if not race:
            continue

        print(f'  [predictor] {venue}{race_no}R 予測中（{len(rows)}頭）')
        pred = run_prediction_for_race(engine, race)
        if pred:
            pred['race_no'] = race_no
            races_output.append(pred)
        else:
            races_output.append({'race_no': race_no, 'error': 'prediction failed'})

    con.close()

    output = {
        'date':         target_date,
        'venue':        venue,
        'races':        races_output,
        'generated_at': datetime.now().isoformat(timespec='seconds'),
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f'[predictor] 完了 → {output_path}')


if __name__ == '__main__':
    main()
