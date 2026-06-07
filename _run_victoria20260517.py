# -*- coding: utf-8 -*-
import sys, os
os.chdir(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')
sys.path.insert(0, r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')

import json

RACE = {
    "race_name": "ヴィクトリアマイル GⅠ",
    "venue": "東京",
    "surface": "芝",
    "distance": 1600,
    "track_cond": "良",
    "horses": [
        {"horse_no":  1, "horse_name": "カピリナ",         "jockey": "横山典弘", "sire": "ダンカーク",             "dam_sire": "マンハッタンカフェ",   "age": 5, "weight": 56.0, "popularity": 16, "odds": 80.5},
        {"horse_no":  2, "horse_name": "ワイドラトゥール", "jockey": "横山武史", "sire": "カリフォルニアクローム", "dam_sire": "アグネスタキオン",     "age": 5, "weight": 56.0, "popularity": 18, "odds": 132.2},
        {"horse_no":  3, "horse_name": "マピュース",       "jockey": "ゴンサルベス", "sire": "マインドユアビスケッツ", "dam_sire": "シンボリクリスエス", "age": 4, "weight": 56.0, "popularity": 14, "odds": 60.4},
        {"horse_no":  4, "horse_name": "エリカエクスプレス","jockey": "武豊",     "sire": "エピファネイア",         "dam_sire": "Galileo",             "age": 4, "weight": 56.0, "popularity":  6, "odds": 20.0},
        {"horse_no":  5, "horse_name": "ケリフレッドアスク","jockey": "ディーン・ホワイト", "sire": "ドゥラメンテ", "dam_sire": "ディープインパクト",  "age": 4, "weight": 56.0, "popularity": 17, "odds": 81.6},
        {"horse_no":  6, "horse_name": "ラヴァンダ",       "jockey": "岩田望来", "sire": "シルバーステート",        "dam_sire": "ベーカバド",           "age": 5, "weight": 56.0, "popularity":  7, "odds": 20.5},
        {"horse_no":  7, "horse_name": "クイーンズウォーク","jockey": "西村淳也", "sire": "キズナ",                "dam_sire": "Harlington",           "age": 5, "weight": 56.0, "popularity":  3, "odds":  8.4},
        {"horse_no":  8, "horse_name": "カムニャック",     "jockey": "川田将雅", "sire": "ブラックタイド",          "dam_sire": "サクラバクシンオー",   "age": 4, "weight": 56.0, "popularity":  2, "odds":  5.6},
        {"horse_no":  9, "horse_name": "ココナッツブラウン","jockey": "北村友一", "sire": "キタサンブラック",        "dam_sire": "キングカメハメハ",     "age": 6, "weight": 56.0, "popularity":  9, "odds": 25.3},
        {"horse_no": 10, "horse_name": "ドロップオブライト","jockey": "松若風馬", "sire": "トーセンラー",            "dam_sire": "フレンチデピュティ",   "age": 7, "weight": 56.0, "popularity": 15, "odds": 63.0},
        {"horse_no": 11, "horse_name": "ボンドガール",     "jockey": "丹内祐次", "sire": "ダイワメジャー",          "dam_sire": "Tizway",               "age": 5, "weight": 56.0, "popularity": 11, "odds": 31.3},
        {"horse_no": 12, "horse_name": "エンブロイダリー", "jockey": "ルメール",  "sire": "アドマイヤマーズ",       "dam_sire": "クロフネ",             "age": 4, "weight": 56.0, "popularity":  1, "odds":  2.2},
        {"horse_no": 13, "horse_name": "カナテープ",       "jockey": "松山弘平", "sire": "ロードカナロア",           "dam_sire": "Royal Applause",       "age": 7, "weight": 56.0, "popularity": 10, "odds": 30.8},
        {"horse_no": 14, "horse_name": "ジョスラン",       "jockey": "戸崎圭太", "sire": "エピファネイア",          "dam_sire": "ハーツクライ",         "age": 4, "weight": 56.0, "popularity":  8, "odds": 21.7},
        {"horse_no": 15, "horse_name": "アイサンサン",     "jockey": "幸英明",   "sire": "キズナ",                  "dam_sire": "シンボリクリスエス",   "age": 4, "weight": 56.0, "popularity": 12, "odds": 32.7},
        {"horse_no": 16, "horse_name": "ニシノティアモ",   "jockey": "津村明秀", "sire": "ドゥラメンテ",             "dam_sire": "コンデュイット",       "age": 5, "weight": 56.0, "popularity":  4, "odds": 10.8},
        {"horse_no": 17, "horse_name": "パラディレーヌ",   "jockey": "坂井瑠星", "sire": "キズナ",                  "dam_sire": "Closing Argument",     "age": 4, "weight": 56.0, "popularity": 13, "odds": 34.1},
        {"horse_no": 18, "horse_name": "チェルヴィニア",   "jockey": "レーン",   "sire": "ハービンジャー",           "dam_sire": "キングカメハメハ",     "age": 5, "weight": 56.0, "popularity":  5, "odds": 18.2},
    ]
}

sys.argv = ['grade_race_predictor.py', '--race', json.dumps(RACE, ensure_ascii=False)]
exec(open('grade_race_predictor.py', encoding='utf-8').read())
