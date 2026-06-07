# -*- coding: utf-8 -*-
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.abspath(__file__)))

OAKS_RACE = {
    "race_id": "20260524_oaks_g1",
    "race_name": "優駿牝馬（オークス）GⅠ",
    "grade": "G1",
    "venue": "東京",
    "course": "芝",
    "distance": 2400,
    "track_condition": "良",
    "num_horses": 18,
    "horses": [
        {"horse_no": 1,  "horse_name": "ミツカネベネラ",    "sire": "モーリス",         "jockey": "横山和生", "popularity": 18, "odds": 310.1},
        {"horse_no": 2,  "horse_name": "レイクラシック",     "sire": "キタサンブラック",   "jockey": "ディー",   "popularity": 10, "odds": 83.0},
        {"horse_no": 3,  "horse_name": "アランカール",       "sire": "エピファネイア",    "jockey": "武豊",    "popularity": 6,  "odds": 11.6},
        {"horse_no": 4,  "horse_name": "ロングトールサリー",  "sire": "キタサンブラック",   "jockey": "戸崎圭太", "popularity": 14, "odds": 156.8},
        {"horse_no": 5,  "horse_name": "リアライズルミナス",  "sire": "シルバーステート",   "jockey": "津村明秀", "popularity": 12, "odds": 92.7},
        {"horse_no": 6,  "horse_name": "ロンギングセリーヌ",  "sire": "モーリス",         "jockey": "石橋脩",  "popularity": 16, "odds": 209.7},
        {"horse_no": 7,  "horse_name": "スタニングレディ",    "sire": "ベンバトル",        "jockey": "三浦皇成", "popularity": 17, "odds": 232.0},
        {"horse_no": 8,  "horse_name": "スマートプリエール",  "sire": "エピファネイア",    "jockey": "原優介",  "popularity": 8,  "odds": 30.5},
        {"horse_no": 9,  "horse_name": "トリニティ",         "sire": "サートゥルナーリア", "jockey": "西村淳也", "popularity": 9,  "odds": 46.0},
        {"horse_no": 10, "horse_name": "スターアニス",       "sire": "ドレフォン",        "jockey": "松山弘平", "popularity": 1,  "odds": 3.2},
        {"horse_no": 11, "horse_name": "アメティスタ",       "sire": "キタサンブラック",   "jockey": "横山武史", "popularity": 13, "odds": 109.3},
        {"horse_no": 12, "horse_name": "ドリームコア",       "sire": "キズナ",           "jockey": "ルメール", "popularity": 5,  "odds": 7.5},
        {"horse_no": 13, "horse_name": "エンネ",            "sire": "キズナ",           "jockey": "坂井瑠星", "popularity": 3,  "odds": 6.8},
        {"horse_no": 14, "horse_name": "ソルパッサーレ",     "sire": "キズナ",           "jockey": "浜中俊",  "popularity": 15, "odds": 198.5},
        {"horse_no": 15, "horse_name": "アンジュドジョワ",   "sire": "キタサンブラック",   "jockey": "岩田望来", "popularity": 7,  "odds": 25.5},
        {"horse_no": 16, "horse_name": "ジュウリョクピエロ",  "sire": "オルフェーヴル",    "jockey": "今村聖奈", "popularity": 4,  "odds": 7.3},
        {"horse_no": 17, "horse_name": "スウィートハピネス",  "sire": "リアルインパクト",   "jockey": "高杉吏麒", "popularity": 11, "odds": 84.0},
        {"horse_no": 18, "horse_name": "ラフターラインズ",   "sire": "アルアイン",        "jockey": "レーン",  "popularity": 2,  "odds": 3.6},
    ]
}

import json
race_json = json.dumps(OAKS_RACE, ensure_ascii=False)
sys.argv = ['grade_race_predictor.py', '--race', race_json]
exec(open('grade_race_predictor.py', encoding='utf-8').read())
