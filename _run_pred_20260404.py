# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json

# ダービー卿チャレンジトロフィー（GⅢ）中山・芝1600m・良
derby_kyo = {
    "race_name": "ダービー卿チャレンジトロフィー（GⅢ）",
    "venue": "中山",
    "surface": "芝",
    "distance": 1600,
    "condition": "良",
    "num_horses": 16,
    "horses": [
        {"horse_no": 1,  "horse_name": "ゾンニッヒ",        "sire_name": "ラブリーデイ",     "popularity": 10, "odds": 13.4, "jockey": "団野大成",   "weight": 57.5},
        {"horse_no": 2,  "horse_name": "ミニトランザット",   "sire_name": "エピファネイア",   "popularity": 1,  "odds": 6.7,  "jockey": "西村淳也",   "weight": 58.0},
        {"horse_no": 3,  "horse_name": "エンペラーズソード", "sire_name": "ドレフォン",       "popularity": 7,  "odds": 11.8, "jockey": "荻野極",     "weight": 57.0},
        {"horse_no": 4,  "horse_name": "メタルスピード",     "sire_name": "シルバーステート", "popularity": 3,  "odds": 8.8,  "jockey": "岩田康誠",   "weight": 55.0},
        {"horse_no": 5,  "horse_name": "ブエナオンダ",       "sire_name": "リオンディーズ",   "popularity": 11, "odds": 13.8, "jockey": "横山武史",   "weight": 58.0},
        {"horse_no": 6,  "horse_name": "マテンロウオリオン", "sire_name": "ダイワメジャー",   "popularity": 4,  "odds": 9.1,  "jockey": "横山典弘",   "weight": 56.0},
        {"horse_no": 7,  "horse_name": "タイムトゥヘヴン",   "sire_name": "ロードカナロア",   "popularity": 14, "odds": 22.6, "jockey": "柴田善臣",   "weight": 56.0},
        {"horse_no": 8,  "horse_name": "ファーヴェント",     "sire_name": "ハーツクライ",     "popularity": 2,  "odds": 7.6,  "jockey": "松山弘平",   "weight": 56.0},
        {"horse_no": 9,  "horse_name": "エエヤン",           "sire_name": "シルバーステート", "popularity": 15, "odds": 94.2, "jockey": "伊藤工真",   "weight": 56.0},
        {"horse_no": 10, "horse_name": "ケイアイセナ",       "sire_name": "ディープインパクト","popularity": 6,  "odds": 11.4, "jockey": "藤岡康太",   "weight": 56.0},
        {"horse_no": 11, "horse_name": "スズハローム",       "sire_name": "サトノダイヤモンド","popularity": 13, "odds": 18.3, "jockey": "永野猛蔵",   "weight": 56.0},
        {"horse_no": 12, "horse_name": "ダディーズビビッド", "sire_name": "キズナ",           "popularity": 16, "odds": 100.5,"jockey": "千田輝彦",   "weight": 56.0},
        {"horse_no": 13, "horse_name": "イミグラントソング", "sire_name": "マクフィ",         "popularity": 8,  "odds": 12.3, "jockey": "田辺裕信",   "weight": 56.0},
        {"horse_no": 14, "horse_name": "ジュンブロッサム",   "sire_name": "ワールドエース",   "popularity": 12, "odds": 16.6, "jockey": "川田将雅",   "weight": 56.0},
        {"horse_no": 15, "horse_name": "シリウスコルト",     "sire_name": "マクフィ",         "popularity": 5,  "odds": 10.7, "jockey": "菅原明良",   "weight": 56.0},
        {"horse_no": 16, "horse_name": "サイルーン",         "sire_name": "ディープインパクト","popularity": 9,  "odds": 13.0, "jockey": "戸崎圭太",   "weight": 56.0},
    ]
}

# チャーチルダウンズカップ（GⅢ）阪神・芝1600m・良
churchill = {
    "race_name": "チャーチルダウンズカップ（GⅢ）",
    "venue": "阪神",
    "surface": "芝",
    "distance": 1600,
    "condition": "良",
    "num_horses": 14,
    "horses": [
        {"horse_no": 1,  "horse_name": "ストームサンダー",   "sire_name": "ヘンリーバローズ",  "popularity": 11, "odds": 55.5,  "jockey": "角田大河",   "weight": 57.0},
        {"horse_no": 2,  "horse_name": "メイショウソラリス", "sire_name": "シスキン",          "popularity": 12, "odds": 63.9,  "jockey": "富田暁",     "weight": 57.0},
        {"horse_no": 3,  "horse_name": "リゾートアイランド", "sire_name": "イスラボニータ",    "popularity": 5,  "odds": 8.6,   "jockey": "横山典弘",   "weight": 57.0},
        {"horse_no": 4,  "horse_name": "エイシンティザー",   "sire_name": "モズアスコット",    "popularity": 8,  "odds": 19.4,  "jockey": "丹内祐次",   "weight": 57.0},
        {"horse_no": 5,  "horse_name": "シーミハットク",     "sire_name": "オルフェーヴル",    "popularity": 7,  "odds": 18.0,  "jockey": "藤岡佑介",   "weight": 57.0},
        {"horse_no": 6,  "horse_name": "サンダーストラック", "sire_name": "ロードカナロア",    "popularity": 2,  "odds": 3.4,   "jockey": "川田将雅",   "weight": 57.0},
        {"horse_no": 7,  "horse_name": "サトノセプター",     "sire_name": "Kingman",           "popularity": 6,  "odds": 14.8,  "jockey": "坂井瑠星",   "weight": 57.0},
        {"horse_no": 8,  "horse_name": "アンドゥーリル",     "sire_name": "サートゥルナーリア","popularity": 1,  "odds": 3.2,   "jockey": "武豊",       "weight": 57.0},
        {"horse_no": 9,  "horse_name": "クールデイトナ",     "sire_name": "フォーウィールドライブ","popularity": 12, "odds": 63.9,"jockey": "岩田康誠",   "weight": 57.0},
        {"horse_no": 10, "horse_name": "バルセシート",       "sire_name": "キズナ",            "popularity": 4,  "odds": 8.3,   "jockey": "西村淳也",   "weight": 57.0},
        {"horse_no": 11, "horse_name": "マルガイユウファラオ","sire_name": "American Pharoah", "popularity": 14, "odds": 146.0, "jockey": "松田大作",   "weight": 57.0},
        {"horse_no": 12, "horse_name": "サーディンラン",     "sire_name": "レイデオロ",        "popularity": 10, "odds": 53.1,  "jockey": "藤懸貴志",   "weight": 57.0},
        {"horse_no": 13, "horse_name": "ファンクション",     "sire_name": "アルアイン",        "popularity": 9,  "odds": 48.9,  "jockey": "田辺裕信",   "weight": 57.0},
        {"horse_no": 14, "horse_name": "アスクイキゴミ",     "sire_name": "ロードカナロア",    "popularity": 3,  "odds": 6.7,   "jockey": "坂井瑠星",   "weight": 57.0},
    ]
}

import grade_race_predictor as gp

engine = gp.load_engine()

for race in [derby_kyo, churchill]:
    pred = gp.run_prediction(engine, race)
    chaos = gp.calc_chaos_index(race)
    gp.print_result(race, pred, chaos)
    print()
