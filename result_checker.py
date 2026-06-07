# -*- coding: utf-8 -*-
"""
result_checker.py - 購入候補 当日結果照合スクリプト（Playwright MCP版）

【設計思想】
  ブラウザ自動操作は Claude（Playwright MCP）が担当し、
  このスクリプトは判定・表示・DB記録に専念する。

  購入候補は candidates_YYYYMMDD.json から自動読み込みする。
  朝の条件フィルター実行時に --save モードで候補を保存し、
  レース後に引数なしで起動すれば自動的に照合・DB記録まで行う。

【使い方】

  # 【朝】条件フィルター結果を保存（Claude が実行）
  python result_checker.py --save '{"venue":"中京","candidates":[[8,10,"馬名","D",15.0]]}'

  # 【レース後】Playwright MCP で取得した結果を渡して照合
  python result_checker.py --results '{"8":[12,"チムグクル",3.1],"11":[18,"アイサンサン",27.6]}'

  # 【レース後】手動入力モード
  python result_checker.py --manual

  # 【レース後】自動取得モード（playwright_retry 経由で競馬ラボから取得）
  python result_checker.py --auto --venue 中京 --race 8

【candidates_YYYYMMDD.json の形式】
  {
    "date":       "2026-03-28",
    "venue":      "中京",
    "candidates": [
      [レース番号, 馬番, "馬名", "条件種別", 想定単勝オッズ],
      ...
    ]
  }
  ※ 想定オッズが不明な場合は 0.0 と入力する。
  ※ 購入候補がない場合は "candidates": [] とする。
"""

import os
import sys
import re
import json
import sqlite3
from datetime import date

# Windows環境での日本語出力設定
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SHARED_DIR = os.path.join(BASE_DIR, '..', 'shared_skills')
db_path    = os.path.join(BASE_DIR, 'course_master.db')

if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

# 競馬ラボの会場コード（--auto モードで使用）
KEIBALAB_VENUE_CODE = {
    '札幌': '01', '函館': '02', '福島': '03', '新潟': '04',
    '東京': '05', '中山': '06', '中京': '07', '京都': '08',
    '阪神': '09', '小倉': '10',
}

# BET_UNIT = 100  # 1頭あたり単勝ベット金額（円）- 収支表示廃止のため参照のみ


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 購入候補ファイルの保存・読み込み
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def candidates_filepath(race_date):
    """candidates_YYYYMMDD.json のフルパスを返す。"""
    filename = f'candidates_{race_date.replace("-", "")}.json'
    return os.path.join(BASE_DIR, filename)


def save_candidates(data_json):
    """
    --save 引数の JSON を candidates_YYYYMMDD.json に保存する。
    JSON形式:
      {"venue": "中京", "candidates": [[R, 馬番, "馬名", "条件", オッズ], ...]}
    date は自動付与（実行日）。
    """
    try:
        data = json.loads(data_json)
    except Exception as e:
        print(f'[エラー] --save の JSON 解析に失敗しました: {e}')
        sys.exit(1)

    race_date = str(date.today())
    data['date'] = race_date

    # candidates が未指定の場合は空リスト
    if 'candidates' not in data:
        data['candidates'] = []

    filepath = candidates_filepath(race_date)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    cands = data['candidates']
    print(f'購入候補を保存しました: {os.path.basename(filepath)}')
    print(f'  会場: {data.get("venue", "不明")}  候補数: {len(cands)}頭')
    for item in cands:
        r, n, name, cond, odds = item
        odds_str = f'{odds}倍' if odds > 0 else '想定オッズ未確認'
        print(f'  {r}R 馬番{n:2d}  {name:<20}  条件{cond}  {odds_str}')


def load_candidates():
    """
    当日の candidates_YYYYMMDD.json を読み込み、
    (CANDIDATES, VENUE, RACE_DATE) を返す。
    ファイルが存在しない場合はエラー終了。
    """
    race_date = str(date.today())
    filepath  = candidates_filepath(race_date)

    if not os.path.exists(filepath):
        print(f'[エラー] 購入候補ファイルが見つかりません: {os.path.basename(filepath)}')
        print('先に条件フィルターを実行して購入候補を保存してください。')
        print(f'  例: python result_checker.py --save \'{{"venue":"中京","candidates":[]}}\'')
        sys.exit(1)

    with open(filepath, encoding='utf-8') as f:
        data = json.load(f)

    candidates = [tuple(c) for c in data.get('candidates', [])]
    venue      = data.get('venue', '不明')
    saved_date = data.get('date', race_date)

    return candidates, venue, saved_date


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DB初期化（condition_bet_history テーブルを自動作成）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def ensure_table(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS condition_bet_history (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            race_date      TEXT,
            venue          TEXT,
            race_no        INTEGER,
            horse_no       INTEGER,
            horse_name     TEXT,
            condition_type TEXT,
            tansho_odds    REAL,
            finish_pos     INTEGER,
            result         TEXT,
            notes          TEXT
        )
    ''')
    conn.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# モード 0: 自動取得（playwright_retry 経由で競馬ラボから取得）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_results_auto(venue: str, race_nos: list[int]) -> dict:
    """
    playwright_retry を使って競馬ラボからレース結果を取得する。

    Parameters
    ----------
    venue     : 開催会場名（例: "中京"）
    race_nos  : 取得対象のレース番号リスト

    Returns
    -------
    dict: {race_no: (winner_name, winner_horse_no, tansho_odds)}
    """
    try:
        from playwright_retry import fetch_with_retry
    except ImportError:
        print('[エラー] shared_skills/playwright_retry.py が見つかりません。')
        print(f'  確認パス: {SHARED_DIR}')
        return {}

    venue_code = KEIBALAB_VENUE_CODE.get(venue)
    if not venue_code:
        print(f'[エラー] 未対応の会場です: {venue}')
        return {}

    race_date_str = str(date.today()).replace('-', '')
    results = {}

    for race_no in sorted(race_nos):
        url = (
            f'https://www.keibalab.jp/db/race/'
            f'{race_date_str}{venue_code}{race_no:02d}/raceresult.html'
        )
        cache_path = os.path.join(
            BASE_DIR, 'cache',
            f'result_{race_date_str}_{venue_code}{race_no:02d}.json'
        )
        print(f'  [{race_no}R] 取得中: {url}')
        try:
            fetched = fetch_with_retry(url, cache_path=cache_path, wait_js=False)
            html    = fetched['html']
            source  = fetched['source']
            print(f'    → ソース: {source}')

            # 1着馬の抽出（競馬ラボの着順テーブルから）
            # 1着行: <td>1</td>... <td>馬名</td>... <td>単勝払戻</td>
            winner = _parse_keibalab_result(html, race_no)
            if winner:
                results[race_no] = winner
                print(f'    → 1着: 馬番{winner[1]} {winner[0]}（{winner[2]}倍）')
            else:
                print(f'    → 1着馬の解析に失敗しました')

        except RuntimeError as e:
            print(f'  [{race_no}R] 取得失敗: {e}')

    return results


def _parse_keibalab_result(html: str, race_no: int) -> tuple | None:
    """
    競馬ラボのレース結果HTMLから1着馬の (馬名, 馬番, 単勝オッズ) を抽出する。
    解析失敗時は None を返す。
    """
    try:
        # 1着行のパターン（着順=1の行を探す）
        # <td ...>1</td> を起点に同行の馬番・馬名・単勝払戻を取得
        pattern = (
            r'<td[^>]*>\s*1\s*</td>'         # 着順1
            r'(?:.*?<td[^>]*>(\d+)</td>)'    # 馬番
            r'(?:.*?<td[^>]*>'
            r'<a[^>]*>([^<]+)</a>'           # 馬名（リンク内）
            r'</td>)'
            r'(?:.*?<td[^>]*>([\d.]+)</td>)' # 単勝払戻（倍）
        )
        m = re.search(pattern, html, re.DOTALL)
        if m:
            horse_no   = int(m.group(1))
            horse_name = m.group(2).strip()
            odds       = float(m.group(3))
            return (horse_name, horse_no, odds)
    except Exception:
        pass
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# モード 1: Playwright MCP から受け取った結果を解析
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_results_from_args(results_json):
    """
    --results 引数の JSON をパースする。
    JSON形式: {"レース番号": [馬番, 馬名, 単勝倍率], ...}
    例:  '{"8": [12, "チムグクル", 3.1], "11": [18, "アイサンサン", 27.6]}'
    戻り値: {race_no(int): (winner_name, winner_horse_no, tansho_odds)}
    """
    try:
        raw = json.loads(results_json)
        results = {}
        for k, v in raw.items():
            race_no    = int(k)
            horse_no   = int(v[0])
            horse_name = str(v[1])
            odds       = float(v[2])
            results[race_no] = (horse_name, horse_no, odds)
        return results
    except Exception as e:
        print(f'[エラー] --results の解析に失敗しました: {e}')
        print('  形式例: \'{"8":[12,"チムグクル",3.1],"11":[18,"アイサンサン",27.6]}\'')
        sys.exit(1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# モード 2: 手動入力
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fetch_results_manual(race_nos):
    """
    各レースの1着情報をユーザーが手動入力する。
    戻り値: {race_no: (winner_name, winner_horse_no, tansho_odds)}
    """
    results = {}
    print('\n--- 手動入力モード ---')
    print('各レースの1着馬情報を入力してください。（Enter のみでスキップ）')

    for race_no in sorted(race_nos):
        print(f'\n【{race_no}R】')
        name = input('  1着 馬名: ').strip()
        if not name:
            continue
        horse_no_str = input('  1着 馬番 (数字): ').strip()
        odds_str     = input('  単勝払戻倍率 (例: 27.6): ').strip()
        horse_no = int(horse_no_str) if horse_no_str.isdigit() else 0
        try:
            odds = float(odds_str)
        except ValueError:
            odds = 0.0
        results[race_no] = (name, horse_no, odds)

    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 的中判定 & 結果表示 & DB記録
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def judge_and_record(conn, candidates, venue, race_date, race_results):
    """
    race_results: {race_no: (winner_name, winner_horse_no, actual_odds)}
    candidates と照合して的中/不的中を判定・表示・DB記録する。
    収支金額は表示しない。着順・1着馬・的中可否のみを記録する。
    """
    print('\n' + '=' * 60)
    print(f'  結果照合  {race_date}  {venue}')
    print('=' * 60)

    hit_count = 0

    for race_no, horse_no, horse_name, cond, est_odds in candidates:
        winner_info = race_results.get(race_no)

        if winner_info is None:
            result_str  = '不明'
            finish_pos  = None
            record_odds = est_odds
            notes       = '結果取得できず'
            print(f'\n  [？] {race_no}R  馬番{horse_no:2d} {horse_name}  条件{cond}')
            print(f'         結果を取得できませんでした')
        else:
            winner_name, winner_no, actual_odds = winner_info
            if winner_name == horse_name or winner_no == horse_no:
                result_str = '的中'
                finish_pos = 1
                hit_count += 1
                marker     = '◎ 的中！'
            else:
                result_str = '不的中'
                finish_pos = None
                marker     = '×'
            record_odds = actual_odds
            notes = f'1着: 馬番{winner_no} {winner_name}'

            print(f'\n  [{marker}] {race_no}R  馬番{horse_no:2d} {horse_name}  条件{cond}')
            print(f'         1着: 馬番{winner_no} {winner_name}（{actual_odds}倍）')

        # DB 重複チェック（同日・同会場・同レース・同馬番が記録済みならスキップ）
        dup = conn.execute('''
            SELECT id FROM condition_bet_history
            WHERE race_date=? AND venue=? AND race_no=? AND horse_no=?
        ''', (race_date, venue, race_no, horse_no)).fetchone()

        if dup:
            print('         ※ DB記録済みのためスキップ')
        else:
            conn.execute('''
                INSERT INTO condition_bet_history
                (race_date, venue, race_no, horse_no, horse_name,
                 condition_type, tansho_odds, finish_pos, result, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (race_date, venue, race_no, horse_no, horse_name,
                  cond, record_odds, finish_pos, result_str, notes))

    conn.commit()

    # サマリー表示（金額なし）
    print('\n' + '-' * 60)
    print(f'  的中: {hit_count} / {len(candidates)} 件')
    print('=' * 60)
    print()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    args = sys.argv[1:]

    # ── --save モード: 購入候補を JSON ファイルに保存して終了 ──
    if '--save' in args:
        idx = args.index('--save')
        if idx + 1 >= len(args):
            print('[エラー] --save の後に JSON を指定してください。')
            print('  例: --save \'{"venue":"中京","candidates":[[8,10,"馬名","D",15.0]]}\'')
            sys.exit(1)
        save_candidates(args[idx + 1])
        return

    # ── 購入候補ファイルを読み込む ──
    candidates, venue, race_date = load_candidates()

    conn = sqlite3.connect(db_path)
    ensure_table(conn)

    race_nos = sorted({c[0] for c in candidates})

    # ── 購入候補 一覧表示 ──
    print(f'\n購入候補: {len(candidates)}頭  対象レース: {race_nos}  {venue} {race_date}')
    if candidates:
        for r, n, name, cond, odds in candidates:
            odds_str = f'{odds}倍' if odds > 0 else '想定オッズ未確認'
            print(f'  {r}R 馬番{n:2d}  {name:<20}  条件{cond}  {odds_str}')
    else:
        print('  （本日の購入候補はありません）')
        conn.close()
        return

    # ── モード判定 ──
    if '--manual' in args:
        race_results = fetch_results_manual(race_nos)

    elif '--results' in args:
        idx = args.index('--results')
        if idx + 1 >= len(args):
            print('[エラー] --results の後に JSON を指定してください。')
            conn.close()
            sys.exit(1)
        print('\nPlaywright MCP から取得した結果を使用します...')
        race_results = fetch_results_from_args(args[idx + 1])
        for rno, info in sorted(race_results.items()):
            print(f'  {rno}R  1着: 馬番{info[1]} {info[0]}（{info[2]}倍）')

    elif '--auto' in args:
        print(f'\n自動取得モード（playwright_retry 経由）...')
        race_results = fetch_results_auto(venue, race_nos)
        if not race_results:
            print('[警告] 自動取得に失敗しました。--manual または --results を使用してください。')
            conn.close()
            return

    else:
        print()
        print('【使い方】')
        print('  python result_checker.py --manual')
        print('    → 手動で1着馬を入力して判定')
        print()
        print('  python result_checker.py --results \'<JSON>\'')
        print('    → Claude（Playwright MCP）から結果を受け取って判定')
        print('    例: --results \'{"8":[12,"チムグクル",3.1],"11":[18,"アイサンサン",27.6]}\'')
        print()
        print('  python result_checker.py --auto')
        print('    → playwright_retry 経由で競馬ラボから自動取得して判定')
        print()
        print('通常は Claude に「result_checker.py を実行して」と指示するだけで')
        print('自動的に --results モードで実行されます。')
        conn.close()
        return

    judge_and_record(conn, candidates, venue, race_date, race_results)
    conn.close()


if __name__ == '__main__':
    main()
