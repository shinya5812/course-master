# -*- coding: utf-8 -*-
"""青葉賞2026 予測実行スクリプト"""
import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

RACE_DATA = {
    "race_name": "青葉賞 GⅡ",
    "venue": "東京",
    "surface": "芝",
    "distance": 2400,
    "track_cond": "良",
    "class_code": 800,
    "horses": [
        {"horse_no": 1,  "horse_name": "トゥーナスタディ",   "jockey": "菅原辰", "sire": "ゴールドアクター",  "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 18, "odds": 348.4},
        {"horse_no": 2,  "horse_name": "カットソロ",         "jockey": "津村",   "sire": "コントレイル",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 12, "odds": 65.1},
        {"horse_no": 3,  "horse_name": "パラディオン",       "jockey": "吉田豊", "sire": "レイデオロ",       "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 14, "odds": 111.1},
        {"horse_no": 4,  "horse_name": "ブラックオリンピア", "jockey": "川田",   "sire": "キタサンブラック",  "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 1,  "odds": 2.2},
        {"horse_no": 5,  "horse_name": "ミッキーファルコン", "jockey": "田辺",   "sire": "エピファネイア",   "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 9,  "odds": 26.8},
        {"horse_no": 6,  "horse_name": "テルヒコウ",         "jockey": "坂井",   "sire": "コントレイル",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 6,  "odds": 17.0},
        {"horse_no": 7,  "horse_name": "タイダルロック",     "jockey": "三浦",   "sire": "モーリス",         "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 3,  "odds": 6.7},
        {"horse_no": 8,  "horse_name": "ラストスマイル",     "jockey": "杉原",   "sire": "ポエティックフレア","dam_sire": "", "age": 3, "weight": 57.0, "popularity": 5,  "odds": 15.5},
        {"horse_no": 9,  "horse_name": "ヒシアムルーズ",     "jockey": "佐々木", "sire": "サートゥルナーリア","dam_sire": "", "age": 3, "weight": 57.0, "popularity": 15, "odds": 126.6},
        {"horse_no": 10, "horse_name": "アッカン",           "jockey": "池添",   "sire": "ホークビル",       "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 11, "odds": 53.5},
        {"horse_no": 11, "horse_name": "ノチェセラーダ",     "jockey": "ディー", "sire": "ドレフォン",       "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 8,  "odds": 24.3},
        {"horse_no": 12, "horse_name": "サガルマータ",       "jockey": "横山武", "sire": "コントレイル",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 7,  "odds": 20.9},
        {"horse_no": 13, "horse_name": "コスモギガンティア", "jockey": "矢野貴", "sire": "ダノンバラード",    "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 13, "odds": 82.7},
        {"horse_no": 14, "horse_name": "ヨカオウ",           "jockey": "岩田康", "sire": "キズナ",           "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 17, "odds": 134.9},
        {"horse_no": 15, "horse_name": "ノーブルサヴェージ", "jockey": "レーン", "sire": "リオンディーズ",    "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 2,  "odds": 5.1},
        {"horse_no": 16, "horse_name": "ゴーイントゥスカイ", "jockey": "武豊",   "sire": "コントレイル",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 4,  "odds": 9.4},
        {"horse_no": 17, "horse_name": "シャドウマスター",   "jockey": "北村友", "sire": "キタサンブラック",  "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 10, "odds": 36.7},
        {"horse_no": 18, "horse_name": "ケントン",           "jockey": "木幡巧", "sire": "リアルスティール",  "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 16, "odds": 129.2}
    ]
}

sys.argv = ['grade_race_predictor.py', '--race', json.dumps(RACE_DATA, ensure_ascii=False)]

exec(open(os.path.join(BASE_DIR, 'grade_race_predictor.py'), encoding='utf-8').read())
