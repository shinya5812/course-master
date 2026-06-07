# -*- coding: utf-8 -*-
"""
2026-05-02 週次予測スクリプト（特別登録段階・予備版）
注意: 馬番・騎手・オッズは未確定。出馬表確定（4/30頃）後に再実行が必要。
ADI/エッジ値は暫定計算（均等オッズ仮置き）。
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ─── 京王杯スプリングカップ G2（東京 芝1400m・20頭特別登録）─────────────────
KEIO_SPRING_RACE = {
    "race_name": "京王杯スプリングカップ",
    "grade": "G2",
    "venue": "東京",
    "surface": "芝",
    "distance": 1400,
    "track_cond": "良",
    "n_horses": 20,
    "provisional": True,
    "note": "特別登録段階(4/27)。馬番は仮番号。オッズ・騎手・馬番は4/30確定後に更新要。",
    "horses": [
        {"no":1,  "name":"アサカラキング",    "sire":"キズナ",                   "jockey":"未定", "popularity":1,  "odds":20.0},
        {"no":2,  "name":"アルセナール",      "sire":"エピファネイア",            "jockey":"未定", "popularity":2,  "odds":20.0},
        {"no":3,  "name":"ウイントワイライト", "sire":"レイデオロ",               "jockey":"未定", "popularity":3,  "odds":20.0},
        {"no":4,  "name":"カンチェンジュンガ", "sire":"ビッグアーサー",           "jockey":"未定", "popularity":4,  "odds":20.0},
        {"no":5,  "name":"キープカルム",      "sire":"ロードカナロア",            "jockey":"未定", "popularity":5,  "odds":20.0},
        {"no":6,  "name":"シリウスコルト",    "sire":"マクフィ",                 "jockey":"未定", "popularity":6,  "odds":20.0},
        {"no":7,  "name":"シンフォーエバー",  "sire":"Complexity",               "jockey":"未定", "popularity":7,  "odds":20.0},
        {"no":8,  "name":"セフィロ",          "sire":"イスラボニータ",            "jockey":"未定", "popularity":8,  "odds":20.0},
        {"no":9,  "name":"ダノンセンチュリー", "sire":"フィエールマン",           "jockey":"未定", "popularity":9,  "odds":20.0},
        {"no":10, "name":"ダノンマッキンリー", "sire":"モーリス",                 "jockey":"未定", "popularity":10, "odds":20.0},
        {"no":11, "name":"ファンダム",        "sire":"サートゥルナーリア",        "jockey":"未定", "popularity":11, "odds":20.0},
        {"no":12, "name":"フリームファクシ",  "sire":"ルーラーシップ",            "jockey":"未定", "popularity":12, "odds":20.0},
        {"no":13, "name":"マイネルチケット",  "sire":"ダノンバラード",            "jockey":"未定", "popularity":13, "odds":20.0},
        {"no":14, "name":"ヤブサメ",          "sire":"ファインニードル",          "jockey":"未定", "popularity":14, "odds":20.0},
        {"no":15, "name":"ラケマーダ",        "sire":"アメリカンペイトリオット",  "jockey":"未定", "popularity":15, "odds":20.0},
        {"no":16, "name":"ララマセラシオン",  "sire":"カリフォルニアクローム",    "jockey":"未定", "popularity":16, "odds":20.0},
        {"no":17, "name":"レイベリング",      "sire":"Frankel",                  "jockey":"未定", "popularity":17, "odds":20.0},
        {"no":18, "name":"レッドシュヴェルト", "sire":"レッドファルクス",         "jockey":"未定", "popularity":18, "odds":20.0},
        {"no":19, "name":"ワイドラトゥール",  "sire":"カリフォルニアクローム",    "jockey":"未定", "popularity":19, "odds":20.0},
        {"no":20, "name":"ワールズエンド",    "sire":"ロードカナロア",            "jockey":"未定", "popularity":20, "odds":20.0},
    ]
}

# ─── ユニコーンステークス G3（京都 ダート1900m・17頭特別登録）──────────────────
UNICORN_RACE = {
    "race_name": "ユニコーンステークス",
    "grade": "G3",
    "venue": "京都",
    "surface": "ダ",
    "distance": 1900,
    "track_cond": "良",
    "n_horses": 17,
    "provisional": True,
    "note": "特別登録段階(4/27)。馬番は仮番号。オッズ・騎手は4/30確定後に更新要。メルカントゥール=川田想定。",
    "horses": [
        {"no":1,  "name":"ガウラディスコ",    "sire":"クリソベリル",              "jockey":"未定", "popularity":1,  "odds":17.0},
        {"no":2,  "name":"ガムラスタン",      "sire":"サンダースノー",            "jockey":"未定", "popularity":2,  "odds":17.0},
        {"no":3,  "name":"クラウトロック",    "sire":"ナダル",                   "jockey":"未定", "popularity":3,  "odds":17.0},
        {"no":4,  "name":"ケイアイアギト",    "sire":"エスポワールシチー",        "jockey":"未定", "popularity":4,  "odds":17.0},
        {"no":5,  "name":"コロナドブリッジ",  "sire":"ベンバトル",               "jockey":"未定", "popularity":5,  "odds":17.0},
        {"no":6,  "name":"サイモンゼスト",    "sire":"サトノアラジン",            "jockey":"未定", "popularity":6,  "odds":17.0},
        {"no":7,  "name":"シャローファースト", "sire":"クリソベリル",             "jockey":"未定", "popularity":7,  "odds":17.0},
        {"no":8,  "name":"シルバーレシオ",    "sire":"ルヴァンスレーヴ",          "jockey":"未定", "popularity":8,  "odds":17.0},
        {"no":9,  "name":"ジェイエルモーダル", "sire":"デクラレーションオブウォー","jockey":"未定", "popularity":9,  "odds":17.0},
        {"no":10, "name":"ストロングエース",  "sire":"ヤマカツエース",            "jockey":"未定", "popularity":10, "odds":17.0},
        {"no":11, "name":"セイントエルモズ",  "sire":"サンダースノー",            "jockey":"未定", "popularity":11, "odds":17.0},
        {"no":12, "name":"ソルチェリア",      "sire":"ナダル",                   "jockey":"未定", "popularity":12, "odds":17.0},
        {"no":13, "name":"デールエルバハリ",  "sire":"クリソベリル",             "jockey":"未定", "popularity":13, "odds":17.0},
        {"no":14, "name":"フクシマブリルハム", "sire":"ドレフォン",               "jockey":"未定", "popularity":14, "odds":17.0},
        {"no":15, "name":"メルカントゥール",  "sire":"ルヴァンスレーヴ",          "jockey":"川田", "popularity":15, "odds":17.0},
        {"no":16, "name":"ユアフェリシティ",  "sire":"ルヴァンスレーヴ",          "jockey":"未定", "popularity":16, "odds":17.0},
        {"no":17, "name":"ヴィエントデコラ",  "sire":"ルヴァンスレーヴ",          "jockey":"未定", "popularity":17, "odds":17.0},
    ]
}

# ─── grade_race_predictorの関数を直接呼び出し ──────────────────────────────────
from grade_race_predictor import load_engine, run_prediction, calc_chaos_index, print_result

print('=' * 70)
print('  2026-05-02 週次予測（特別登録段階・予備版）')
print('  ※ 馬番・騎手・オッズは未確定。4/30確定後に再実行が必要')
print('=' * 70)

engine = load_engine()

results_all = {}

for race in [KEIO_SPRING_RACE, UNICORN_RACE]:
    print()
    pred = run_prediction(engine, race)
    chaos = calc_chaos_index(race)
    print_result(race, pred, chaos)
    results_all[race['race_name']] = {
        'race': {k: v for k, v in race.items() if k != 'horses'},
        'top_horses': [
            {'rank': i+1, 'name': p[0], 'score': round(p[1], 2),
             'win_prob': round(p[2], 4), 'edge': round(p[4], 4) if len(p) > 4 else None}
            for i, p in enumerate(pred[:10])
        ],
        'chaos_index': round(chaos, 1) if chaos else None,
        'honmei': pred[0][0] if pred else None,
    }

# ─── JSON保存 ────────────────────────────────────────────────────────────────
out = {
    'generated': '2026-04-27',
    'status': 'provisional',
    'note': '特別登録段階。出馬表確定（4/30頃）後に馬番・騎手・オッズを更新して再実行すること。',
    'races': results_all,
}
out_path = os.path.join(BASE_DIR, 'predictions_20260502.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f'\npredictions_20260502.json 保存完了: {out_path}')
