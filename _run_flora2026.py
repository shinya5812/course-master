# -*- coding: utf-8 -*-
"""フローラS2026 予測実行スクリプト"""
import sys, os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

RACE_DATA = {
    "race_name": "サンスポ賞フローラＳ GⅡ",
    "venue": "東京",
    "surface": "芝",
    "distance": 2000,
    "track_cond": "良",
    "class_code": 800,
    "horses": [
        {"horse_no": 1,  "horse_name": "リスレジャンデール", "jockey": "津村明秀", "sire": "エピファネイア",    "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 6,  "odds": 18.7},
        {"horse_no": 2,  "horse_name": "ラベルセーヌ",       "jockey": "荻野極",   "sire": "キズナ",          "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 2,  "odds": 4.5},
        {"horse_no": 3,  "horse_name": "サムシングスイート", "jockey": "酒井学",   "sire": "サートゥルナーリア","dam_sire": "", "age": 3, "weight": 54.0, "popularity": 8,  "odds": 28.9},
        {"horse_no": 4,  "horse_name": "ペイシャシス",       "jockey": "北村宏司", "sire": "シスキン",        "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 13, "odds": 80.0},
        {"horse_no": 5,  "horse_name": "ラフターラインズ",   "jockey": "D.レーン", "sire": "アルアイン",      "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 1,  "odds": 2.5},
        {"horse_no": 6,  "horse_name": "ペンダント",         "jockey": "佐々木大輔","sire": "オルフェーヴル",  "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 7,  "odds": 22.9},
        {"horse_no": 7,  "horse_name": "リアライズルミナス", "jockey": "松山弘平", "sire": "シルバーステート", "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 5,  "odds": 10.7},
        {"horse_no": 8,  "horse_name": "ゴバド",             "jockey": "原優介",   "sire": "トーセンラー",    "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 9,  "odds": 29.0},
        {"horse_no": 9,  "horse_name": "コウギョク",         "jockey": "横山和生", "sire": "シルバーステート", "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 12, "odds": 56.8},
        {"horse_no": 10, "horse_name": "エイシンウィスパー", "jockey": "松若風馬", "sire": "ルーラーシップ",   "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 10, "odds": 31.0},
        {"horse_no": 11, "horse_name": "ファムクラジューズ", "jockey": "横山武史", "sire": "ベンバトル",      "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 4,  "odds": 8.4},
        {"horse_no": 12, "horse_name": "スタニングレディ",   "jockey": "三浦皇成", "sire": "ベンバトル",      "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 11, "odds": 41.3},
        {"horse_no": 13, "horse_name": "エンネ",             "jockey": "M.ディー", "sire": "キズナ",          "dam_sire": "", "age": 3, "weight": 54.0, "popularity": 3,  "odds": 5.8}
    ]
}

sys.argv = ['grade_race_predictor.py', '--race', json.dumps(RACE_DATA, ensure_ascii=False)]
exec(open(os.path.join(BASE_DIR, 'grade_race_predictor.py'), encoding='utf-8').read())
