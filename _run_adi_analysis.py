# -*- coding: utf-8 -*-
"""
ADI70-85帯 統計調査
B成分を実際の1番人気支持率から計算（B=60固定の近似を廃止）
"""
import sys, io, sqlite3, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'course_master.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# 全馬のオッズ・着順・馬場状態を取得
sql = '''
SELECT rr.race_date, rr.venue, rr.race_no,
       rr.horse_name, rr.horse_no, rr.popularity,
       rr.tansho_odds, rr.finish_pos, rr.track_cond,
       COUNT(*) OVER (PARTITION BY rr.race_date, rr.venue, rr.race_no) AS nheads
FROM race_results rr
WHERE rr.race_date >= '2024-01-01'
  AND rr.surface = '芝'
  AND rr.distance BETWEEN 1200 AND 2100
  AND CAST(rr.race_no AS INTEGER) >= 10
ORDER BY rr.race_date, rr.venue, rr.race_no, rr.popularity
'''
cur.execute(sql)
rows = cur.fetchall()
conn.close()

from collections import defaultdict
races = defaultdict(list)
for rd, venue, rno, hname, hno, pop, odds, fpos, track_cond, nheads in rows:
    if nheads < 10: continue
    races[(rd, venue, rno)].append({
        'name': hname, 'no': hno, 'pop': pop,
        'odds': odds or 0, 'finish': fpos,
        'track_cond': track_cond, 'nheads': nheads
    })

def calc_adi_full(horses):
    """実際の支持率からB成分を計算した正確版ADI"""
    odds_by_pop = {}
    for h in horses:
        if h['pop'] and h['odds'] and h['odds'] > 0:
            odds_by_pop[h['pop']] = h['odds']
    p1 = odds_by_pop.get(1, 0)
    p3 = odds_by_pop.get(3, 0)
    if p1 == 0 or p3 == 0: return None

    # A成分: オッズ分散
    A = min(100.0, (p1 / p3) * 100.0)

    # B成分: 1番人気支持率から計算
    total_inv = sum(1.0 / h['odds'] for h in horses if h['odds'] > 0)
    if total_inv <= 0: return None
    support = (1.0 / p1) / total_inv
    B = max(0.0, min(100.0, (0.50 - support) / 0.20 * 100.0))

    # C成分: 馬場状態
    cond = horses[0].get('track_cond', '良') if horses else '良'
    c_map = {'良': 20.0, '稍重': 50.0, '重': 80.0, '不良': 100.0}
    C = c_map.get(cond, 20.0)

    return 0.4 * A + 0.4 * B + 0.2 * C

# ADI帯別集計
bands = {'0-50': [], '50-60': [], '60-70': [], '70-80': [], '80-90': [], '90+': []}
for key, horses in races.items():
    adi = calc_adi_full(horses)
    if adi is None: continue
    fav = next((h for h in horses if h['pop'] == 1), None)
    winner = next((h for h in horses if h['finish'] == 1), None)
    if fav is None: continue
    win = 1 if fav['finish'] == 1 else 0
    payout = fav['odds'] if win else 0
    entry = {
        'adi': round(adi, 1), 'win': win, 'payout': payout,
        'key': str(key),
        'pop1_odds': fav['odds'],
        'winner_pop': winner['pop'] if winner else None,
    }
    if adi < 50:      bands['0-50'].append(entry)
    elif adi < 60:    bands['50-60'].append(entry)
    elif adi < 70:    bands['60-70'].append(entry)
    elif adi < 80:    bands['70-80'].append(entry)
    elif adi < 90:    bands['80-90'].append(entry)
    else:             bands['90+'].append(entry)

results = {}
print('ADI帯別 1番人気 勝率・回収率（2024-2026 Grade近似・B成分実計算版）')
print('='*65)
for band, entries in bands.items():
    n = len(entries)
    if n == 0: continue
    wins = sum(e['win'] for e in entries)
    roi = sum(e['payout'] for e in entries) * 100 / n
    wr = wins / n * 100
    print(f'ADI {band:10s}: {n:4d}R  勝率{wr:5.1f}%  回収率{roi:6.1f}%')
    results[band] = {'n': n, 'wins': wins, 'win_rate': round(wr, 1), 'roi': round(roi, 1)}

# ADI70-85帯の詳細
detail_70_85 = []
for key, horses in races.items():
    adi = calc_adi_full(horses)
    if adi is None or not (70 <= adi < 85): continue
    fav = next((h for h in horses if h['pop'] == 1), None)
    winner = next((h for h in horses if h['finish'] == 1), None)
    if fav is None: continue
    detail_70_85.append({
        'race_date': key[0], 'venue': key[1], 'race_no': key[2],
        'adi': round(adi, 1),
        'pop1_name': fav['name'], 'pop1_odds': fav['odds'],
        'pop1_finish': fav['finish'],
        'winner_name': winner['name'] if winner else '?',
        'winner_pop': winner['pop'] if winner else '?',
        'pop1_won': (fav['finish'] == 1),
    })

n70 = results.get('70-80', {})
n80 = results.get('80-90', {})
w70 = n70.get('win_rate', 0)
r70 = n70.get('roi', 0)

if w70 < 25:
    label = '「大波乱注意」ラベルは妥当（1番人気勝率25%未満）'
elif w70 < 30:
    label = '「波乱の可能性あり」程度が適切（1番人気勝率25-30%）'
else:
    label = '「大波乱注意」は過剰（1番人気勝率30%超）→ ラベル見直し推奨'

# 的中した場合の1番人気人気帯分布
pop1_won_detail = [e for e in detail_70_85 if e.get('pop1_won')]
pop1_lost_detail = [e for e in detail_70_85 if not e.get('pop1_won')]

print(f'\nADI70-85帯の詳細:')
print(f'  対象レース数: {len(detail_70_85)}R')
print(f'  1番人気が勝ったレース: {len(pop1_won_detail)}R')
print(f'  1番人気が負けたレース: {len(pop1_lost_detail)}R')
if pop1_lost_detail:
    avg_winner_pop = sum(e['winner_pop'] for e in pop1_lost_detail if isinstance(e['winner_pop'], int)) / max(1, len(pop1_lost_detail))
    print(f'  負けた場合の勝者平均人気: {avg_winner_pop:.1f}番人気')

output = {
    'generated': '2026-05-02',
    'method': 'B成分=実際の1番人気支持率から計算（B=60固定の近似を廃止）',
    'description': 'ADI70-85帯の1番人気勝率・回収率調査（2024-2026 Grade近似）',
    'band_summary': results,
    'detail_70_85_count': len(detail_70_85),
    'detail_70_85': sorted(detail_70_85, key=lambda x: x['race_date']),
    'conclusion': label,
    'label_assessment': {
        'current_label': '大波乱注意',
        'pop1_win_rate_70_80': w70,
        'pop1_roi_70_80': r70,
        'judgement': label,
    }
}

out_path = os.path.join(BASE_DIR, 'adi_analysis_70_85.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\nadi_analysis_70_85.json 保存完了')
print(f'ADI70-80: {n70.get("n",0)}R 勝率{w70}% 回収率{r70}%')
print(f'結論: {label}')
