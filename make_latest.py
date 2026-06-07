# -*- coding: utf-8 -*-
import glob, json, os, sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

BASE = os.path.dirname(os.path.abspath(__file__))

files = sorted(glob.glob(os.path.join(BASE, 'predictions_*.json')))
if not files:
    print('predictions_*.json not found', file=sys.stderr)
    sys.exit(1)

latest_file = files[-1]
with open(latest_file, encoding='utf-8') as f:
    data = json.load(f)

honmei = data['prediction']['◎']
edge = honmei.get('edge', 0)
is_anaba = honmei.get('popularity', 99) >= 4
edge_ok = edge >= 0.06

if is_anaba and edge_ok:
    verdict = '🟢🟢 強推奨'
elif edge_ok:
    verdict = '🟢 推奨'
elif edge > 0:
    verdict = '🟡 様子見'
else:
    verdict = '🔴 見送り'

summary = {
    'race_name': data.get('race_name', ''),
    'race_date': data.get('date', ''),
    'venue': data.get('venue', ''),
    'surface': data.get('surface', ''),
    'distance': data.get('distance', 0),
    'horse_name': honmei.get('horse_name', ''),
    'popularity': honmei.get('popularity', 0),
    'odds': honmei.get('odds', 0),
    'edge': edge,
    'verdict': verdict,
    'adi': data.get('chaos_index', 0),
    'adi_label': data.get('chaos_label', ''),
}

os.makedirs(os.path.join(BASE, 'output'), exist_ok=True)
out_path = os.path.join(BASE, 'output', 'latest_data.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"latest_data.json: {summary['race_name']} ◎{summary['horse_name']} edge={edge:+.3f} {verdict}")
