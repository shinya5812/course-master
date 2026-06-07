# -*- coding: utf-8 -*-
"""
仮説検証: 条件Bの人気フィルター見直し
福島ダ1700m × スタミナ系血統 × 人気帯別 回収率比較
"""

import sqlite3
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'course_master.db')

VENUE = '福島'
SURFACE = 'ダ'
DISTANCE = 1700
CATEGORY = 'スタミナ系'
TRACK_CONDS = ('良', '重')  # 条件B馬場フィルター


def run():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # blood_category からスタミナ系種牡馬を取得
    cur.execute("SELECT sire_name FROM blood_category WHERE category = ?", (CATEGORY,))
    stamina_sires = {row[0] for row in cur.fetchall()}
    print(f"スタミナ系種牡馬: {len(stamina_sires)}件")

    # race_results から福島ダ1700m の全データ取得
    cur.execute("""
        SELECT r.race_date, r.venue, r.surface, r.distance, r.track_cond,
               r.race_no, r.horse_name, r.sire_name, r.finish_pos, r.popularity,
               r.tansho_odds
        FROM race_results r
        WHERE r.venue = ? AND r.surface = ? AND r.distance = ?
        ORDER BY r.race_date, r.race_no
    """, (VENUE, SURFACE, DISTANCE))
    rows = cur.fetchall()
    conn.close()

    print(f"福島ダ{DISTANCE}m 総レコード数: {len(rows)}件")

    # レース単位に集約
    # key: (race_date, race_no) → list of (horse_name, sire_name, finish_pos, popularity, tansho_odds, track_cond)
    races = {}
    for row in rows:
        race_date, venue, surface, distance, track_cond, race_no, horse_name, sire_name, finish_pos, popularity, tansho_odds = row
        key = (race_date, race_no)
        if key not in races:
            races[key] = {'track_cond': track_cond, 'horses': []}
        races[key]['horses'].append({
            'horse_name': horse_name,
            'sire_name': sire_name,
            'finish_pos': finish_pos,
            'popularity': popularity,
            'tansho_odds': tansho_odds,
            'track_cond': track_cond,
        })

    print(f"レース数: {len(races)}件")

    # 馬場フィルター（良・重のみ）
    valid_races = {k: v for k, v in races.items() if v['track_cond'] in TRACK_CONDS}
    print(f"馬場フィルター後（良・重）: {len(valid_races)}件")

    # 人気閾値リスト
    thresholds = [7, 8, 9, 10, 11, 12]

    print("\n" + "=" * 70)
    print("【Step 1・2】人気帯別 回収率比較（福島ダ1700m × スタミナ系 × 良・重）")
    print("=" * 70)
    print(f"{'閾値（X番人気以上）':20s} {'ベット数':>8s} {'的中数':>8s} {'的中率':>8s} {'回収率':>10s} {'年間R数':>8s}")
    print("-" * 70)

    results = {}
    for thresh in thresholds:
        bets = 0
        hits = 0
        total_payout = 0.0
        for key, race_data in valid_races.items():
            for h in race_data['horses']:
                if h['sire_name'] in stamina_sires and h['popularity'] is not None and h['popularity'] >= thresh:
                    bets += 1
                    if h['finish_pos'] == 1:
                        hits += 1
                        total_payout += (h['tansho_odds'] or 0)

        win_rate = hits / bets * 100 if bets > 0 else 0
        recovery = total_payout * 100 / bets if bets > 0 else 0
        # 年数は2015〜2026の中でfukushimaの開催がある年（約10年）
        annual_r = bets / 10.0

        results[thresh] = {
            'bets': bets, 'hits': hits, 'win_rate': win_rate,
            'recovery': recovery, 'annual_r': annual_r,
            'total_payout': total_payout
        }
        marker = " ← 現行" if thresh == 10 else ""
        print(f"  {thresh}番人気以上{'':10s} {bets:>8d} {hits:>8d} {win_rate:>7.1f}% {recovery:>9.1f}% {annual_r:>7.1f}R{marker}")

    # 年別詳細（10番人気以上・現行 vs 最適候補）
    print("\n" + "=" * 70)
    print("【Step 3】年別安定性比較")
    print("=" * 70)

    def year_analysis(thresh):
        from collections import defaultdict
        yearly = defaultdict(lambda: {'bets': 0, 'hits': 0, 'payout': 0.0})
        for (race_date, race_no), race_data in valid_races.items():
            year = race_date[:4]
            for h in race_data['horses']:
                if h['sire_name'] in stamina_sires and h['popularity'] is not None and h['popularity'] >= thresh:
                    yearly[year]['bets'] += 1
                    if h['finish_pos'] == 1:
                        yearly[year]['hits'] += 1
                        yearly[year]['payout'] += (h['tansho_odds'] or 0)
        return yearly

    # 年別比較（7番・10番）
    thresholds_to_show = [7, 8, 9, 10, 12]
    print(f"\n{'年':6s}", end='')
    for t in thresholds_to_show:
        label = f" {t}人気以上 " if t != 10 else f" {t}人気(現行)"
        print(f"{label:>18s}", end='')
    print()
    print("-" * 96)

    all_yearly = {t: year_analysis(t) for t in thresholds_to_show}
    years = sorted({y for t in thresholds_to_show for y in all_yearly[t].keys()})

    black_count = {t: 0 for t in thresholds_to_show}
    for year in years:
        print(f"{year:6s}", end='')
        for t in thresholds_to_show:
            d = all_yearly[t].get(year, {'bets': 0, 'hits': 0, 'payout': 0.0})
            if d['bets'] > 0:
                rec = d['payout'] * 100 / d['bets']
                marker = "★" if rec >= 100 else " "
                print(f"  {marker}{d['bets']:>3d}R {rec:>6.1f}%  ", end='')
                if rec >= 100:
                    black_count[t] += 1
            else:
                print(f"  {'—':>14s}   ", end='')
        print()

    print("-" * 96)
    print(f"{'黒字年数':6s}", end='')
    for t in thresholds_to_show:
        cnt = black_count[t]
        total_years = len(years)
        print(f"  {cnt}/{total_years}年{'':10s}", end='')
    print()

    # Step 4: 馬場フィルターなし vs ありの比較（10番人気以上のみ）
    print("\n" + "=" * 70)
    print("【参考】馬場フィルターなし vs 良・重のみ（10番人気以上）")
    print("=" * 70)

    for use_filter in [False, True]:
        target_races = valid_races if use_filter else {k: v for k, v in races.items()}
        bets = hits = 0
        payout = 0.0
        for race_data in target_races.values():
            for h in race_data['horses']:
                if h['sire_name'] in stamina_sires and h['popularity'] is not None and h['popularity'] >= 10:
                    bets += 1
                    if h['finish_pos'] == 1:
                        hits += 1
                        payout += (h['tansho_odds'] or 0)
        wr = hits / bets * 100 if bets > 0 else 0
        rec = payout * 100 / bets if bets > 0 else 0
        label = "良・重のみ（フィルターあり）" if use_filter else "全馬場（フィルターなし）"
        print(f"  {label}: {bets}ベット / 的中率{wr:.1f}% / 回収率{rec:.1f}%")

    # Step 5: 最適閾値の特定
    print("\n" + "=" * 70)
    print("【Step 4】結論・最適閾値の提案")
    print("=" * 70)

    best = None
    best_score = -1
    for thresh, d in results.items():
        if d['bets'] < 50:
            continue
        # 回収率 × 黒字年率のスコア（どちらも重視）
        yearly_d = year_analysis(thresh)
        yr_list = list(yearly_d.values())
        black = sum(1 for y in yr_list if y['bets'] > 0 and y['payout'] * 100 / y['bets'] >= 100)
        total_y = sum(1 for y in yr_list if y['bets'] > 0)
        black_rate = black / total_y if total_y > 0 else 0
        score = d['recovery'] * 0.5 + black_rate * 100 * 0.5
        if score > best_score:
            best_score = score
            best = (thresh, d, black, total_y, black_rate)

    if best:
        thresh, d, black, total_y, black_rate = best
        print(f"\n  推奨閾値: {thresh}番人気以上")
        print(f"  回収率: {d['recovery']:.1f}%  的中率: {d['win_rate']:.1f}%")
        print(f"  安定性: {black}/{total_y}年（{black_rate*100:.0f}%）黒字")
        print(f"  年間購入頻度: {d['annual_r']:.1f}R")
        print(f"  現行（10番人気以上）との比較:")
        d10 = results[10]
        print(f"    回収率: {d10['recovery']:.1f}% → {d['recovery']:.1f}%（{d['recovery']-d10['recovery']:+.1f}%）")
        print(f"    年間R数: {d10['annual_r']:.1f}R → {d['annual_r']:.1f}R")

    print("\n  ※ 注意: 馬場フィルター（良・重のみ）は引き続き適用")
    print("  ※ tansho_odds は実数（例: 48.6倍）で格納。回収率 = SUM(的中時odds)×100/ベット数")


if __name__ == '__main__':
    run()
