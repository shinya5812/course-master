# -*- coding: utf-8 -*-
"""読売マイラーズC2026 予測実行スクリプト"""
import sys, os, json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

RACE_DATA = {
    "race_name": "読売マイラーズカップ GⅡ",
    "venue": "京都",
    "surface": "芝",
    "distance": 1600,
    "track_cond": "良",
    "class_code": 800,
    "horses": [
        {"horse_no": 1,  "horse_name": "ドラゴンブースト",   "jockey": "丹内祐次",   "sire": "スクリーンヒーロー","dam_sire": "", "age": 4, "weight": 58.0, "popularity": 9,  "odds": 28.0},
        {"horse_no": 2,  "horse_name": "オフトレイル",       "jockey": "岩田望来",   "sire": "Farhh",            "dam_sire": "", "age": 5, "weight": 58.0, "popularity": 2,  "odds": 5.2},
        {"horse_no": 3,  "horse_name": "ファインライン",     "jockey": "鮫島克駿",   "sire": "ファインニードル",  "dam_sire": "", "age": 5, "weight": 58.0, "popularity": 14, "odds": 94.4},
        {"horse_no": 4,  "horse_name": "クルゼイロドスル",   "jockey": "太宰啓介",   "sire": "ファインニードル",  "dam_sire": "", "age": 5, "weight": 58.0, "popularity": 13, "odds": 88.8},
        {"horse_no": 5,  "horse_name": "ショウナンアデイブ", "jockey": "池添謙一",   "sire": "ディープインパクト","dam_sire": "", "age": 6, "weight": 58.0, "popularity": 12, "odds": 80.1},
        {"horse_no": 6,  "horse_name": "ブエナオンダ",       "jockey": "田口貫太",   "sire": "リオンディーズ",    "dam_sire": "", "age": 5, "weight": 58.0, "popularity": 11, "odds": 33.7},
        {"horse_no": 7,  "horse_name": "ベラジオボンド",     "jockey": "北村友一",   "sire": "ロードカナロア",    "dam_sire": "", "age": 5, "weight": 58.0, "popularity": 5,  "odds": 10.4},
        {"horse_no": 8,  "horse_name": "シャンパンカラー",   "jockey": "岩田康誠",   "sire": "ドゥラメンテ",      "dam_sire": "", "age": 5, "weight": 58.0, "popularity": 10, "odds": 30.3},
        {"horse_no": 9,  "horse_name": "アドマイヤズーム",   "jockey": "武豊",       "sire": "モーリス",          "dam_sire": "", "age": 6, "weight": 58.0, "popularity": 1,  "odds": 3.7},
        {"horse_no": 10, "horse_name": "ウォーターリヒト",   "jockey": "高杉吏麒",   "sire": "ドレフォン",        "dam_sire": "", "age": 4, "weight": 58.0, "popularity": 3,  "odds": 5.3},
        {"horse_no": 11, "horse_name": "キョウエイブリッサ", "jockey": "田山旺佑",   "sire": "グレーターロンドン","dam_sire": "", "age": 5, "weight": 58.0, "popularity": 17, "odds": 167.6},
        {"horse_no": 12, "horse_name": "ファーヴェント",     "jockey": "坂井瑠星",   "sire": "ハーツクライ",      "dam_sire": "", "age": 6, "weight": 58.0, "popularity": 8,  "odds": 22.4},
        {"horse_no": 13, "horse_name": "アサヒ",             "jockey": "松本大輝",   "sire": "カレンブラックヒル","dam_sire": "", "age": 6, "weight": 58.0, "popularity": 18, "odds": 209.6},
        {"horse_no": 14, "horse_name": "ロングラン",         "jockey": "団野大成",   "sire": "ヴィクトワールピサ","dam_sire": "", "age": 7, "weight": 58.0, "popularity": 16, "odds": 134.2},
        {"horse_no": 15, "horse_name": "マテンロウスカイ",   "jockey": "横山典弘",   "sire": "モーリス",          "dam_sire": "", "age": 5, "weight": 58.0, "popularity": 15, "odds": 108.8},
        {"horse_no": 16, "horse_name": "シックスペンス",     "jockey": "戸崎圭太",   "sire": "キズナ",            "dam_sire": "", "age": 4, "weight": 58.0, "popularity": 4,  "odds": 6.4},
        {"horse_no": 17, "horse_name": "エルトンバローズ",   "jockey": "西村淳也",   "sire": "ディープブリランテ","dam_sire": "", "age": 6, "weight": 58.0, "popularity": 6,  "odds": 12.1},
        {"horse_no": 18, "horse_name": "ランスオブカオス",   "jockey": "吉村誠之助", "sire": "シルバーステート",  "dam_sire": "", "age": 4, "weight": 58.0, "popularity": 7,  "odds": 15.4}
    ]
}

sys.argv = ['grade_race_predictor.py', '--race', json.dumps(RACE_DATA, ensure_ascii=False)]
exec(open(os.path.join(BASE_DIR, 'grade_race_predictor.py'), encoding='utf-8').read())
