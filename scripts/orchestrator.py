# -*- coding: utf-8 -*-
"""
scripts/orchestrator.py - Multi-Claudingオーケストレーター

3エージェント（predictor / analyst / result_checker）を並列起動し、
各エージェントのJSON出力を収集して weekly_report_{date}.md を生成する。

【使い方】
  python scripts/orchestrator.py [--date YYYY-MM-DD]

【エラー時】
  各エージェントは失敗時に最大2回リトライされる。
  全リトライ失敗時はレポートに ERROR セクションを追加して続行する。
"""

import os
import sys
import json
import subprocess
import argparse
import concurrent.futures
from datetime import date as dt_date, datetime

# Windows環境での日本語出力
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

PYTHON = sys.executable  # 実行中のPythonインタープリタを使用

MAX_RETRY = 2


# ─────────────────────────────────────────────────────────
def run_agent(name: str, extra_args: list, max_retry: int = MAX_RETRY):
    """
    エージェントスクリプトをsubprocessで実行する。
    失敗時は max_retry 回リトライする。
    戻り値: (name, success: bool, stdout: str, stderr: str)
    """
    script = os.path.join(SCRIPTS_DIR, f'agent_{name}.py')
    cmd    = [PYTHON, script] + extra_args

    last_err = ''
    for attempt in range(max_retry + 1):
        if attempt > 0:
            print(f'  [RETRY] {name} 失敗({attempt}/{max_retry}) → リトライ中...')

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                cwd=BASE_DIR,
                timeout=180,
            )
            if proc.returncode == 0:
                return name, True, proc.stdout, ''
            last_err = proc.stderr or proc.stdout
        except subprocess.TimeoutExpired:
            last_err = f'{name}: タイムアウト（180秒超過）'
        except Exception as e:
            last_err = str(e)

    return name, False, '', last_err


# ─────────────────────────────────────────────────────────
def load_json_safe(path: str):
    """JSONファイルを安全に読み込む（存在しない・パースエラーはNoneを返す）。"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def format_condition_table(by_condition: dict) -> str:
    """条件別集計をMarkdownテーブルに変換する。"""
    if not by_condition:
        return '（データなし）'
    lines = ['| 条件 | ベット | 的中 | 投資 | 払戻 | ROI | 勝率 |',
             '|------|--------|------|------|------|-----|------|']
    for cond, v in sorted(by_condition.items()):
        lines.append(
            f"| {cond} | {v['bets']} | {v['wins']} | "
            f"{v['invested']:,}円 | {v['returned']:,}円 | "
            f"{v['roi']}% | {v['win_rate']:.1%} |"
        )
    return '\n'.join(lines)


def format_monthly_table(monthly: list) -> str:
    """月次集計をMarkdownテーブルに変換する。"""
    if not monthly:
        return '（データなし）'
    lines = ['| 月 | ベット | 的中 | ROI | 収支 |',
             '|----|--------|------|-----|------|']
    for m in monthly:
        sign = '+' if m['net_pnl'] >= 0 else ''
        lines.append(
            f"| {m['month']} | {m['bets']} | {m['wins']} | "
            f"{m['roi']}% | {sign}{m['net_pnl']:,}円 |"
        )
    return '\n'.join(lines)


def format_pnl_table(bets: list) -> str:
    """P&Lベット一覧をMarkdownテーブルに変換する。"""
    if not bets:
        return '（購入候補なし）'
    lines = ['| R | 馬名 | 条件 | オッズ | 結果 | 払戻 | 収支 |',
             '|---|------|------|--------|------|------|------|']
    for b in bets:
        sign = '+' if b['pnl'] >= 0 else ''
        lines.append(
            f"| {b['race_no']}R | {b['horse_name']} | {b['condition']} | "
            f"{b['act_odds']}倍 | {b['result']} | {b['returned']:,}円 | "
            f"{sign}{b['pnl']:,}円 |"
        )
    return '\n'.join(lines)


def format_predictions(races: list, venue: str) -> str:
    """予測結果をMarkdown形式に変換する。"""
    if not races:
        return '（予測データなし）'
    lines = []
    for r in races:
        race_no = r.get('race_no', '?')
        if 'error' in r:
            lines.append(f'- {venue}{race_no}R: {r["error"]}')
            continue
        honmei   = r.get('honmei', {})
        chaos    = r.get('chaos_index', 0)
        top5     = r.get('top5', [])
        horse_ct = r.get('horse_count', 0)

        mark = '⚠️ 大波乱注意' if chaos >= 70 else ('△ 波乱含み' if chaos >= 50 else '◯ 安定')
        lines.append(f'\n#### {venue}{race_no}R（{horse_ct}頭） 荒れ指数: {chaos} {mark}')
        if honmei:
            edge_mark = '★購入推奨' if honmei.get('edge', 0) >= 0.06 else '△様子見' if honmei.get('edge', 0) >= 0 else '✗見送り'
            lines.append(f'- ◎ **{honmei.get("horse_name", "")}** '
                         f'（{honmei.get("popularity", "?")}番人気 {honmei.get("odds", 0)}倍）'
                         f' エッジ: {honmei.get("edge", 0):+.3f} {edge_mark}')
        if top5:
            lines.append('  上位5頭: ' + ' / '.join(
                f'{t["horse_name"]}({t["popularity"]}人気)' for t in top5
            ))
    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────
def generate_report(target_date: str, results: dict) -> str:
    """3エージェントの結果を統合してMarkdownレポートを生成する。"""
    date_nodash  = target_date.replace('-', '')
    pred_data    = load_json_safe(os.path.join(BASE_DIR, f'predictions_{date_nodash}.json'))
    analysis     = load_json_safe(os.path.join(BASE_DIR, f'analysis_{target_date}.json'))
    pnl_data     = load_json_safe(os.path.join(BASE_DIR, f'pnl_{date_nodash}.json'))

    errors = [(name, info['stderr']) for name, info in results.items() if not info['success']]

    lines = [
        f'# 週次レポート — {target_date}',
        f'',
        f'生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        f'',
        f'---',
    ]

    # ─── エラーセクション ───
    if errors:
        lines += ['', '## ⚠️ エラー発生エージェント', '']
        for name, msg in errors:
            lines.append(f'- **{name}**: {msg[:200]}')

    # ─── セクション1: 当日P&L ───
    lines += ['', '## 1. 当日P&L', '']
    if pnl_data and 'error' not in pnl_data:
        s = pnl_data.get('summary', {})
        venue = pnl_data.get('venue', '')
        sign  = '+' if s.get('net_pnl', 0) >= 0 else ''
        lines += [
            f'**会場**: {venue}　**ベット数**: {s.get("total_bets", 0)}件　'
            f'**投資**: {s.get("total_invested", 0):,}円　**払戻**: {s.get("total_returned", 0):,}円',
            f'**ROI**: {s.get("roi", 0.0)}%　**収支**: {sign}{s.get("net_pnl", 0):,}円　'
            f'**的中**: {s.get("win_count", 0)}件',
            '',
            format_pnl_table(pnl_data.get('bets', [])),
        ]
    else:
        lines.append('（P&Lデータなし）')

    # ─── セクション2: 予測結果 ───
    lines += ['', '## 2. エンジン予測', '']
    if pred_data and 'error' not in pred_data:
        venue = pred_data.get('venue', '')
        lines.append(format_predictions(pred_data.get('races', []), venue))
    else:
        lines.append('（予測データなし）')

    # ─── セクション3: 累積分析 ───
    lines += ['', '## 3. 累積ROI分析', '']
    if analysis and 'error' not in analysis:
        t = analysis.get('total', {})
        sign = '+' if t.get('net_pnl', 0) >= 0 else ''
        lines += [
            f'**集計期間**: {analysis.get("period", "")}　'
            f'**総ベット**: {t.get("bets", 0)}件　**勝率**: {t.get("win_rate", 0):.1%}',
            f'**ROI**: {t.get("roi", 0.0)}%　**累積収支**: {sign}{t.get("net_pnl", 0):,}円',
            '',
            '### 条件別',
            '',
            format_condition_table(analysis.get('by_condition', {})),
            '',
            '### 月次推移',
            '',
            format_monthly_table(analysis.get('monthly', [])),
        ]
    else:
        lines.append('（分析データなし）')

    # ─── セクション4: 直近実績 ───
    if analysis and analysis.get('recent'):
        lines += ['', '## 4. 直近5件', '']
        rec_lines = ['| 日付 | 会場 | R | 馬名 | 条件 | オッズ | 結果 |',
                     '|------|------|---|------|------|--------|------|']
        for r in analysis['recent']:
            rec_lines.append(
                f"| {r['race_date']} | {r['venue']} | {r['race_no']}R | "
                f"{r['horse_name']} | {r['condition_type']} | "
                f"{r['tansho_odds']}倍 | {r['result']} |"
            )
        lines += rec_lines

    lines += ['', '---', f'*generated by orchestrator.py*']
    return '\n'.join(lines)


# ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Multi-Claudingオーケストレーター')
    parser.add_argument('--date', default=dt_date.today().isoformat(),
                        help='対象日（YYYY-MM-DD）')
    args = parser.parse_args()
    target_date = args.date

    report_path = os.path.join(BASE_DIR, f'weekly_report_{target_date}.md')

    print(f'=' * 60)
    print(f' orchestrator 開始  date={target_date}')
    print(f'=' * 60)
    print(f'  3エージェントを並列起動します...')
    print()

    # エージェント定義: (name, extra_args)
    agent_configs = [
        ('predictor',     ['--date', target_date]),
        ('analyst',       ['--date', target_date]),
        ('result_checker', ['--date', target_date]),
    ]

    results = {}
    start_t = datetime.now()

    # ── 並列実行 ──
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_name = {
            executor.submit(run_agent, name, extra_args): name
            for name, extra_args in agent_configs
        }
        for future in concurrent.futures.as_completed(future_to_name):
            name, success, stdout, stderr = future.result()
            status = '✅ 成功' if success else '❌ 失敗'
            elapsed = (datetime.now() - start_t).total_seconds()
            print(f'  [{status}] {name:20s} ({elapsed:.1f}s)')
            if stdout:
                for line in stdout.strip().splitlines():
                    print(f'    {line}')
            if not success and stderr:
                print(f'    ERROR: {stderr[:300]}')
            results[name] = {'success': success, 'stdout': stdout, 'stderr': stderr}

    elapsed_total = (datetime.now() - start_t).total_seconds()
    print()
    print(f'  全エージェント完了 ({elapsed_total:.1f}s)')
    print()

    # ── レポート生成 ──
    print(f'  レポート生成中...')
    report_md = generate_report(target_date, results)

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_md)

    print(f'  → {report_path}')
    print()

    success_count = sum(1 for v in results.values() if v['success'])
    print(f'=' * 60)
    print(f' 完了: {success_count}/3 エージェント成功')
    print(f' レポート: {os.path.basename(report_path)}')
    print(f'=' * 60)


if __name__ == '__main__':
    main()
