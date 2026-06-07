# -*- coding: utf-8 -*-
"""2026-04-19 日曜 重賞予測 - 皐月賞GⅠ + 福島牝馬SG3"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONIOENCODING'] = 'utf-8'

import io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from grade_race_predictor import load_engine, build_race_df, calc_chaos_index, run_prediction, print_result

engine = load_engine()

# ─────────────────────────────────────────────────────
# 皐月賞 GⅠ  中山 芝2000m 良 18頭
# ─────────────────────────────────────────────────────
SATSUKI = {
    "race_name": "皐月賞 GⅠ",
    "venue": "中山",
    "surface": "芝",
    "distance": 2000,
    "track_cond": "良",
    "horses": [
        {"horse_no":  1, "horse_name": "カヴァレリッツォ",  "jockey": "レーン",   "sire": "サートゥルナーリア", "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  4, "odds":   6.8},
        {"horse_no":  2, "horse_name": "サウンドムーブ",    "jockey": "団野",     "sire": "リアルスティール",   "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 16, "odds": 102.1},
        {"horse_no":  3, "horse_name": "サノノグレーター",  "jockey": "田辺",     "sire": "グレーターロンドン", "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 14, "odds":  57.9},
        {"horse_no":  4, "horse_name": "ロブチェン",        "jockey": "松山",     "sire": "ワールドプレミア",   "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  1, "odds":   4.4},
        {"horse_no":  5, "horse_name": "アスクエジンバラ",  "jockey": "岩田康",   "sire": "リオンディーズ",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 12, "odds":  37.2},
        {"horse_no":  6, "horse_name": "フォルテアンジェロ","jockey": "荻野極",   "sire": "フィエールマン",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 11, "odds":  26.9},
        {"horse_no":  7, "horse_name": "ロードフィレール",  "jockey": "武豊",     "sire": "キズナ",             "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 15, "odds":  60.3},
        {"horse_no":  8, "horse_name": "マテンロウゲイル",  "jockey": "横山和",   "sire": "エピファネイア",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  6, "odds":  13.5},
        {"horse_no":  9, "horse_name": "ライヒスアドラー",  "jockey": "佐々木",   "sire": "シスキン",           "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  9, "odds":  23.5},
        {"horse_no": 10, "horse_name": "ラージアンサンブル","jockey": "高杉",     "sire": "ベンバトル",         "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 18, "odds": 153.4},
        {"horse_no": 11, "horse_name": "パントルナイーフ",  "jockey": "ルメール", "sire": "キズナ",             "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  7, "odds":  15.6},
        {"horse_no": 12, "horse_name": "グリーンエナジー",  "jockey": "戸崎圭",   "sire": "スワーヴリチャード", "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  2, "odds":   4.5},
        {"horse_no": 13, "horse_name": "アクロフェイズ",    "jockey": "西村淳",   "sire": "ロードカナロア",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 17, "odds": 103.6},
        {"horse_no": 14, "horse_name": "ゾロアストロ",      "jockey": "岩田望",   "sire": "モーリス",           "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 10, "odds":  24.9},
        {"horse_no": 15, "horse_name": "リアライズシリウス","jockey": "津村",     "sire": "ポエティックフレア", "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  3, "odds":   6.3},
        {"horse_no": 16, "horse_name": "アルトラムス",      "jockey": "横山武",   "sire": "イスラボニータ",     "dam_sire": "", "age": 3, "weight": 57.0, "popularity": 13, "odds":  49.6},
        {"horse_no": 17, "horse_name": "アドマイヤクワッズ","jockey": "坂井",     "sire": "リアルスティール",   "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  8, "odds":  15.7},
        {"horse_no": 18, "horse_name": "バステール",        "jockey": "川田",     "sire": "キタサンブラック",   "dam_sire": "", "age": 3, "weight": 57.0, "popularity":  5, "odds":  13.3},
    ]
}

# ─────────────────────────────────────────────────────
# 福島牝馬S GⅢ  福島 芝1800m 良 16頭
# ─────────────────────────────────────────────────────
FUKUSHIMA_HIMBA = {
    "race_name": "福島牝馬ステークス GⅢ",
    "venue": "福島",
    "surface": "芝",
    "distance": 1800,
    "track_cond": "良",
    "horses": [
        {"horse_no":  1, "horse_name": "エラトー",        "jockey": "斎藤",   "sire": "Saxon Warrior",       "dam_sire": "", "age": 5, "weight": 55.0, "popularity":  8, "odds":  19.1},
        {"horse_no":  2, "horse_name": "フィールシンパシー","jockey": "横山琉", "sire": "ベーカバド",           "dam_sire": "", "age": 7, "weight": 55.0, "popularity": 13, "odds":  51.4},
        {"horse_no":  3, "horse_name": "パラディレーヌ",  "jockey": "丹内",   "sire": "キズナ",               "dam_sire": "", "age": 4, "weight": 55.0, "popularity":  1, "odds":   3.1},
        {"horse_no":  4, "horse_name": "アンリーロード",  "jockey": "富田",   "sire": "リアルスティール",     "dam_sire": "", "age": 6, "weight": 55.0, "popularity": 16, "odds": 135.3},
        {"horse_no":  5, "horse_name": "パレハ",          "jockey": "田山",   "sire": "サトノクラウン",       "dam_sire": "", "age": 5, "weight": 55.0, "popularity":  9, "odds":  20.7},
        {"horse_no":  6, "horse_name": "ミッキーゴージャス","jockey": "横山典", "sire": "ミッキーロケット",     "dam_sire": "", "age": 6, "weight": 55.0, "popularity":  4, "odds":   9.3},
        {"horse_no":  7, "horse_name": "レディマリオン",  "jockey": "小沢",   "sire": "ハービンジャー",       "dam_sire": "", "age": 5, "weight": 55.0, "popularity": 15, "odds":  77.6},
        {"horse_no":  8, "horse_name": "ブラウンラチェット","jockey": "武藤",   "sire": "キズナ",               "dam_sire": "", "age": 4, "weight": 55.0, "popularity": 12, "odds":  50.3},
        {"horse_no":  9, "horse_name": "コンドゥイア",    "jockey": "鷲頭",   "sire": "フォーウィールドライブ","dam_sire": "", "age": 4, "weight": 55.0, "popularity": 14, "odds":  72.7},
        {"horse_no": 10, "horse_name": "カネラフィーナ",  "jockey": "石川",   "sire": "Frankel",              "dam_sire": "", "age": 4, "weight": 55.0, "popularity":  3, "odds":   7.2},
        {"horse_no": 11, "horse_name": "ケリフレッドアスク","jockey": "西塚",   "sire": "ドゥラメンテ",         "dam_sire": "", "age": 4, "weight": 57.0, "popularity": 10, "odds":  35.0},
        {"horse_no": 12, "horse_name": "レーゼドラマ",    "jockey": "丸山",   "sire": "キズナ",               "dam_sire": "", "age": 4, "weight": 55.0, "popularity":  6, "odds":  14.0},
        {"horse_no": 13, "horse_name": "コガネノソラ",    "jockey": "菊沢",   "sire": "ゴールドシップ",       "dam_sire": "", "age": 5, "weight": 55.0, "popularity":  7, "odds":  18.3},
        {"horse_no": 14, "horse_name": "ジョイフルニュース","jockey": "大野",   "sire": "ロードカナロア",       "dam_sire": "", "age": 4, "weight": 55.0, "popularity":  2, "odds":   3.9},
        {"horse_no": 15, "horse_name": "テレサ",          "jockey": "松若",   "sire": "アドマイヤマーズ",     "dam_sire": "", "age": 4, "weight": 55.0, "popularity":  5, "odds":  11.9},
        {"horse_no": 16, "horse_name": "カニキュル",      "jockey": "杉原",   "sire": "エピファネイア",       "dam_sire": "", "age": 5, "weight": 55.0, "popularity": 11, "odds":  37.4},
    ]
}

print("=" * 76)
print("  2026-04-19（日） 重賞予測レポート")
print("=" * 76)

for race_data in [SATSUKI, FUKUSHIMA_HIMBA]:
    df    = build_race_df(race_data)
    chaos = calc_chaos_index(race_data)
    pred  = run_prediction(engine, race_data)
    print_result(race_data, pred, chaos)
    print()
