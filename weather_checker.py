# -*- coding: utf-8 -*-
"""
weather_checker.py - 開催場 天気予報チェッカー（Playwright MCP連携版）

【設計思想】
  ClaudeがPlaywright MCPでYahoo天気（競馬場専用ページ）または tenki.jp から
  天気予報を取得し、このスクリプトに JSON で渡す。
  スクリプトは午後（12〜17時）の降水確率と降水量を表示し、
  50%以上の場合は「馬場悪化リスクあり」と警告する。
  判断は人間が行う（自動的な購入判断変更はしない）。

【使い方】

  # Playwright MCPで取得したデータを渡す
  python weather_checker.py --weather '<JSON>'

  # JSON形式例
  {
    "date": "2026-04-06",
    "venues": [
      {
        "name": "中京",
        "hourly": [
          {"hour": 9,  "prob": 10, "mm": 0.0},
          {"hour": 12, "prob": 30, "mm": 0.0},
          {"hour": 15, "prob": 50, "mm": 1.0},
          {"hour": 18, "prob": 40, "mm": 0.5}
        ]
      },
      {
        "name": "中山",
        "hourly": [
          {"hour": 9,  "prob": 0,  "mm": 0.0},
          {"hour": 12, "prob": 10, "mm": 0.0},
          {"hour": 15, "prob": 20, "mm": 0.0},
          {"hour": 18, "prob": 10, "mm": 0.0}
        ]
      }
    ]
  }

  # 保存済みファイルを表示
  python weather_checker.py --show

【出力ファイル】
  weather_YYYYMMDD.json  ← 当日の天気データを保存（--weather 実行時）
"""

import os
import sys
import json
from datetime import date

# Windows環境での日本語出力設定
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 警告閾値
WARN_PROB_THRESHOLD = 50   # 降水確率（%）がこれ以上で警告
WARN_MM_THRESHOLD   = 2.0  # 降水量（mm）がこれ以上で警告（追加情報）

# 午後の対象時間帯（12〜17時）
AFTERNOON_HOURS = set(range(12, 18))

# 馬場状態への影響コメント
CONDITION_IMPACT = {
    'A': ('中京', 'ダ', '馬場問わず購入可。雨でも条件Aは見送りなし。'),
    'B': ('福島', 'ダ', '稍重・不良は見送り。雨が降ると影響大。'),
    'C': ('新潟', '芝', '重馬場は見送り。雨量に注意。'),
    'D': ('中京', '芝', '不良のみ見送り。稍重・重は積極買い。'),
}


def weather_filepath(race_date):
    filename = f'weather_{race_date.replace("-", "")}.json'
    return os.path.join(BASE_DIR, filename)


def parse_weather(json_str):
    try:
        return json.loads(json_str)
    except Exception as e:
        print(f'[エラー] --weather の JSON 解析に失敗: {e}')
        sys.exit(1)


def get_afternoon_stats(hourly):
    """
    hourly: [{"hour": 12, "prob": 30, "mm": 0.5}, ...]
    12〜17時のデータを抽出して最大降水確率・合計降水量を返す。
    """
    afternoon = [h for h in hourly if h.get('hour', -1) in AFTERNOON_HOURS]
    if not afternoon:
        return None, None, []

    max_prob  = max(h.get('prob', 0) for h in afternoon)
    total_mm  = sum(h.get('mm', 0.0) for h in afternoon)
    return max_prob, total_mm, afternoon


def display_venue(venue_data):
    name    = venue_data.get('name', '不明')
    hourly  = venue_data.get('hourly', [])

    max_prob, total_mm, afternoon = get_afternoon_stats(hourly)

    print(f'\n  ■ {name}')

    if not afternoon:
        print('    （午後の時間帯データなし）')
        return False

    # 時間帯別テーブル
    print('    時刻  降水確率  降水量')
    print('    ' + '─' * 28)
    for h in sorted(afternoon, key=lambda x: x['hour']):
        hour  = h['hour']
        prob  = h.get('prob', 0)
        mm    = h.get('mm', 0.0)
        bar   = '█' * (prob // 10) + '░' * (10 - prob // 10)
        print(f'    {hour:2d}時   {prob:3d}%  {bar}  {mm:.1f}mm')

    print('    ' + '─' * 28)
    print(f'    午後最大降水確率: {max_prob}%  /  午後合計降水量: {total_mm:.1f}mm')

    # 警告判定
    warned = False
    if max_prob >= WARN_PROB_THRESHOLD:
        print(f'    ⚠️  警告: 降水確率{max_prob}% ≥ {WARN_PROB_THRESHOLD}%  →  馬場悪化リスクあり')
        warned = True
    if total_mm >= WARN_MM_THRESHOLD:
        print(f'    ⚠️  警告: 午後合計降水量{total_mm:.1f}mm  →  馬場状態変化に注意')
        warned = True

    return warned


def display_condition_impact(warned_venues):
    """
    警告が出た会場に対して、条件A〜Dへの影響を表示する。
    """
    if not warned_venues:
        return

    print('\n  ─ 条件別・馬場変化リスク早見 ─')
    for cond, (venue, baba, note) in CONDITION_IMPACT.items():
        if venue in warned_venues:
            print(f'  条件{cond}（{venue} {baba}）: {note}')


def main():
    args = sys.argv[1:]

    # ── --weather モード ──
    if '--weather' in args:
        idx = args.index('--weather')
        if idx + 1 >= len(args):
            print('[エラー] --weather の後に JSON を指定してください。')
            sys.exit(1)

        data = parse_weather(args[idx + 1])
        race_date = data.get('date', str(date.today()))
        venues    = data.get('venues', [])

        # ファイル保存
        filepath = weather_filepath(race_date)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 表示
        print()
        print('=' * 56)
        print(f'  天気予報チェック  {race_date}  （午後 12〜17時）')
        print('=' * 56)

        warned_venues = []
        for v in venues:
            had_warning = display_venue(v)
            if had_warning:
                warned_venues.append(v.get('name', ''))

        display_condition_impact(warned_venues)

        print()
        print('  ※ 馬場判断は人間が行ってください（自動変更なし）')
        if not warned_venues:
            print('  ✅ 全会場で降水確率50%未満。馬場悪化リスクは低い。')
        print('=' * 56)
        print(f'  保存先: {os.path.basename(filepath)}')
        print()
        return

    # ── --show モード（保存済みファイルを表示）──
    if '--show' in args:
        race_date = str(date.today())
        filepath  = weather_filepath(race_date)
        if not os.path.exists(filepath):
            print(f'[エラー] 天気データファイルが見つかりません: {os.path.basename(filepath)}')
            print('先に --weather で天気データを保存してください。')
            sys.exit(1)

        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)

        # --weather と同じ表示処理
        sys.argv = [sys.argv[0], '--weather', json.dumps(data, ensure_ascii=False)]
        main()
        return

    # ── 使い方表示 ──
    print()
    print('【使い方】')
    print('  python weather_checker.py --weather \'<JSON>\'')
    print('    → Claude（Playwright MCP）から取得した天気データを表示・保存')
    print()
    print('  python weather_checker.py --show')
    print('    → 当日の保存済み天気データを表示')
    print()
    print('【JSON形式例】')
    example = {
        "date": str(date.today()),
        "venues": [
            {
                "name": "中京",
                "hourly": [
                    {"hour": 9,  "prob": 10, "mm": 0.0},
                    {"hour": 12, "prob": 30, "mm": 0.0},
                    {"hour": 15, "prob": 50, "mm": 1.0},
                    {"hour": 18, "prob": 40, "mm": 0.5}
                ]
            }
        ]
    }
    print(json.dumps(example, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
