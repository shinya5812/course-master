# -*- coding: utf-8 -*-
import sys, os, json
os.chdir(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')
sys.argv = ['grade_race_predictor.py', '--race', json.dumps({
    "race_name": "大阪杯 GⅠ",
    "venue": "阪神",
    "surface": "芝",
    "distance": 2000,
    "track_cond": "稍重",
    "horses": [
        {"horse_no": 1,  "horse_name": "サンストックトン",  "jockey": "高杉吏麒",   "sire": "ワールドエース",    "dam_sire": "キングカメハメハ",    "age": 7, "weight": 58.0, "popularity": 15, "odds": 189.8},
        {"horse_no": 2,  "horse_name": "マテンロウレオ",    "jockey": "横山典弘",   "sire": "ハーツクライ",      "dam_sire": "ブライアンズタイム",    "age": 7, "weight": 58.0, "popularity": 11, "odds": 58.2},
        {"horse_no": 3,  "horse_name": "セイウンハーデス",  "jockey": "幸英明",     "sire": "シルバーステート",   "dam_sire": "マンハッタンカフェ",    "age": 7, "weight": 58.0, "popularity": 10, "odds": 47.2},
        {"horse_no": 4,  "horse_name": "ダノンデサイル",    "jockey": "坂井瑠星",   "sire": "エピファネイア",     "dam_sire": "Congrats",             "age": 5, "weight": 58.0, "popularity":  2, "odds": 4.4},
        {"horse_no": 5,  "horse_name": "ショウヘイ",        "jockey": "川田将雅",   "sire": "サートゥルナーリア", "dam_sire": "オルフェーヴル",        "age": 4, "weight": 58.0, "popularity":  4, "odds": 6.0},
        {"horse_no": 6,  "horse_name": "メイショウタバル",  "jockey": "武豊",       "sire": "ゴールドシップ",     "dam_sire": "フレンチデピュティ",    "age": 5, "weight": 58.0, "popularity":  3, "odds": 4.5},
        {"horse_no": 7,  "horse_name": "エコロディノス",    "jockey": "池添謙一",   "sire": "キタサンブラック",   "dam_sire": "Generous",             "age": 4, "weight": 58.0, "popularity":  6, "odds": 34.1},
        {"horse_no": 8,  "horse_name": "エコロヴァルツ",    "jockey": "浜中俊",     "sire": "ブラックタイド",     "dam_sire": "キングカメハメハ",     "age": 5, "weight": 58.0, "popularity":  7, "odds": 35.2},
        {"horse_no": 9,  "horse_name": "ヨーホーレイク",    "jockey": "西村淳也",   "sire": "ディープインパクト", "dam_sire": "フレンチデピュティ",    "age": 8, "weight": 58.0, "popularity":  9, "odds": 46.6},
        {"horse_no": 10, "horse_name": "ボルドグフーシュ",  "jockey": "松山弘平",   "sire": "スクリーンヒーロー", "dam_sire": "Layman",               "age": 7, "weight": 58.0, "popularity": 14, "odds": 128.5},
        {"horse_no": 11, "horse_name": "デビットバローズ",  "jockey": "岩田望来",   "sire": "ロードカナロア",     "dam_sire": "サンデーサイレンス",    "age": 7, "weight": 58.0, "popularity":  8, "odds": 41.7},
        {"horse_no": 12, "horse_name": "レーベンスティール","jockey": "C.ルメール", "sire": "リアルスティール",   "dam_sire": "トウカイテイオー",     "age": 6, "weight": 58.0, "popularity":  5, "odds": 8.2},
        {"horse_no": 13, "horse_name": "ファウストラーゼン","jockey": "岩田康誠",   "sire": "モズアスコット",     "dam_sire": "スペシャルウィーク",    "age": 4, "weight": 58.0, "popularity": 12, "odds": 59.2},
        {"horse_no": 14, "horse_name": "タガノデュード",    "jockey": "古川吉洋",   "sire": "ヤマカツエース",     "dam_sire": "ハーツクライ",          "age": 5, "weight": 58.0, "popularity": 13, "odds": 66.1},
        {"horse_no": 15, "horse_name": "クロワデュノール",  "jockey": "北村友一",   "sire": "キタサンブラック",   "dam_sire": "Cape Cross",           "age": 4, "weight": 58.0, "popularity":  1, "odds": 2.9}
    ]
}, ensure_ascii=False)]

exec(open('grade_race_predictor.py', encoding='utf-8').read())
