# -*- coding: utf-8 -*-
import sys, io, sqlite3, pickle, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db = sqlite3.connect(os.path.join(BASE_DIR, 'course_master.db'))
cur = db.cursor()

print('='*60)
print('=== DB verify ===')
cur.execute("SELECT COUNT(*), MAX(race_date), MIN(race_date) FROM race_results")
total, latest, oldest = cur.fetchone()
print(f'  race_results : {total:,}件 / {oldest} ~ {latest}')

cur.execute("SELECT COUNT(*) FROM blood_map")
print(f'  blood_map    : {cur.fetchone()[0]:,}件')

for tbl in ['sire_profile','bms_profile','course_win_rate','jockey_stats','trainer_stats','speed_base']:
    cur.execute(f"SELECT COUNT(*) FROM {tbl}")
    print(f'  {tbl:<20}: {cur.fetchone()[0]:,}件')

cur.execute("SELECT race_date, venue, race_no, horse_name, finish_pos FROM race_results ORDER BY race_date DESC LIMIT 5")
print('\n  [最新レースサンプル]')
for r in cur.fetchall():
    print(f'    {r}')

db.close()

print('\n=== pkl verify ===')
pkl_path = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
with open(pkl_path,'rb') as f:
    state = pickle.load(f)

for k in ['sire_dist_stats','bms_dist_stats','blood_category_map','course_stats']:
    v = state.get(k,{})
    print(f'  {k:<24}: {len(v):,}件')

size = os.path.getsize(pkl_path) / 1024 / 1024
print(f'  pkl size: {size:.1f} MB')
print('='*60)
print('verify: OK')
