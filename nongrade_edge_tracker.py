# -*- coding: utf-8 -*-
"""
nongrade_edge_tracker.py - 重賞外穴馬エッジ記録ツール

週次フロー実行時に重賞外レース（条件A〜D以外の一般レース）で
エッジ+0.06以上かつ10番人気以上の穴馬を記録する。

【使い方】
  # 記録を追加
  python nongrade_edge_tracker.py --add '<JSON>'

  # 結果を後から更新（result_checker 実行時に自動呼び出し可）
  python nongrade_edge_tracker.py --result '<JSON>'

  # 集計サマリーを表示
  python nongrade_edge_tracker.py --summary

【--add JSONフォーマット】
  {
    "date": "2026-05-23",
    "race_name": "3歳未勝利",
    "venue": "東京",
    "race_no": 5,
    "surface": "芝",
    "distance": 1600,
    "track_cond": "良",
    "horse_no": 12,
    "horse_name": "サンプルホース",
    "popularity": 11,
    "odds": 45.0,
    "edge": 0.082
  }

【--result JSONフォーマット】
  {
    "date": "2026-05-23",
    "race_name": "3歳未勝利",
    "horse_name": "サンプルホース",
    "finish": 1
  }
"""

import os
import sys
import json
import io
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_PATH  = os.path.join(BASE_DIR, 'nongrade_edge_log.json')

ALERT_THRESHOLD = 50  # 件数到達時にバックテスト推奨アラート


def _load() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, encoding='utf-8') as f:
        return json.load(f)


def _save(records: list):
    with open(LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def cmd_add(raw_json: str):
    """穴馬記録を追加する。"""
    try:
        d = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f'[エラー] JSON解析失敗: {e}')
        sys.exit(1)

    required = ['date', 'race_name', 'venue', 'race_no', 'surface', 'distance',
                'track_cond', 'horse_no', 'horse_name', 'popularity', 'odds', 'edge']
    for key in required:
        if key not in d:
            print(f'[エラー] 必須フィールド "{key}" がありません。')
            sys.exit(1)

    record = {
        'date':       d['date'],
        'race_name':  d['race_name'],
        'venue':      d['venue'],
        'race_no':    int(d['race_no']),
        'surface':    d['surface'],
        'distance':   int(d['distance']),
        'track_cond': d['track_cond'],
        'horse_no':   int(d['horse_no']),
        'horse_name': d['horse_name'],
        'popularity': int(d['popularity']),
        'odds':       float(d['odds']),
        'edge':       float(d['edge']),
        'finish':     d.get('finish', None),   # None = 未照合
        'pnl':        d.get('pnl', None),       # None = 未計算（投資100円基準）
        'added_at':   datetime.now().strftime('%Y-%m-%d %H:%M'),
    }

    records = _load()
    records.append(record)
    _save(records)

    total = len(records)
    print(f'[OK] 記録追加: {record["date"]} {record["venue"]} {record["race_no"]}R '
          f'{record["horse_name"]}（{record["popularity"]}人気 {record["odds"]}倍 '
          f'エッジ{record["edge"]:+.3f}）')
    print(f'     累計 {total} 件 / ログ: {os.path.basename(LOG_PATH)}')

    if total >= ALERT_THRESHOLD:
        print(f'\n  ⚠ 累計 {total} 件到達 → バックテスト実施を推奨します。')
        print(f'    python nongrade_edge_tracker.py --summary')


def cmd_result(raw_json: str):
    """記録済みエントリーに着順・収支を後から補完する。"""
    try:
        d = json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f'[エラー] JSON解析失敗: {e}')
        sys.exit(1)

    records = _load()
    matched = 0
    for rec in records:
        if (rec['date'] == d.get('date') and
                rec['race_name'] == d.get('race_name') and
                rec['horse_name'] == d.get('horse_name')):
            finish = int(d['finish'])
            rec['finish'] = finish
            # 収支計算: 投資100円固定
            if finish == 1:
                pnl = round(rec['odds'] * 100 - 100, 0)
            else:
                pnl = -100
            rec['pnl'] = int(pnl)
            matched += 1

    if matched == 0:
        print('[警告] 一致するレコードが見つかりませんでした。')
        print(f'  date={d.get("date")}  race_name={d.get("race_name")}  horse_name={d.get("horse_name")}')
        sys.exit(1)

    _save(records)
    print(f'[OK] {matched} 件を更新しました。')


def cmd_summary():
    """集計サマリーを表示する。"""
    records = _load()
    if not records:
        print('記録がありません。')
        return

    total  = len(records)
    done   = [r for r in records if r['finish'] is not None]
    nd     = total - len(done)

    hits   = [r for r in done if r['finish'] == 1]
    n_hit  = len(hits)
    invest = len(done) * 100
    payout = sum(r['pnl'] + 100 for r in done if r['finish'] == 1)
    roi    = payout / invest * 100 if invest > 0 else 0.0
    pnl_total = sum(r['pnl'] for r in done)

    print()
    print('=' * 60)
    print('  【重賞外穴馬エッジ トラッカー サマリー】')
    print('=' * 60)
    print(f'  記録件数 : {total} 件（照合済み {len(done)} 件 / 未照合 {nd} 件）')
    print(f'  的中数   : {n_hit} 件 / {len(done)} 件（的中率 {n_hit/len(done)*100:.1f}%）' if done else '  的中数   : -')
    print(f'  投資総額 : {invest:,} 円（100円×{len(done)}件）')
    print(f'  払戻総額 : {payout:,} 円')
    print(f'  収支     : {pnl_total:+,} 円')
    print(f'  回収率   : {roi:.1f}%')
    print()

    # 的中馬一覧
    if hits:
        print('  【的中馬一覧】')
        for r in sorted(hits, key=lambda x: x['date']):
            print(f'    {r["date"]}  {r["venue"]} {r["race_no"]}R  {r["horse_name"]}'
                  f'  {r["popularity"]}人気 {r["odds"]}倍  エッジ{r["edge"]:+.3f}'
                  f'  +{r["pnl"]:,}円')
        print()

    # 未照合件数
    if nd > 0:
        print(f'  ※ 未照合 {nd} 件あり。--result で着順を補完してください。')
        print()

    # バックテスト推奨アラート
    if total >= ALERT_THRESHOLD:
        print(f'  ⚠ 累計 {total} 件（目標{ALERT_THRESHOLD}件）到達 → バックテスト実施を推奨します。')
        print()

    print('=' * 60)
    print()


def main():
    args = sys.argv[1:]

    if '--add' in args:
        idx = args.index('--add')
        if idx + 1 >= len(args):
            print('[エラー] --add の後にJSONを指定してください。')
            sys.exit(1)
        cmd_add(args[idx + 1])

    elif '--result' in args:
        idx = args.index('--result')
        if idx + 1 >= len(args):
            print('[エラー] --result の後にJSONを指定してください。')
            sys.exit(1)
        cmd_result(args[idx + 1])

    elif '--summary' in args:
        cmd_summary()

    else:
        print()
        print('【nongrade_edge_tracker.py - 重賞外穴馬エッジ記録ツール】')
        print()
        print('使い方:')
        print('  python nongrade_edge_tracker.py --add \'<JSON>\'')
        print('    → エッジ+0.06以上・10番人気以上の穴馬を記録')
        print()
        print('  python nongrade_edge_tracker.py --result \'<JSON>\'')
        print('    → 記録済みエントリーに着順・収支を補完')
        print()
        print('  python nongrade_edge_tracker.py --summary')
        print('    → 集計サマリーを表示（50件でバックテスト推奨アラート）')
        print()
        print('記録条件:')
        print('  ・重賞（G1/G2/G3）以外のレース')
        print('  ・エッジ値 +0.06 以上')
        print('  ・10番人気以上の穴馬')
        print(f'  ・ログ保存先: {LOG_PATH}')
        print()


if __name__ == '__main__':
    main()
