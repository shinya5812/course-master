# -*- coding: utf-8 -*-
"""マーチステークス GⅢ 2026-03-29 予測実行"""
import sys, os, json
sys.argv = ['grade_race_predictor.py', '--race', json.dumps({
    "race_name": "マーチステークス GⅢ",
    "venue": "中山",
    "surface": "ダート",
    "distance": 1800,
    "track_cond": "稍重",
    "horses": [
        {"horse_no": 2,  "horse_name": "マテンロウスカイ",   "jockey": "横山典弘",  "sire": "モーリス",                "dam_sire": "スペシャルウィーク",    "age": 7, "weight": 59.0, "popularity": 6,  "odds": 11.0},
        {"horse_no": 3,  "horse_name": "ショウナンライシン",  "jockey": "田中勝春",  "sire": "エスケンデレヤ",          "dam_sire": "ウォーエンブレム",      "age": 6, "weight": 56.0, "popularity": 13, "odds": 59.2},
        {"horse_no": 4,  "horse_name": "ブレイクフォース",    "jockey": "菅原明良",  "sire": "アジアエクスプレス",      "dam_sire": "スマートファルコン",    "age": 7, "weight": 58.0, "popularity": 7,  "odds": 11.2},
        {"horse_no": 5,  "horse_name": "レヴォントゥレット",  "jockey": "横山武史",  "sire": "ロードカナロア",          "dam_sire": "ゴールドアリュール",    "age": 5, "weight": 57.0, "popularity": 4,  "odds": 7.1},
        {"horse_no": 6,  "horse_name": "ヴァルツァーシャル",  "jockey": "北村宏司",  "sire": "マクフィ",               "dam_sire": "ハーツクライ",          "age": 7, "weight": 58.5, "popularity": 2,  "odds": 6.4},
        {"horse_no": 7,  "horse_name": "アクションプラン",    "jockey": "津村明秀",  "sire": "リオンディーズ",          "dam_sire": "キングカメハメハ",      "age": 6, "weight": 56.0, "popularity": 5,  "odds": 7.9},
        {"horse_no": 8,  "horse_name": "ピュアキアン",        "jockey": "石川裕紀人","sire": "ホッコータルマエ",        "dam_sire": "クロフネ",              "age": 5, "weight": 56.0, "popularity": 12, "odds": 48.1},
        {"horse_no": 9,  "horse_name": "オメガギネス",        "jockey": "C.ルメール","sire": "ロゴタイプ",              "dam_sire": "メダグリアドーロ",      "age": 6, "weight": 59.0, "popularity": 1,  "odds": 5.5},
        {"horse_no": 10, "horse_name": "バスタードサフラン",  "jockey": "柴田大知",  "sire": "マジェスティックウォリアー","dam_sire": "エンパイアメーカー",    "age": 5, "weight": 54.0, "popularity": 14, "odds": 67.2},
        {"horse_no": 11, "horse_name": "ペイシャエス",        "jockey": "木幡巧也",  "sire": "エスポワールシチー",      "dam_sire": "ワイルドラッシュ",      "age": 7, "weight": 58.5, "popularity": 10, "odds": 20.1},
        {"horse_no": 12, "horse_name": "ハナウマビーチ",      "jockey": "江田照男",  "sire": "ゴールドドリーム",        "dam_sire": "ネオユニヴァース",      "age": 4, "weight": 55.0, "popularity": 11, "odds": 20.7},
        {"horse_no": 13, "horse_name": "ミッキーヌチバナ",    "jockey": "松岡正海",  "sire": "ダノンレジェンド",        "dam_sire": "ウオッカ",              "age": 8, "weight": 58.0, "popularity": 9,  "odds": 13.6},
        {"horse_no": 14, "horse_name": "チュウワクリスエス",  "jockey": "吉田豊",    "sire": "ルヴァンスレーヴ",        "dam_sire": "クリスエス",            "age": 4, "weight": 56.0, "popularity": 3,  "odds": 6.7},
        {"horse_no": 15, "horse_name": "サンデーファンデー",  "jockey": "松山弘平",  "sire": "スズカコーズウェイ",      "dam_sire": "エンドスウィープ",      "age": 6, "weight": 59.0, "popularity": 8,  "odds": 11.8},
        {"horse_no": 16, "horse_name": "コレペティトール",    "jockey": "丹内祐次",  "sire": "ジャスタウェイ",          "dam_sire": "フレンチデピュティ",    "age": 6, "weight": 56.0, "popularity": 15, "odds": 76.9}
    ]
}, ensure_ascii=False)]

exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grade_race_predictor.py'), encoding='utf-8').read())
