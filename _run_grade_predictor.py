# -*- coding: utf-8 -*-
"""今日（2026-03-28）の重賞2レースを grade_race_predictor.py で予測する"""
import sys, os, io, json

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.argv = ['grade_race_predictor.py']
sys.path.insert(0, BASE_DIR)

# grade_race_predictor からモジュールを直接インポート
from grade_race_predictor import load_engine, calc_chaos_index, run_prediction, print_result, detect_grade

# ────────────────────────────────────────────────────────────
# レース1: 日経賞 GⅡ  中山 芝2500m 稍重  15頭
# ────────────────────────────────────────────────────────────
race_nikkei = {
    "race_name":  "日経賞 GⅡ",
    "venue":      "中山",
    "surface":    "芝",
    "distance":   2500,
    "track_cond": "稍重",
    "class_code": 800,
    "horses": [
        {"horse_no":  1, "horse_name": "ミクニインスパイア",  "jockey": "丹内祐次",    "sire": "アドマイヤマーズ",    "dam_sire": "ティンバーカントリー", "age": 4, "weight": 56.0, "popularity":  2, "odds":  4.3},
        {"horse_no":  2, "horse_name": "ホールネス",          "jockey": "M.ディー",    "sire": "Lope de Vega",        "dam_sire": "Golan",               "age": 6, "weight": 55.0, "popularity": 13, "odds": 51.9},
        {"horse_no":  3, "horse_name": "クリスマスパレード",  "jockey": "石川裕紀人",  "sire": "キタサンブラック",    "dam_sire": "Blame",               "age": 5, "weight": 55.0, "popularity":  9, "odds": 29.4},
        {"horse_no":  4, "horse_name": "エヒト",              "jockey": "川田将雅",    "sire": "ルーラーシップ",      "dam_sire": "ディープインパクト",   "age": 9, "weight": 57.0, "popularity": 10, "odds": 29.5},
        {"horse_no":  5, "horse_name": "アスクナイスショー",  "jockey": "田辺裕信",    "sire": "シルバーステート",    "dam_sire": "アドマイヤムーン",     "age": 5, "weight": 57.0, "popularity":  7, "odds": 16.1},
        {"horse_no":  6, "horse_name": "リビアングラス",      "jockey": "三浦皇成",    "sire": "キズナ",              "dam_sire": "Curlin",               "age": 6, "weight": 57.0, "popularity": 11, "odds": 33.7},
        {"horse_no":  7, "horse_name": "コスモキュランダ",    "jockey": "横山武史",    "sire": "アルアイン",          "dam_sire": "Southern Image",       "age": 5, "weight": 57.0, "popularity":  1, "odds":  3.5},
        {"horse_no":  8, "horse_name": "ホウオウノーサイド",  "jockey": "杉原誠人",    "sire": "キングカメハメハ",    "dam_sire": "ヘクタープロテクター", "age": 7, "weight": 57.0, "popularity": 15, "odds": 214.6},
        {"horse_no":  9, "horse_name": "マイネルケレリウス",  "jockey": "松岡正海",    "sire": "ルーラーシップ",      "dam_sire": "アグネスタキオン",     "age": 6, "weight": 57.0, "popularity": 12, "odds": 36.0},
        {"horse_no": 10, "horse_name": "シャイニングソード",  "jockey": "西村淳也",    "sire": "Frankel",             "dam_sire": "Monsun",               "age": 5, "weight": 57.0, "popularity":  6, "odds": 13.4},
        {"horse_no": 11, "horse_name": "ミステリーウェイ",    "jockey": "松本大輝",    "sire": "ジャスタウェイ",      "dam_sire": "High Chaparral",       "age": 8, "weight": 58.0, "popularity":  8, "odds": 19.2},
        {"horse_no": 12, "horse_name": "チャックネイト",      "jockey": "大野拓弥",    "sire": "ハーツクライ",        "dam_sire": "Dynaformer",           "age": 8, "weight": 57.0, "popularity":  5, "odds": 10.4},
        {"horse_no": 13, "horse_name": "ブレイヴロッカー",    "jockey": "荻野極",      "sire": "ドゥラメンテ",        "dam_sire": "Elusive City",         "age": 6, "weight": 57.0, "popularity": 14, "odds": 59.0},
        {"horse_no": 14, "horse_name": "ローシャムパーク",    "jockey": "C.ルメール",  "sire": "ハービンジャー",      "dam_sire": "キングカメハメハ",     "age": 7, "weight": 57.0, "popularity":  3, "odds":  6.3},
        {"horse_no": 15, "horse_name": "マイユニバース",      "jockey": "横山典弘",    "sire": "レイデオロ",          "dam_sire": "ネオユニヴァース",     "age": 4, "weight": 56.0, "popularity":  4, "odds":  7.4},
    ]
}

# ────────────────────────────────────────────────────────────
# レース2: 毎日杯 GⅢ  阪神 芝1800m 良  7頭
# ────────────────────────────────────────────────────────────
race_mainichi = {
    "race_name":  "毎日杯 GⅢ",
    "venue":      "阪神",
    "surface":    "芝",
    "distance":   1800,
    "track_cond": "良",
    "class_code": 800,
    "horses": [
        {"horse_no": 1, "horse_name": "フレイムスター",      "jockey": "団野大成",    "sire": "ドレフォン",          "dam_sire": "ディープインパクト",   "age": 3, "weight": 57.0, "popularity": 7, "odds": 36.4},
        {"horse_no": 2, "horse_name": "カフジエメンタール",  "jockey": "武豊",        "sire": "ポエティックフレア",  "dam_sire": "キングカメハメハ",     "age": 3, "weight": 57.0, "popularity": 2, "odds":  3.0},
        {"horse_no": 3, "horse_name": "ローベルクランツ",    "jockey": "松山弘平",    "sire": "サトノダイヤモンド",  "dam_sire": "キングカメハメハ",     "age": 3, "weight": 57.0, "popularity": 4, "odds":  5.1},
        {"horse_no": 4, "horse_name": "アルトラムス",        "jockey": "岩田望来",    "sire": "イスラボニータ",      "dam_sire": "スクリーンヒーロー",   "age": 3, "weight": 57.0, "popularity": 1, "odds":  2.7},
        {"horse_no": 5, "horse_name": "ブリガンティン",      "jockey": "原優介",      "sire": "ベンバトル",          "dam_sire": "ステイゴールド",       "age": 3, "weight": 57.0, "popularity": 5, "odds": 14.7},
        {"horse_no": 6, "horse_name": "ウップヘリーア",      "jockey": "吉村誠之助",  "sire": "エピファネイア",      "dam_sire": "キングカメハメハ",     "age": 3, "weight": 57.0, "popularity": 3, "odds":  4.8},
        {"horse_no": 7, "horse_name": "シーズザスローン",    "jockey": "幸英明",      "sire": "キズナ",              "dam_sire": "Frankel",              "age": 3, "weight": 57.0, "popularity": 6, "odds": 15.6},
    ]
}

# ────────────────────────────────────────────────────────────
# エンジン読み込み（1回だけ）
# ────────────────────────────────────────────────────────────
print("=" * 68)
print("  COURSE MASTER v7.3  重賞予測  2026-03-28（土）")
print("=" * 68)
print("エンジン読み込み中...")
engine = load_engine()

# ────────────────────────────────────────────────────────────
# レース1: 日経賞
# ────────────────────────────────────────────────────────────
grade = detect_grade(race_nikkei["race_name"])
print(f"\n[{grade}] {race_nikkei['race_name']}  予測開始...")
chaos1 = calc_chaos_index(race_nikkei)
pred1  = run_prediction(engine, race_nikkei)
print_result(race_nikkei, pred1, chaos1)

# ────────────────────────────────────────────────────────────
# レース2: 毎日杯
# ────────────────────────────────────────────────────────────
grade2 = detect_grade(race_mainichi["race_name"])
print(f"[{grade2}] {race_mainichi['race_name']}  予測開始...")
chaos2 = calc_chaos_index(race_mainichi)
pred2  = run_prediction(engine, race_mainichi)
print_result(race_mainichi, pred2, chaos2)
