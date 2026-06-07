# -*- coding: utf-8 -*-
import sys, os
os.chdir(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')
sys.argv = ['grade_race_predictor.py', '--race', '''
{
  "race_name": "平安ステークス GⅢ",
  "venue": "京都",
  "surface": "ダート",
  "distance": 1900,
  "track_cond": "稍重",
  "horses": [
    {"horse_no": 1,  "horse_name": "ポッドロゴ",        "jockey": "岩田望来",  "sire": "ロゴタイプ",        "dam_sire": "キングカメハメハ",    "age": 5, "weight": 57.0, "popularity": 15, "odds": 52.1},
    {"horse_no": 2,  "horse_name": "キョウキランブ",    "jockey": "菅原明良",  "sire": "エスケンデレヤ",    "dam_sire": "エンパイアメーカー",  "age": 4, "weight": 57.0, "popularity": 16, "odds": 75.3},
    {"horse_no": 3,  "horse_name": "リアライズカミオン","jockey": "坂井瑠星",  "sire": "American Pharoah", "dam_sire": "Smiling Tiger",       "age": 4, "weight": 57.0, "popularity": 3,  "odds": 6.0},
    {"horse_no": 4,  "horse_name": "ジューンアヲニヨシ","jockey": "浜中俊",    "sire": "キズナ",            "dam_sire": "ノボジャック",        "age": 6, "weight": 57.0, "popularity": 8,  "odds": 22.3},
    {"horse_no": 5,  "horse_name": "ヴァルツァーシャル","jockey": "斎藤新",    "sire": "マクフィ",          "dam_sire": "エンパイアメーカー",  "age": 7, "weight": 57.0, "popularity": 10, "odds": 23.3},
    {"horse_no": 6,  "horse_name": "ハグ",              "jockey": "高杉吏麒",  "sire": "Justify",           "dam_sire": "Afleet Alex",         "age": 4, "weight": 57.0, "popularity": 6,  "odds": 18.3},
    {"horse_no": 7,  "horse_name": "ゼットリアン",      "jockey": "団野大成",  "sire": "モーリス",          "dam_sire": "ネオユニヴァース",    "age": 6, "weight": 57.0, "popularity": 4,  "odds": 13.4},
    {"horse_no": 8,  "horse_name": "マルチヴァンヤール", "jockey": "角田大和",  "sire": "タートルボウル",    "dam_sire": "ブライアンズタイム",  "age": 8, "weight": 57.0, "popularity": 13, "odds": 39.2},
    {"horse_no": 9,  "horse_name": "メリークリスマス",  "jockey": "三浦皇成",  "sire": "ルヴァンスレーヴ",  "dam_sire": "スペシャルウィーク",  "age": 4, "weight": 57.0, "popularity": 11, "odds": 24.9},
    {"horse_no": 10, "horse_name": "シュラザック",      "jockey": "幸英明",    "sire": "モーニン",          "dam_sire": "ベーカバド",          "age": 4, "weight": 57.0, "popularity": 14, "odds": 51.8},
    {"horse_no": 11, "horse_name": "マルチタイトニット","jockey": "川田将雅",  "sire": "キズナ",            "dam_sire": "シンボリクリスエス",  "age": 6, "weight": 57.0, "popularity": 5,  "odds": 13.5},
    {"horse_no": 12, "horse_name": "サイモンザナドゥ",  "jockey": "池添謙一",  "sire": "アジアエクスプレス","dam_sire": "アグネスデジタル",    "age": 6, "weight": 57.0, "popularity": 9,  "odds": 22.6},
    {"horse_no": 13, "horse_name": "チュウワクリスエス","jockey": "武豊",      "sire": "ルヴァンスレーヴ",  "dam_sire": "サウスヴィグラス",    "age": 4, "weight": 57.0, "popularity": 12, "odds": 30.9},
    {"horse_no": 14, "horse_name": "ロードクロンヌ",    "jockey": "横山和生",  "sire": "リオンディーズ",    "dam_sire": "ブライアンズタイム",  "age": 5, "weight": 58.0, "popularity": 1,  "odds": 2.8},
    {"horse_no": 15, "horse_name": "ナルカミ",          "jockey": "戸崎圭太",  "sire": "サンダースノー",    "dam_sire": "ディープインパクト",  "age": 4, "weight": 59.0, "popularity": 2,  "odds": 5.1},
    {"horse_no": 16, "horse_name": "アクションプラン",  "jockey": "松山弘平",  "sire": "リオンディーズ",    "dam_sire": "タートルボウル",      "age": 6, "weight": 57.0, "popularity": 6,  "odds": 18.3}
  ]
}
''']
exec(open('grade_race_predictor.py', encoding='utf-8').read())
