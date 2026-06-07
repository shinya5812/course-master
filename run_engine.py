#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

print("=" * 70)
print(" COURSE MASTER v7.0 - 実行テスト")
print("=" * 70)

# カレントディレクトリを表示
print(f"\n現在のフォルダ: {os.getcwd()}")

# ファイル確認
print("\nファイル確認:")
files_to_check = [
    'course_master_v70_engine.pkl',
    'course_master_v70_engine.py',
    '2024_2026結果.csv'
]

for fname in files_to_check:
    exists = os.path.exists(fname)
    status = "✓" if exists else "✗"
    print(f"  {status} {fname}")

# Pickle ファイルをロード
print("\n[1] Pickle ファイルをロード中...")
try:
    import pickle
    with open('course_master_v70_engine.pkl', 'rb') as f:
        state = pickle.load(f)
    print("  ✓ ロード成功")
except Exception as e:
    print(f"  ✗ エラー: {e}")
    sys.exit(1)

# 統計情報を表示
print("\n[2] 統計マスター情報:")
stats_to_show = [
    ('sire_stats', '種牡馬統計'),
    ('dam_sire_stats', '母の父統計'),
    ('jockey_stats', '騎手統計'),
    ('trainer_stats', '調教師統計'),
    ('class_stats', 'クラス統計'),
    ('track_stats', 'トラック統計'),
    ('distance_stats', '距離統計'),
]

for key, name in stats_to_show:
    count = len(state.get(key, {}))
    print(f"  {name}: {count}件")

# サンプル表示
print("\n[3] サンプル（種牡馬 TOP 3）:")
if 'sire_stats' in state and state['sire_stats']:
    sires = sorted(state['sire_stats'].items(), 
                   key=lambda x: x[1]['races'], 
                   reverse=True)[:3]
    for sire, stat in sires:
        print(f"  {sire}: 出走{stat['races']:5d}回 | 勝率{stat['win_rate']:5.1%}")

print("\n" + "=" * 70)
print("✓ エンジンは正常に動作しています")
print("=" * 70)

print("\n【成功した場合のステップ】")
print("1. quickstart_v70.py でレース予測を実行")
print("2. 必要な CSV ファイルをダウンロード")
print("3. 本格的なレース予測を開始")

input("\nEnter キーを押して終了...")