# -*- coding: utf-8 -*-
"""高松宮記念 2026-03-29 予測実行スクリプト"""
import sys, os, json
sys.argv = ['grade_race_predictor.py', '--race', json.dumps({
    "race_name": "高松宮記念 GⅠ",
    "venue": "中京",
    "surface": "芝",
    "distance": 1200,
    "track_cond": "良",
    "horses": [
        {"horse_no": 1,  "horse_name": "パンジャタワー",         "jockey": "松山弘平",   "sire": "タワーオブロンドン",       "dam_sire": "ヴィクトワールピサ",     "age": 4, "weight": 58.0, "popularity": 3,  "odds": 4.8},
        {"horse_no": 2,  "horse_name": "ビッグシーザー",          "jockey": "西村淳也",   "sire": "ビッグアーサー",           "dam_sire": "Tale of Ekati",         "age": 6, "weight": 58.0, "popularity": 13, "odds": 46.5},
        {"horse_no": 3,  "horse_name": "エーティーマクフィ",      "jockey": "富田暁",     "sire": "マクフィ",                 "dam_sire": "ハーツクライ",           "age": 7, "weight": 58.0, "popularity": 8,  "odds": 18.9},
        {"horse_no": 4,  "horse_name": "ダノンマッキンリー",      "jockey": "高杉吏麒",   "sire": "モーリス",                 "dam_sire": "Holy Roman Emperor",    "age": 5, "weight": 58.0, "popularity": 15, "odds": 54.1},
        {"horse_no": 5,  "horse_name": "ヤマニンアルリフラ",      "jockey": "団野大成",   "sire": "イスラボニータ",           "dam_sire": "スウェプトオーヴァーボード", "age": 5, "weight": 58.0, "popularity": 11, "odds": 35.2},
        {"horse_no": 6,  "horse_name": "レッドモンレーヴ",        "jockey": "酒井学",     "sire": "ロードカナロア",           "dam_sire": "ディープインパクト",     "age": 7, "weight": 58.0, "popularity": 12, "odds": 41.9},
        {"horse_no": 7,  "horse_name": "ヨシノイースター",        "jockey": "田辺裕信",   "sire": "ルーラーシップ",           "dam_sire": "ゼンノロブロイ",         "age": 8, "weight": 58.0, "popularity": 16, "odds": 61.6},
        {"horse_no": 8,  "horse_name": "ウインカーネリアン",      "jockey": "三浦皇成",   "sire": "スクリーンヒーロー",       "dam_sire": "マイネルラヴ",           "age": 9, "weight": 58.0, "popularity": 7,  "odds": 16.7},
        {"horse_no": 9,  "horse_name": "サトノレーヴ",            "jockey": "C.ルメール", "sire": "ロードカナロア",           "dam_sire": "サクラバクシンオー",     "age": 7, "weight": 58.0, "popularity": 2,  "odds": 4.4},
        {"horse_no": 10, "horse_name": "ママコチャ",              "jockey": "川田将雅",   "sire": "クロフネ",                 "dam_sire": "キングカメハメハ",       "age": 7, "weight": 56.0, "popularity": 4,  "odds": 8.7},
        {"horse_no": 11, "horse_name": "ララマセラシオン",        "jockey": "丸田恭介",   "sire": "カリフォルニアクローム",   "dam_sire": "クロフネ",               "age": 5, "weight": 58.0, "popularity": 14, "odds": 50.6},
        {"horse_no": 12, "horse_name": "ピューロマジック",        "jockey": "北村友一",   "sire": "アジアエクスプレス",       "dam_sire": "ディープインパクト",     "age": 5, "weight": 56.0, "popularity": 18, "odds": 83.7},
        {"horse_no": 13, "horse_name": "ナムラクレア",            "jockey": "浜中俊",     "sire": "ミッキーアイル",           "dam_sire": "Storm Cat",             "age": 7, "weight": 56.0, "popularity": 1,  "odds": 4.2},
        {"horse_no": 14, "horse_name": "レイピア",                "jockey": "丸山元気",   "sire": "タワーオブロンドン",       "dam_sire": "エンパイアメーカー",     "age": 4, "weight": 58.0, "popularity": 6,  "odds": 15.8},
        {"horse_no": 15, "horse_name": "マルガイインビンシブルパパ", "jockey": "佐々木大輔", "sire": "Shalaa",                "dam_sire": "Canford Cliffs",        "age": 5, "weight": 58.0, "popularity": 9,  "odds": 22.5},
        {"horse_no": 16, "horse_name": "フィオライア",            "jockey": "太宰啓介",   "sire": "ファインニードル",         "dam_sire": "サクラバクシンオー",     "age": 5, "weight": 56.0, "popularity": 17, "odds": 74.0},
        {"horse_no": 17, "horse_name": "ペアポルックス",          "jockey": "岩田康誠",   "sire": "キンシャサノキセキ",       "dam_sire": "ディープインパクト",     "age": 5, "weight": 58.0, "popularity": 10, "odds": 31.6},
        {"horse_no": 18, "horse_name": "マルガイジューンブレア",  "jockey": "武豊",       "sire": "American Pharoah",         "dam_sire": "Galileo",               "age": 5, "weight": 56.0, "popularity": 5,  "odds": 15.7}
    ]
}, ensure_ascii=False)]

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grade_race_predictor.py'), encoding='utf-8').read())
