# -*- coding: utf-8 -*-
"""2026-04-11 土曜重賞予測: NZT G2 + 阪神牝馬S G2"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# grade_race_predictor の main 相当を直接呼ぶ
import grade_race_predictor as gp

engine = gp.load_engine()

# ─── ニュージーランドT G2 (中山 芝1600m 稍重 15頭) ───
nzt = {
    "race_name": "ニュージーランドT GⅡ",
    "venue": "中山",
    "surface": "芝",
    "distance": 1600,
    "track_cond": "稍重",
    "horses": [
        {"horse_no":1,  "horse_name":"ハノハノ",          "jockey":"岩田康","sire":"モーリス",          "dam_sire":"",  "age":3,"weight":55.0,"popularity":9,  "odds":38.9},
        {"horse_no":2,  "horse_name":"マダックス",         "jockey":"吉田豊","sire":"マクフィ",           "dam_sire":"",  "age":3,"weight":57.0,"popularity":14, "odds":107.8},
        {"horse_no":3,  "horse_name":"レザベーション",     "jockey":"原",    "sire":"ダノンプレミアム",   "dam_sire":"",  "age":3,"weight":57.0,"popularity":8,  "odds":35.1},
        {"horse_no":4,  "horse_name":"ヒズマスターピース", "jockey":"佐々木","sire":"スクリーンヒーロー",  "dam_sire":"",  "age":3,"weight":55.0,"popularity":5,  "odds":12.3},
        {"horse_no":5,  "horse_name":"ジーネキング",       "jockey":"横山和","sire":"コントレイル",        "dam_sire":"",  "age":3,"weight":57.0,"popularity":3,  "odds":6.4},
        {"horse_no":6,  "horse_name":"シュペルリング",     "jockey":"ディーン","sire":"シスキン",          "dam_sire":"",  "age":3,"weight":57.0,"popularity":7,  "odds":28.4},
        {"horse_no":7,  "horse_name":"ロデオドライブ",     "jockey":"津村",  "sire":"サートゥルナーリア", "dam_sire":"",  "age":3,"weight":57.0,"popularity":1,  "odds":2.2},
        {"horse_no":8,  "horse_name":"スマイルカーブ",     "jockey":"大野",  "sire":"キズナ",            "dam_sire":"",  "age":3,"weight":55.0,"popularity":11, "odds":55.3},
        {"horse_no":9,  "horse_name":"ブルズアイプリンス", "jockey":"柴田善","sire":"フィエールマン",     "dam_sire":"",  "age":3,"weight":57.0,"popularity":12, "odds":68.4},
        {"horse_no":10, "horse_name":"ジーティーシンドウ", "jockey":"田辺",  "sire":"オルフェーヴル",     "dam_sire":"",  "age":3,"weight":57.0,"popularity":10, "odds":39.0},
        {"horse_no":11, "horse_name":"ゴーラッキー",       "jockey":"横山武","sire":"キタサンブラック",   "dam_sire":"",  "age":3,"weight":57.0,"popularity":2,  "odds":4.4},
        {"horse_no":12, "horse_name":"アルデトップガン",   "jockey":"三浦",  "sire":"ナダル",            "dam_sire":"",  "age":3,"weight":57.0,"popularity":6,  "odds":15.1},
        {"horse_no":13, "horse_name":"ガリレア",           "jockey":"石橋脩","sire":"モズアスコット",     "dam_sire":"",  "age":3,"weight":57.0,"popularity":13, "odds":91.4},
        {"horse_no":14, "horse_name":"ディールメーカー",   "jockey":"戸崎圭","sire":"イスラボニータ",     "dam_sire":"",  "age":3,"weight":57.0,"popularity":4,  "odds":8.7},
        {"horse_no":15, "horse_name":"ミリオンクラウン",   "jockey":"柴田大","sire":"リーチザクラウン",   "dam_sire":"",  "age":3,"weight":57.0,"popularity":15, "odds":158.8},
    ]
}

# ─── 阪神牝馬S G2 (阪神 芝1600m 稍重 10頭) ───
hanshin_himba = {
    "race_name": "阪神牝馬S GⅡ",
    "venue": "阪神",
    "surface": "芝",
    "distance": 1600,
    "track_cond": "稍重",
    "horses": [
        {"horse_no":1,  "horse_name":"エンブロイダリー",   "jockey":"ルメール","sire":"アドマイヤマーズ",           "dam_sire":"","age":4,"weight":57.0,"popularity":1,  "odds":2.7},
        {"horse_no":2,  "horse_name":"カピリナ",           "jockey":"横山典",  "sire":"ダンカーク",                "dam_sire":"","age":5,"weight":55.0,"popularity":5,  "odds":13.4},
        {"horse_no":3,  "horse_name":"ルージュソリテール", "jockey":"西塚",    "sire":"ロードカナロア",             "dam_sire":"","age":4,"weight":55.0,"popularity":6,  "odds":16.4},
        {"horse_no":4,  "horse_name":"ラヴァンダ",         "jockey":"岩田望",  "sire":"シルバーステート",           "dam_sire":"","age":5,"weight":56.0,"popularity":2,  "odds":3.9},
        {"horse_no":5,  "horse_name":"カムニャック",       "jockey":"川田",    "sire":"ブラックタイド",             "dam_sire":"","age":4,"weight":57.0,"popularity":4,  "odds":7.4},
        {"horse_no":6,  "horse_name":"アスコリピチェーノ", "jockey":"坂井",    "sire":"ダイワメジャー",             "dam_sire":"","age":5,"weight":57.0,"popularity":3,  "odds":4.0},
        {"horse_no":7,  "horse_name":"クランフォード",     "jockey":"幸",      "sire":"ブリックスアンドモルタル",   "dam_sire":"","age":5,"weight":55.0,"popularity":7,  "odds":25.3},
        {"horse_no":8,  "horse_name":"カナテープ",         "jockey":"松山",    "sire":"ロードカナロア",             "dam_sire":"","age":7,"weight":55.0,"popularity":8,  "odds":26.8},
        {"horse_no":9,  "horse_name":"エポックヴィーナス", "jockey":"酒井",    "sire":"ヴィクトワールピサ",         "dam_sire":"","age":5,"weight":55.0,"popularity":10, "odds":109.7},
        {"horse_no":10, "horse_name":"ビップデイジー",     "jockey":"西村淳",  "sire":"サトノダイヤモンド",         "dam_sire":"","age":4,"weight":55.0,"popularity":9,  "odds":43.8},
    ]
}

print("=" * 60)
pred_nzt = gp.run_prediction(engine, nzt)
chaos_nzt = gp.calc_chaos_index(nzt)
gp.print_result(nzt, pred_nzt, chaos_nzt)

print("\n" + "=" * 60)
pred_himba = gp.run_prediction(engine, hanshin_himba)
chaos_himba = gp.calc_chaos_index(hanshin_himba)
gp.print_result(hanshin_himba, pred_himba, chaos_himba)
