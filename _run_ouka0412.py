# -*- coding: utf-8 -*-
import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

with open('_ouka2026_race.json', encoding='utf-8') as f:
    race_data = json.load(f)

sys.argv = ['grade_race_predictor.py', '--race', json.dumps(race_data, ensure_ascii=False)]
