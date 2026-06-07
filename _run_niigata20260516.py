# -*- coding: utf-8 -*-
import sys, os
os.chdir(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')
sys.path.insert(0, r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')

import json

RACE = {
    "race_name": "新潟大賞典 GⅢ",
    "venue": "新潟",
    "surface": "芝",
    "distance": 2000,
    "track_cond": "良",
    "horses": [
        {"horse_no":  1, "horse_name": "ホールネス",       "jockey": "西塚洸二", "sire": "Lope de Vega",         "dam_sire": "Golan",                "age": 6, "weight": 55.0, "popularity": 10, "odds": 25.2},
        {"horse_no":  2, "horse_name": "ラインベック",     "jockey": "富田暁",   "sire": "ディープインパクト",    "dam_sire": "キングカメハメハ",     "age": 9, "weight": 56.0, "popularity": 14, "odds": 90.9},
        {"horse_no":  3, "horse_name": "グランディア",     "jockey": "西村淳也", "sire": "ハービンジャー",        "dam_sire": "サンデーサイレンス",   "age": 7, "weight": 57.0, "popularity":  6, "odds": 11.9},
        {"horse_no":  4, "horse_name": "アンゴラブラック", "jockey": "岩田康誠", "sire": "キズナ",               "dam_sire": "ルーラーシップ",       "age": 5, "weight": 56.0, "popularity":  4, "odds":  8.7},
        {"horse_no":  5, "horse_name": "グランドカリナン", "jockey": "小林美駒", "sire": "リアルインパクト",      "dam_sire": "マンハッタンカフェ",   "age": 6, "weight": 54.0, "popularity": 15, "odds": 109.0},
        {"horse_no":  6, "horse_name": "ドゥラドーレス",   "jockey": "ルメール", "sire": "ドゥラメンテ",          "dam_sire": "ハービンジャー",       "age": 7, "weight": 58.0, "popularity":  1, "odds":  3.2},
        {"horse_no":  7, "horse_name": "トーセンリョウ",   "jockey": "斎藤新",   "sire": "ディープインパクト",    "dam_sire": "Hawk Wing",            "age": 7, "weight": 56.0, "popularity":  8, "odds": 17.1},
        {"horse_no":  8, "horse_name": "ヤマニンブークリエ","jockey":"横山典弘", "sire": "キタサンブラック",      "dam_sire": "チチカステナンゴ",     "age": 4, "weight": 56.0, "popularity":  7, "odds": 13.6},
        {"horse_no":  9, "horse_name": "フクノブルーレイク","jockey":"ゴンサルベス","sire":"ウインブライト",     "dam_sire": "ロードカナロア",       "age": 4, "weight": 53.0, "popularity":  9, "odds": 17.2},
        {"horse_no": 10, "horse_name": "サフィラ",         "jockey": "丸山元気", "sire": "ハーツクライ",          "dam_sire": "Lomitas",              "age": 5, "weight": 56.0, "popularity": 11, "odds": 30.5},
        {"horse_no": 11, "horse_name": "バレエマスター",   "jockey": "菊沢一樹", "sire": "スピルバーグ",          "dam_sire": "スウェプトオーヴァーボード","age": 7,"weight": 55.0, "popularity": 12, "odds": 32.8},
        {"horse_no": 12, "horse_name": "セキトバイースト", "jockey": "浜中俊",   "sire": "デクラレーションオブウォー","dam_sire":"Footstepsinthesand","age": 5,"weight": 56.0, "popularity":  5, "odds":  9.4},
        {"horse_no": 13, "horse_name": "シュトルーヴェ",   "jockey": "丹内祐次", "sire": "キングカメハメハ",      "dam_sire": "ディープインパクト",   "age": 7, "weight": 59.0, "popularity": 13, "odds": 59.7},
        {"horse_no": 14, "horse_name": "シンハナーダ",     "jockey": "杉原誠人", "sire": "レイデオロ",            "dam_sire": "ウォーエンブレム",     "age": 5, "weight": 56.0, "popularity":  3, "odds":  8.2},
        {"horse_no": 15, "horse_name": "シュガークン",     "jockey": "武豊",     "sire": "ドゥラメンテ",          "dam_sire": "サクラバクシンオー",   "age": 5, "weight": 58.0, "popularity":  2, "odds":  5.2},
    ]
}

sys.argv = ['grade_race_predictor.py', '--race', json.dumps(RACE, ensure_ascii=False)]
exec(open('grade_race_predictor.py', encoding='utf-8').read())
