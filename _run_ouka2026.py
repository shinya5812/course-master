# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster')
sys.argv = ['grade_race_predictor.py', '--race', r'''
{
  "race_name": "桜花賞(G1)",
  "venue": "阪神",
  "surface": "芝",
  "distance": 1600,
  "track_cond": "良",
  "grade": "G1",
  "race_date": "2026-04-12",
  "horses": [
    {"horse_no":1,  "horse_name":"フェスティバルヒル", "sire":"サートゥルナーリア", "jockey":"坂井瑠星", "popularity":7,  "odds":22.4},
    {"horse_no":2,  "horse_name":"サンアントワーヌ",   "sire":"ドレフォン",         "jockey":"荻野極",   "popularity":8,  "odds":27.4},
    {"horse_no":3,  "horse_name":"ディアダイヤモンド", "sire":"サートゥルナーリア", "jockey":"戸崎圭太", "popularity":6,  "odds":18.0},
    {"horse_no":4,  "horse_name":"エレガンスアスク",   "sire":"ポエティックフレア", "jockey":"岩田望来", "popularity":14, "odds":60.2},
    {"horse_no":5,  "horse_name":"ギャラボーグ",       "sire":"ロードカナロア",     "jockey":"西村淳也", "popularity":4,  "odds":13.1},
    {"horse_no":6,  "horse_name":"アイニードユー",     "sire":"ファインニードル",   "jockey":"川田将雅", "popularity":11, "odds":30.9},
    {"horse_no":7,  "horse_name":"アランカール",       "sire":"エピファネイア",     "jockey":"武豊",     "popularity":3,  "odds":5.1},
    {"horse_no":8,  "horse_name":"ロンギングセリーヌ", "sire":"モーリス",           "jockey":"石橋脩",   "popularity":15, "odds":85.2},
    {"horse_no":9,  "horse_name":"ルールザウェイヴ",   "sire":"ロードカナロア",     "jockey":"原優介",   "popularity":16, "odds":91.5},
    {"horse_no":10, "horse_name":"ナムラコスモス",     "sire":"ダノンプレミアム",   "jockey":"田口貫太", "popularity":13, "odds":33.5},
    {"horse_no":11, "horse_name":"ジッピーチューン",   "sire":"ロードカナロア",     "jockey":"北村友一", "popularity":10, "odds":30.5},
    {"horse_no":12, "horse_name":"スウィートハピネス", "sire":"リアルインパクト",   "jockey":"高杉大河", "popularity":12, "odds":31.3},
    {"horse_no":13, "horse_name":"リリージョワ",       "sire":"シルバーステート",   "jockey":"浜中俊",   "popularity":5,  "odds":14.0},
    {"horse_no":14, "horse_name":"ドリームコア",       "sire":"キズナ",             "jockey":"C.ルメール","popularity":1,  "odds":3.2},
    {"horse_no":15, "horse_name":"スターアニス",       "sire":"ドレフォン",         "jockey":"松山弘平", "popularity":2,  "odds":4.2},
    {"horse_no":16, "horse_name":"ショウナンカリス",   "sire":"リアルスティール",   "jockey":"池添謙一", "popularity":17, "odds":120.9},
    {"horse_no":17, "horse_name":"ブラックチャリス",   "sire":"キタサンブラック",   "jockey":"津村明秀", "popularity":9,  "odds":29.3},
    {"horse_no":18, "horse_name":"プレセピオ",         "sire":"パドトロワ",         "jockey":"富田暁",   "popularity":18, "odds":145.5}
  ]
}
''']

exec(open(r'C:\Users\shiny\Dropbox\shinya_wa\coursemaster\grade_race_predictor.py', encoding='utf-8').read())
