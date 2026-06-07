# -*- coding: utf-8 -*-
"""
course_win_rate テーブル更新スクリプト
race_results から venue×surface×distance×condition の勝率・複勝率を再集計し、
course_win_rate を更新する。
完了後に C:\coursemaster\results_log.txt へ結果を書き出す。
"""
import sqlite3
import os
import sys
import datetime

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'course_master.db')
LOG_PATH = os.path.join(BASE_DIR, 'results_log.txt')

MIN_RACE_COUNT = 30  # 統計的信頼性確保のための最低レース数

log_lines = []

def log(msg=''):
    print(msg)
    log_lines.append(msg)

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
log(f"=== course_win_rate 更新ログ ===")
log(f"実行日時  : {now}")
log(f"DB パス   : {DB_PATH}")
log(f"最低件数  : {MIN_RACE_COUNT}R以上のみ対象")
log()

errors = []

try:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur  = conn.cursor()

    # ------------------------------------------------------------------
    # Step 1: race_results から新しい集計を作成
    # ------------------------------------------------------------------
    log("--- Step 1: race_results から集計 ---")
    cur.execute("""
        SELECT
            venue,
            surface,
            distance,
            track_cond                                                    AS condition,
            COUNT(*)                                                      AS race_count,
            SUM(CASE WHEN finish_pos = 1 THEN 1 ELSE 0 END)              AS wins,
            SUM(CASE WHEN finish_pos <= 3 THEN 1 ELSE 0 END)             AS places
        FROM race_results
        WHERE finish_pos IS NOT NULL
          AND finish_pos > 0
          AND venue IS NOT NULL
          AND surface IS NOT NULL
          AND distance IS NOT NULL
          AND track_cond IS NOT NULL
        GROUP BY venue, surface, distance, track_cond
        HAVING COUNT(*) >= ?
    """, (MIN_RACE_COUNT,))
    new_rows = cur.fetchall()
    log(f"  集計結果: {len(new_rows):,} 件（{MIN_RACE_COUNT}R以上）")

    # ------------------------------------------------------------------
    # Step 2: 既存レコードを取得してキーセット作成
    # ------------------------------------------------------------------
    log()
    log("--- Step 2: 既存レコード確認 ---")
    cur.execute("SELECT venue, surface, distance, condition FROM course_win_rate")
    existing_keys = {(r['venue'], r['surface'], r['distance'], r['condition'])
                     for r in cur.fetchall()}
    cur.execute("SELECT COUNT(*) FROM course_win_rate")
    existing_count = cur.fetchone()[0]
    log(f"  既存レコード: {existing_count:,} 件")

    # ------------------------------------------------------------------
    # Step 3: UPDATE / INSERT を分類
    # ------------------------------------------------------------------
    new_keys   = {(r['venue'], r['surface'], r['distance'], r['condition'])
                  for r in new_rows}
    update_keys = existing_keys & new_keys       # 既存かつ新集計あり → UPDATE
    insert_keys = new_keys - existing_keys       # 新規組み合わせ → INSERT
    delete_keys = existing_keys - new_keys       # 新集計に現れない（30R未満） → DELETE

    log(f"  UPDATE対象 : {len(update_keys):,} 件")
    log(f"  INSERT対象 : {len(insert_keys):,} 件（新規組み合わせ）")
    log(f"  DELETE対象 : {len(delete_keys):,} 件（{MIN_RACE_COUNT}R未満に減少）")

    # ------------------------------------------------------------------
    # Step 4: トランザクション内で更新
    # ------------------------------------------------------------------
    log()
    log("--- Step 3: DB更新実行 ---")

    upd_count = 0
    ins_count = 0
    del_count = 0

    conn.execute("BEGIN")

    for r in new_rows:
        venue     = r['venue']
        surface   = r['surface']
        distance  = r['distance']
        condition = r['condition']
        rc        = r['race_count']
        wins      = r['wins']
        places    = r['places']
        win_rate  = round(wins  / rc * 100, 4) if rc else 0.0
        place_rate= round(places/ rc * 100, 4) if rc else 0.0

        key = (venue, surface, distance, condition)
        if key in update_keys:
            cur.execute("""
                UPDATE course_win_rate
                   SET race_count  = ?,
                       wins        = ?,
                       places      = ?,
                       win_rate    = ?,
                       place_rate  = ?
                 WHERE venue    = ?
                   AND surface  = ?
                   AND distance = ?
                   AND condition= ?
            """, (rc, wins, places, win_rate, place_rate,
                  venue, surface, distance, condition))
            upd_count += 1
        else:
            cur.execute("""
                INSERT INTO course_win_rate
                    (venue, surface, distance, condition,
                     race_count, wins, places, win_rate, place_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (venue, surface, distance, condition,
                  rc, wins, places, win_rate, place_rate))
            ins_count += 1

    # 30R未満になったレコードを削除
    for venue, surface, distance, condition in delete_keys:
        cur.execute("""
            DELETE FROM course_win_rate
             WHERE venue=? AND surface=? AND distance=? AND condition=?
        """, (venue, surface, distance, condition))
        del_count += 1

    conn.commit()
    log(f"  UPDATE完了 : {upd_count:,} 件")
    log(f"  INSERT完了 : {ins_count:,} 件")
    log(f"  DELETE完了 : {del_count:,} 件")

    # ------------------------------------------------------------------
    # Step 5: 更新後の件数確認
    # ------------------------------------------------------------------
    log()
    log("--- Step 4: 更新後確認 ---")
    cur.execute("SELECT COUNT(*) FROM course_win_rate")
    after_count = cur.fetchone()[0]
    log(f"  更新前レコード数 : {existing_count:,} 件")
    log(f"  更新後レコード数 : {after_count:,} 件")
    log(f"  純増分           : {after_count - existing_count:+,} 件")

    # 更新後サンプル（WIN率上位5件）
    cur.execute("""
        SELECT venue, surface, distance, condition, race_count, win_rate, place_rate
        FROM course_win_rate
        ORDER BY race_count DESC
        LIMIT 5
    """)
    log()
    log("  【参考】レース数上位5件:")
    log(f"  {'会場':<4} {'面':<2} {'距離':>5} {'馬場':<2} {'R数':>7} {'勝率':>7} {'複勝率':>8}")
    log(f"  {'─'*44}")
    for r in cur.fetchall():
        log(f"  {r[0]:<4} {r[1]:<2} {r[2]:>5}m {r[3]:<2} "
            f"{r[4]:>7,} {r[5]:>6.2f}% {r[6]:>7.2f}%")

    conn.close()

except Exception as e:
    errors.append(str(e))
    log(f"\n[ERROR] {e}")
    import traceback
    tb = traceback.format_exc()
    log(tb)

# ------------------------------------------------------------------
# ログ書き出し
# ------------------------------------------------------------------
log()
if errors:
    log(f"エラー件数: {len(errors)} 件")
    for i, e in enumerate(errors, 1):
        log(f"  [{i}] {e}")
else:
    log("エラー: なし")

log()
log("=== 完了 ===")

with open(LOG_PATH, 'w', encoding='utf-8') as f:
    f.write('\n'.join(log_lines) + '\n')

print(f"\nログ書き出し完了: {LOG_PATH}")
