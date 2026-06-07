# -*- coding: utf-8 -*-
"""NHKマイルC 2026-05-10 予測実行スクリプト"""
import sys, os, json
sys.stdout = __import__('io').TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = __import__('io').TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

NHK_RACE = {
    "race_name":  "NHKマイルC GⅠ",
    "venue":      "東京",
    "surface":    "芝",
    "distance":   1600,
    "track_cond": "良",
    "class_code": 800,
    "horses": [
        {"horse_no":  7, "horse_name": "ダイヤモンドノット", "jockey": "川田将雅",  "sire": "ブリックスアンドモルタル", "dam_sire": "ディープインパクト",  "age": 3, "weight": 57.0, "popularity":  1, "odds":  4.7},
        {"horse_no": 10, "horse_name": "エコロアルバ",       "jockey": "横山和生",  "sire": "モズアスコット",           "dam_sire": "フレンチデピュティ",  "age": 3, "weight": 57.0, "popularity":  2, "odds":  5.2},
        {"horse_no": 17, "horse_name": "ロデオドライブ",     "jockey": "レーン",    "sire": "サートゥルナーリア",       "dam_sire": "スニッツェル",        "age": 3, "weight": 57.0, "popularity":  3, "odds":  6.1},
        {"horse_no":  4, "horse_name": "カヴァレリッツォ",   "jockey": "西村淳也",  "sire": "サートゥルナーリア",       "dam_sire": "ハーツクライ",        "age": 3, "weight": 57.0, "popularity":  4, "odds":  8.6},
        {"horse_no": 16, "horse_name": "アスクイキゴミ",     "jockey": "戸崎圭太",  "sire": "ロードカナロア",           "dam_sire": "Bated Breath",        "age": 3, "weight": 57.0, "popularity":  5, "odds":  9.9},
        {"horse_no": 11, "horse_name": "アドマイヤクワッズ", "jockey": "坂井瑠星",  "sire": "リアルスティール",         "dam_sire": "Zoffany",             "age": 3, "weight": 57.0, "popularity":  6, "odds": 10.7},
        {"horse_no":  9, "horse_name": "サンダーストラック",  "jockey": "ルメール",  "sire": "ロードカナロア",           "dam_sire": "Hinchinbrook",        "age": 3, "weight": 57.0, "popularity":  7, "odds": 18.5},
        {"horse_no": 12, "horse_name": "アンドゥーリル",     "jockey": "岩田望来",  "sire": "サートゥルナーリア",       "dam_sire": "オルフェーヴル",      "age": 3, "weight": 57.0, "popularity":  8, "odds": 19.2},
        {"horse_no": 14, "horse_name": "バルセシート",       "jockey": "北村友一",  "sire": "キズナ",                  "dam_sire": "Lizard Island",       "age": 3, "weight": 57.0, "popularity":  9, "odds": 19.7},
        {"horse_no":  8, "horse_name": "ローベルクランツ",   "jockey": "松山弘平",  "sire": "サトノダイヤモンド",       "dam_sire": "キングカメハメハ",    "age": 3, "weight": 57.0, "popularity": 10, "odds": 25.0},
        {"horse_no":  6, "horse_name": "ジーネキング",       "jockey": "斎藤新",    "sire": "コントレイル",             "dam_sire": "Into Mischief",       "age": 3, "weight": 57.0, "popularity": 11, "odds": 28.8},
        {"horse_no": 15, "horse_name": "レザベーション",     "jockey": "原優介",    "sire": "ダノンプレミアム",         "dam_sire": "ジャングルポケット",  "age": 3, "weight": 57.0, "popularity": 12, "odds": 31.8},
        {"horse_no":  5, "horse_name": "ギリーズボール",     "jockey": "西塚洸二",  "sire": "エピファネイア",           "dam_sire": "フジキセキ",          "age": 3, "weight": 55.0, "popularity": 13, "odds": 33.5},
        {"horse_no": 18, "horse_name": "フクチャンショウ",   "jockey": "横山武史",  "sire": "イスラボニータ",           "dam_sire": "Thewayyouare",        "age": 3, "weight": 57.0, "popularity": 14, "odds": 33.9},
        {"horse_no":  3, "horse_name": "オルネーロ",         "jockey": "津村明秀",  "sire": "サトノダイヤモンド",       "dam_sire": "Not For Sale",        "age": 3, "weight": 57.0, "popularity": 15, "odds": 45.5},
        {"horse_no":  2, "horse_name": "ユウファラオ",       "jockey": "松若風馬",  "sire": "American Pharoah",        "dam_sire": "Medaglia d'Oro",      "age": 3, "weight": 57.0, "popularity": 16, "odds": 89.8},
        {"horse_no": 13, "horse_name": "ハッピーエンジェル", "jockey": "三浦皇成",  "sire": "ジョーカプチーノ",         "dam_sire": "スウェプトオーヴァーボード", "age": 3, "weight": 55.0, "popularity": 17, "odds": 94.5},
        {"horse_no":  1, "horse_name": "リゾートアイランド", "jockey": "佐々木大輔","sire": "イスラボニータ",           "dam_sire": "Frankel",             "age": 3, "weight": 57.0, "popularity": 18, "odds": 109.8},
    ]
}

from grade_race_predictor import load_engine, calc_chaos_index, run_prediction, print_result

print("エンジン読み込み中...")
engine = load_engine()

print("\nNHKマイルC 予測開始...")
chaos = calc_chaos_index(NHK_RACE)
prediction = run_prediction(engine, NHK_RACE)
summary = print_result(NHK_RACE, prediction, chaos)

# JSON出力用データ構築
horse_map = {h['horse_name']: h for h in NHK_RACE['horses']}

def _edge_lbl(edge, thr=0.06):
    if edge is None: return "-"
    if edge >= thr: return "★推奨"
    if edge >= 0.0: return "△様子見"
    return "✗見送り"

all_list = []
for idx, horse_name, score, win_prob, edge in prediction['all']:
    h = horse_map.get(horse_name, {})
    all_list.append({
        "horse_no": h.get('horse_no'),
        "horse_name": horse_name,
        "popularity": h.get('popularity'),
        "odds": h.get('odds'),
        "score": round(score, 1),
        "win_prob": round(win_prob * 100, 1),
        "edge": round(edge, 3) if edge is not None else None,
        "edge_label": _edge_lbl(edge),
        "sire": h.get('sire'),
    })

honmei = prediction['○']
result_json = {
    "date": "2026-05-10",
    "race": "NHKマイルC",
    "venue": "東京",
    "distance": 1600,
    "grade": "G1",
    "surface": "芝",
    "track_cond": "良",
    "ADI": chaos['score'],
    "ADI_label": chaos['label'],
    "honmei": all_list[0] if all_list else {},
    "circle": all_list[1:4] if len(all_list) >= 4 else [],
    "triangle": all_list[4:9] if len(all_list) >= 9 else [],
    "all": all_list,
    "verdict": summary['verdict'],
    "tansho_amount": summary['tansho_amount'],
    "edge_ok": summary['edge_ok'],
    "is_anaba": summary['is_anaba'],
    "umaren": summary['umaren'],
}

out_path = os.path.join(BASE_DIR, "predictions_20260510.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result_json, f, ensure_ascii=False, indent=2)

print(f"\n✅ 予測JSON保存完了: {out_path}")
