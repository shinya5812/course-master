# -*- coding: utf-8 -*-
import pandas as pd
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster'

# 血統CSV
ped_path = BASE + r'\data\pedigree\血統_0410.csv'
ped_df = pd.read_csv(ped_path, encoding='cp932')
print(f"=== 血統CSV ===")
print(f"行数: {len(ped_df):,}")
print(f"カラム: {list(ped_df.columns)}")
print(f"先頭3行:")
print(ped_df.head(3).to_string())

print()

# レース結果CSV
race_path = BASE + r'\data\race\結果202603070405.csv'
race_df = pd.read_csv(race_path, encoding='cp932')
print(f"=== レース結果CSV ===")
print(f"行数: {len(race_df):,}")
print(f"カラム: {list(race_df.columns)}")
print(f"先頭3行:")
print(race_df.head(3).to_string())
