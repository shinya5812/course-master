# -*- coding: utf-8 -*-
"""
update_race_results.py
新CSVファイルを race_results テーブルに追加インポートするスクリプト
"""
import sqlite3
import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')

# 追加インポート対象CSVファイル
NEW_CSV_FILES = [
    os.path.join(BASE_DIR, '2026結果.csv'),
    os.path.join(BASE_DIR, '202602280331結果.csv'),
]

# 馬場状態マッピング（CSV表記 → DB表記）
TRACK_COND_MAP = {'良': '良', '稍重': '稍', '重': '重', '不良': '不'}

# 芝ダマッピング（CSV表記 → DB表記）
SURFACE_MAP = {'芝': '芝', 'ダート': 'ダ', 'ダ': 'ダ'}

def parse_row(row):
    """CSVの1行をrace_resultsのカラムにマッピング"""
    try:
        year  = int(row[0]) + 2000
        month = int(row[1])
        day   = int(row[2])
        race_date = f"{year}-{month:02d}-{day:02d}"
        venue     = row[4].strip()
        surface   = SURFACE_MAP.get(row[9].strip(), row[9].strip())
        distance  = int(row[11]) if row[11].strip() else None
        track_cond= TRACK_COND_MAP.get(row[12].strip(), row[12].strip())
        race_no   = int(row[6]) if row[6].strip() else None
        horse_name= row[13].strip()
        finish_pos= int(row[20]) if row[20].strip().isdigit() else None
        popularity= int(row[24]) if row[24].strip().isdigit() else None
        horse_no  = int(row[19]) if row[19].strip().isdigit() else None
        odds_str  = row[48].strip() if len(row) > 48 else ''
        tansho_odds = float(odds_str) if odds_str and odds_str != '0' else None
        return (race_date, venue, surface, distance, track_cond,
                race_no, horse_name, finish_pos, popularity, horse_no, tansho_odds)
    except Exception:
        return None

def main():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # blood_map を辞書化（馬名 → 父馬名）
    print("blood_map 読み込み中...")
    cur.execute("SELECT TRIM(name), sire FROM blood_map")
    blood_map = {row[0]: row[1] for row in cur.fetchall()}
    print(f"  blood_map: {len(blood_map):,} 件")

    # 既存のレースキーセット（重複チェック用）
    print("既存レースキー取得中...")
    cur.execute("SELECT race_date, venue, race_no, horse_no FROM race_results")
    existing_keys = set(cur.fetchall())
    print(f"  既存レコード数: {len(existing_keys):,} 件")

    total_inserted = 0
    total_skipped  = 0

    for csv_path in NEW_CSV_FILES:
        if not os.path.exists(csv_path):
            print(f"[SKIP] ファイルなし: {csv_path}")
            continue

        print(f"\n処理中: {os.path.basename(csv_path)}")
        inserted = 0
        skipped  = 0

        with open(csv_path, encoding='cp932') as f:
            reader = csv.reader(f)
            next(reader)  # ヘッダースキップ
            rows_buf = []
            for raw in reader:
                parsed = parse_row(raw)
                if parsed is None:
                    skipped += 1
                    continue
                (race_date, venue, surface, distance, track_cond,
                 race_no, horse_name, finish_pos, popularity, horse_no, tansho_odds) = parsed

                # 重複チェック
                key = (race_date, venue, race_no, horse_no)
                if key in existing_keys:
                    skipped += 1
                    continue

                sire_name = blood_map.get(horse_name)
                rows_buf.append((race_date, venue, surface, distance, track_cond,
                                 race_no, horse_name, sire_name, finish_pos,
                                 popularity, horse_no, tansho_odds))
                existing_keys.add(key)
                inserted += 1

        if rows_buf:
            cur.executemany("""
                INSERT INTO race_results
                    (race_date, venue, surface, distance, track_cond,
                     race_no, horse_name, sire_name, finish_pos,
                     popularity, horse_no, tansho_odds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows_buf)
            conn.commit()

        print(f"  挿入: {inserted:,} 件 / スキップ: {skipped:,} 件")
        total_inserted += inserted
        total_skipped  += skipped

    # 最終確認
    cur.execute("SELECT COUNT(*), MAX(race_date) FROM race_results")
    total, latest = cur.fetchone()
    conn.close()

    print(f"\n=== 完了 ===")
    print(f"  総挿入件数  : {total_inserted:,} 件")
    print(f"  スキップ件数: {total_skipped:,} 件")
    print(f"  DB総件数    : {total:,} 件")
    print(f"  最新レース日: {latest}")

if __name__ == '__main__':
    main()
