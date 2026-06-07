# -*- coding: utf-8 -*-
"""
db_update_0421.py
2026-04-21 DB統計マスター全再集計スクリプト
  - race_resultsは既にStep3でINSERT済み
  - sire_profile / bms_profile / course_win_rate / jockey_stats / trainer_stats / speed_base を再集計
"""
import os, sys, io, json, csv, sqlite3
from datetime import datetime, date
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')
RACE_DIR = os.path.join(BASE_DIR, 'data', 'race')

ALL_RACE_CSVS = [
    os.path.join(RACE_DIR, '2015_2016結果.csv'),
    os.path.join(RACE_DIR, '2017_2018結果.csv'),
    os.path.join(RACE_DIR, '2019_2020結果.csv'),
    os.path.join(RACE_DIR, '2021_2023結果.csv'),
    os.path.join(RACE_DIR, '2024_2026結果.csv'),
    os.path.join(RACE_DIR, '2026結果.csv'),
    os.path.join(RACE_DIR, '202602280331結果.csv'),
    os.path.join(RACE_DIR, '結果202603070405.csv'),
    os.path.join(RACE_DIR, '結果202604110419.csv'),
]

TRACK_COND_MAP = {'良': '良', '稍重': '稍', '重': '重', '不良': '不'}
SURFACE_MAP    = {'芝': '芝', 'ダート': 'ダ', 'ダ': 'ダ'}

def dist_band(d):
    if d <= 1400: return 'sprint'
    if d <= 1800: return 'mile'
    if d <= 2100: return 'middle'
    return 'long'

def step4a_sire_profile(conn):
    print("\n" + "="*60)
    print("Step 4a: sire_profile 再集計（race_resultsベース）")
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT sire_name, surface, distance, finish_pos
        FROM race_results
        WHERE sire_name IS NOT NULL AND finish_pos IS NOT NULL AND finish_pos > 0
    """).fetchall()

    sire_data = defaultdict(lambda: defaultdict(lambda: {'n': 0, 'wins': 0}))
    for sire, surface, distance, fp in rows:
        if not surface or not distance:
            continue
        db = dist_band(distance)
        sire_data[sire][surface]['n']    += 1
        sire_data[sire][surface]['wins'] += (1 if fp == 1 else 0)
        sire_data[sire][f'dist_{db}']['n']    += 1
        sire_data[sire][f'dist_{db}']['wins'] += (1 if fp == 1 else 0)
        sire_data[sire][f'{surface}_{db}']['n']    += 1
        sire_data[sire][f'{surface}_{db}']['wins'] += (1 if fp == 1 else 0)

    MIN_RACES = 30
    cur.execute("DELETE FROM sire_profile")

    upsert_rows = []
    for sire, stats in sire_data.items():
        turf = stats.get('芝', {'n': 0, 'wins': 0})
        dirt = stats.get('ダ', {'n': 0, 'wins': 0})
        turf_wr = round(turf['wins'] / turf['n'] * 100, 2) if turf['n'] >= MIN_RACES else None
        dirt_wr = round(dirt['wins'] / dirt['n'] * 100, 2) if dirt['n'] >= MIN_RACES else None

        dist_json = {}
        for band in ['sprint', 'mile', 'middle', 'long']:
            d = stats.get(f'dist_{band}', {'n': 0, 'wins': 0})
            if d['n'] >= MIN_RACES:
                dist_json[band] = {'wr': round(d['wins'] / d['n'] * 100, 2), 'n': d['n']}

        surface_dist = {}
        for surf in ['芝', 'ダ']:
            for band in ['sprint', 'mile', 'middle', 'long']:
                sd = stats.get(f'{surf}_{band}', {'n': 0, 'wins': 0})
                if sd['n'] >= MIN_RACES:
                    surface_dist[f'{surf}_{band}'] = {'wr': round(sd['wins'] / sd['n'] * 100, 2), 'n': sd['n']}

        total_n = turf['n'] + dirt['n']
        if total_n < MIN_RACES:
            continue

        data = {}
        if turf['n'] > 0: data['tw'] = turf_wr or 0; data['tn'] = turf['n']
        if dirt['n'] > 0: data['dw'] = dirt_wr or 0; data['dn'] = dirt['n']
        if dist_json: data['dist'] = dist_json
        if surface_dist: data['surface_dist'] = surface_dist

        upsert_rows.append((sire, turf_wr or 0, dirt_wr or 0, json.dumps(data, ensure_ascii=False)))

    cur.executemany(
        "INSERT INTO sire_profile (name, turf_wr, dirt_wr, data_json) VALUES (?, ?, ?, ?)",
        upsert_rows
    )
    conn.commit()
    print(f"  sire_profile: {len(upsert_rows):,}件")
    return len(upsert_rows)

def step4b_bms_profile(conn):
    print("\n" + "="*60)
    print("Step 4b: bms_profile 再集計（race_results × blood_map）")
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT bm.bms, rr.surface, rr.distance, rr.finish_pos
        FROM race_results rr
        JOIN blood_map bm ON rr.horse_name = bm.name
        WHERE bm.bms IS NOT NULL AND rr.finish_pos IS NOT NULL AND rr.finish_pos > 0
    """).fetchall()

    bms_data = defaultdict(lambda: defaultdict(lambda: {'n': 0, 'wins': 0}))
    for bms, surface, distance, fp in rows:
        if not surface or not distance:
            continue
        db = dist_band(distance)
        bms_data[bms][surface]['n']    += 1
        bms_data[bms][surface]['wins'] += (1 if fp == 1 else 0)
        bms_data[bms][f'dist_{db}']['n']    += 1
        bms_data[bms][f'dist_{db}']['wins'] += (1 if fp == 1 else 0)

    MIN_RACES = 30
    cur.execute("DELETE FROM bms_profile")

    upsert_rows = []
    for bms, stats in bms_data.items():
        turf = stats.get('芝', {'n': 0, 'wins': 0})
        dirt = stats.get('ダ', {'n': 0, 'wins': 0})
        turf_wr = round(turf['wins'] / turf['n'] * 100, 2) if turf['n'] >= MIN_RACES else None
        dirt_wr = round(dirt['wins'] / dirt['n'] * 100, 2) if dirt['n'] >= MIN_RACES else None

        dist_json = {}
        for band in ['sprint', 'mile', 'middle', 'long']:
            d = stats.get(f'dist_{band}', {'n': 0, 'wins': 0})
            if d['n'] >= MIN_RACES:
                dist_json[band] = {'wr': round(d['wins'] / d['n'] * 100, 2), 'n': d['n']}

        if (turf['n'] + dirt['n']) < MIN_RACES:
            continue

        data = {}
        if turf['n'] > 0: data['tw'] = turf_wr or 0; data['tn'] = turf['n']
        if dirt['n'] > 0: data['dw'] = dirt_wr or 0; data['dn'] = dirt['n']
        if dist_json: data['dist'] = dist_json

        upsert_rows.append((bms, turf_wr or 0, dirt_wr or 0, json.dumps(data, ensure_ascii=False)))

    cur.executemany(
        "INSERT INTO bms_profile (name, turf_wr, dirt_wr, data_json) VALUES (?, ?, ?, ?)",
        upsert_rows
    )
    conn.commit()
    print(f"  bms_profile: {len(upsert_rows):,}件")
    return len(upsert_rows)

def step4c_course_win_rate(conn):
    print("\n" + "="*60)
    print("Step 4c: course_win_rate 再集計（race_resultsベース）")
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT venue, surface, distance, track_cond, finish_pos
        FROM race_results
        WHERE finish_pos IS NOT NULL AND finish_pos > 0
    """).fetchall()

    stats = defaultdict(lambda: {'n': 0, 'wins': 0, 'places': 0})
    for venue, surface, distance, cond, fp in rows:
        if not all([venue, surface, distance, cond]):
            continue
        k = (venue, surface, distance, cond)
        stats[k]['n']      += 1
        stats[k]['wins']   += (1 if fp == 1 else 0)
        stats[k]['places'] += (1 if fp <= 3 else 0)

    MIN_RACES = 30
    cur.execute("DELETE FROM course_win_rate")

    upsert_rows = []
    for (venue, surface, distance, cond), s in stats.items():
        if s['n'] < MIN_RACES:
            continue
        wr = round(s['wins'] / s['n'] * 100, 2)
        pr = round(s['places'] / s['n'] * 100, 2)
        upsert_rows.append((venue, surface, distance, cond, s['n'], s['wins'], s['places'], wr, pr))

    cur.executemany("""
        INSERT INTO course_win_rate
            (venue, surface, distance, condition, race_count, wins, places, win_rate, place_rate)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, upsert_rows)
    conn.commit()
    print(f"  course_win_rate: {len(upsert_rows):,}件")
    return len(upsert_rows)

def step4d_jockey_stats(conn):
    print("\n" + "="*60)
    print("Step 4d: jockey_stats 再集計（全CSV）")

    jdata = defaultdict(list)
    for csv_path in ALL_RACE_CSVS:
        if not os.path.exists(csv_path):
            print(f"  [SKIP] {os.path.basename(csv_path)} not found")
            continue
        with open(csv_path, encoding='cp932', newline='') as f:
            reader = csv.reader(f)
            next(reader)
            for raw in reader:
                try:
                    jockey = raw[16].strip()
                    fp_str = raw[20].strip()
                    if not jockey or not fp_str.isdigit():
                        continue
                    fp       = int(fp_str)
                    surface  = SURFACE_MAP.get(raw[9].strip(), raw[9].strip())
                    distance = int(raw[11]) if raw[11].strip() else None
                    venue    = raw[4].strip()
                    cond     = TRACK_COND_MAP.get(raw[12].strip(), raw[12].strip())
                    year     = int(raw[0]) + 2000
                    month    = int(raw[1])
                    day      = int(raw[2])
                    rd = date(year, month, day)
                    if distance:
                        jdata[jockey].append((surface, distance, venue, cond, fp, rd))
                except Exception:
                    pass

    MIN_RACES = 50
    cur = conn.cursor()
    cur.execute("DELETE FROM jockey_stats")

    cutoff = date(2025, 4, 19)
    upsert_rows = []
    for jockey, records in jdata.items():
        n = len(records)
        if n < MIN_RACES:
            continue
        wins = sum(1 for r in records if r[4] == 1)
        wr   = round(wins / n * 100, 2)
        recent = [r for r in records if r[5] >= cutoff]
        rn  = len(recent)
        rwr = round(sum(1 for r in recent if r[4] == 1) / rn * 100, 2) if rn > 0 else 0

        v_stats = defaultdict(lambda: {'n': 0, 'wins': 0})
        s_stats = defaultdict(lambda: {'n': 0, 'wins': 0})
        d_stats = defaultdict(lambda: {'n': 0, 'wins': 0})
        b_stats = defaultdict(lambda: {'n': 0, 'wins': 0})
        for surface, distance, venue, cond, fp, rd in records:
            v_stats[venue]['n'] += 1; v_stats[venue]['wins'] += (1 if fp == 1 else 0)
            s_stats[surface]['n'] += 1; s_stats[surface]['wins'] += (1 if fp == 1 else 0)
            db = dist_band(distance)
            d_stats[db]['n'] += 1; d_stats[db]['wins'] += (1 if fp == 1 else 0)
            b_stats[cond]['n'] += 1; b_stats[cond]['wins'] += (1 if fp == 1 else 0)

        data_json = json.dumps({
            'wr': wr, 'rwr': rwr,
            'venue':   {v: {'wr': round(s['wins']/s['n']*100,2),'n':s['n']} for v,s in v_stats.items() if s['n']>=20},
            'surface': {s: {'wr': round(ss['wins']/ss['n']*100,2),'n':ss['n']} for s,ss in s_stats.items() if ss['n']>=20},
            'dist':    {d: {'wr': round(ds['wins']/ds['n']*100,2),'n':ds['n']} for d,ds in d_stats.items() if ds['n']>=20},
            'baba':    {b: {'wr': round(bs['wins']/bs['n']*100,2),'n':bs['n']} for b,bs in b_stats.items() if bs['n']>=20},
        }, ensure_ascii=False)
        upsert_rows.append((jockey, wr, rwr, data_json))

    cur.executemany(
        "INSERT INTO jockey_stats (name, win_rate, recent_win_rate, data_json) VALUES (?, ?, ?, ?)",
        upsert_rows
    )
    conn.commit()
    print(f"  jockey_stats: {len(upsert_rows):,}件")
    return len(upsert_rows)

def step4e_trainer_stats(conn):
    print("\n" + "="*60)
    print("Step 4e: trainer_stats 再集計（全CSV）")

    tdata = defaultdict(list)
    for csv_path in ALL_RACE_CSVS:
        if not os.path.exists(csv_path):
            continue
        with open(csv_path, encoding='cp932', newline='') as f:
            reader = csv.reader(f)
            next(reader)
            for raw in reader:
                try:
                    trainer = raw[34].strip() if len(raw) > 34 else ''
                    fp_str  = raw[20].strip()
                    if not trainer or not fp_str.isdigit():
                        continue
                    fp       = int(fp_str)
                    surface  = SURFACE_MAP.get(raw[9].strip(), raw[9].strip())
                    distance = int(raw[11]) if raw[11].strip() else None
                    venue    = raw[4].strip()
                    year     = int(raw[0]) + 2000
                    month    = int(raw[1])
                    day      = int(raw[2])
                    rd = date(year, month, day)
                    if distance:
                        tdata[trainer].append((surface, distance, venue, '', fp, rd))
                except Exception:
                    pass

    MIN_RACES = 50
    cur = conn.cursor()
    cur.execute("DELETE FROM trainer_stats")

    cutoff = date(2025, 4, 19)
    upsert_rows = []
    for trainer, records in tdata.items():
        n = len(records)
        if n < MIN_RACES:
            continue
        wins = sum(1 for r in records if r[4] == 1)
        wr   = round(wins / n * 100, 2)
        recent = [r for r in records if r[5] >= cutoff]
        rn  = len(recent)
        rwr = round(sum(1 for r in recent if r[4] == 1) / rn * 100, 2) if rn > 0 else 0

        v_stats = defaultdict(lambda: {'n': 0, 'wins': 0})
        s_stats = defaultdict(lambda: {'n': 0, 'wins': 0})
        d_stats = defaultdict(lambda: {'n': 0, 'wins': 0})
        for surface, distance, venue, cond, fp, rd in records:
            v_stats[venue]['n'] += 1; v_stats[venue]['wins'] += (1 if fp == 1 else 0)
            s_stats[surface]['n'] += 1; s_stats[surface]['wins'] += (1 if fp == 1 else 0)
            db = dist_band(distance)
            d_stats[db]['n'] += 1; d_stats[db]['wins'] += (1 if fp == 1 else 0)

        data_json = json.dumps({
            'wr': wr, 'rwr': rwr,
            'venue':   {v: {'wr': round(s['wins']/s['n']*100,2),'n':s['n']} for v,s in v_stats.items() if s['n']>=20},
            'surface': {s: {'wr': round(ss['wins']/ss['n']*100,2),'n':ss['n']} for s,ss in s_stats.items() if ss['n']>=20},
            'dist':    {d: {'wr': round(ds['wins']/ds['n']*100,2),'n':ds['n']} for d,ds in d_stats.items() if ds['n']>=20},
        }, ensure_ascii=False)
        upsert_rows.append((trainer, wr, rwr, data_json))

    cur.executemany(
        "INSERT INTO trainer_stats (name, win_rate, recent_win_rate, data_json) VALUES (?, ?, ?, ?)",
        upsert_rows
    )
    conn.commit()
    print(f"  trainer_stats: {len(upsert_rows):,}件")
    return len(upsert_rows)

def step4f_speed_base(conn):
    print("\n" + "="*60)
    print("Step 4f: speed_base 再集計（全CSV）")

    speed_data = defaultdict(list)
    for csv_path in ALL_RACE_CSVS:
        if not os.path.exists(csv_path):
            continue
        with open(csv_path, encoding='cp932', newline='') as f:
            reader = csv.reader(f)
            next(reader)
            for raw in reader:
                try:
                    venue   = raw[4].strip()
                    surface = SURFACE_MAP.get(raw[9].strip(), raw[9].strip())
                    dist_s  = raw[11].strip()
                    cond    = TRACK_COND_MAP.get(raw[12].strip(), raw[12].strip())
                    time_s  = raw[25].strip()
                    if not all([venue, surface, dist_s, cond, time_s]):
                        continue
                    distance  = int(dist_s)
                    race_time = float(time_s)
                    if race_time <= 0:
                        continue
                    speed_data[f"{venue}_{surface}_{distance}_{cond}"].append(race_time)
                except Exception:
                    pass

    import statistics as stat_lib
    MIN_N = 30
    cur = conn.cursor()
    cur.execute("DELETE FROM speed_base")

    upsert_rows = []
    for key, times in speed_data.items():
        if len(times) < MIN_N:
            continue
        mean_t = round(stat_lib.mean(times), 3)
        std_t  = round(stat_lib.stdev(times), 3) if len(times) > 1 else 0
        upsert_rows.append((key, mean_t, std_t, len(times)))

    cur.executemany(
        "INSERT INTO speed_base (cond_key, mean_time, std_time, n) VALUES (?, ?, ?, ?)",
        upsert_rows
    )
    conn.commit()
    print(f"  speed_base: {len(upsert_rows):,}件")
    return len(upsert_rows)

def main():
    print("=" * 60)
    print("db_update_0421.py 開始（統計マスター全再集計）")
    print(f"  DB: {DB_PATH}")
    print(f"  CSV数: {len(ALL_RACE_CSVS)}ファイル")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL')

    sire_cnt    = step4a_sire_profile(conn)
    bms_cnt     = step4b_bms_profile(conn)
    cwr_cnt     = step4c_course_win_rate(conn)
    jockey_cnt  = step4d_jockey_stats(conn)
    trainer_cnt = step4e_trainer_stats(conn)
    speed_cnt   = step4f_speed_base(conn)

    conn.close()

    print("\n" + "=" * 60)
    print("【統計再集計 完了報告】")
    print(f"  sire_profile  : {sire_cnt:,}件")
    print(f"  bms_profile   : {bms_cnt:,}件")
    print(f"  course_win_rate: {cwr_cnt:,}件")
    print(f"  jockey_stats  : {jockey_cnt:,}件")
    print(f"  trainer_stats : {trainer_cnt:,}件")
    print(f"  speed_base    : {speed_cnt:,}件")
    print("=" * 60)

if __name__ == '__main__':
    main()
