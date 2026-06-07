# -*- coding: utf-8 -*-
"""葵S GⅢ 2026-05-30 予測スクリプト"""
import sys, os, io

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from grade_race_predictor import load_engine, calc_chaos_index, run_prediction, print_result

RACE = {
    'race_name':  '葵S GⅢ',
    'venue':      '京都',
    'surface':    '芝',
    'distance':   1200,
    'track_cond': '良',
    'class_code': 800,
    'horses': [
        {'horse_no':  1, 'horse_name': 'ヒシアイラ',         'jockey': '荻野極',   'sire': 'モーリス',                     'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  4, 'odds':  9.4},
        {'horse_no':  2, 'horse_name': 'フィオラーノ',        'jockey': '松本',     'sire': 'インディチャンプ',              'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 21, 'odds':127.7},
        {'horse_no':  3, 'horse_name': 'マジェステラ',        'jockey': '',         'sire': 'ディーマジェスティ',            'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 22, 'odds':139.9},
        {'horse_no':  4, 'horse_name': 'アンジュプロミス',    'jockey': '古川奈',   'sire': 'ドレフォン',                   'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 10, 'odds': 22.7},
        {'horse_no':  5, 'horse_name': 'タマモイカロス',      'jockey': '高杉',     'sire': 'デクラレーションオブウォー',   'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  2, 'odds':  7.2},
        {'horse_no':  6, 'horse_name': 'クリエープキー',      'jockey': '幸',       'sire': 'ミッキーアイル',               'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 20, 'odds':116.7},
        {'horse_no':  7, 'horse_name': 'ハイヤーマーク',      'jockey': '西塚',     'sire': 'ブリックスアンドモルタル',     'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 11, 'odds': 29.8},
        {'horse_no':  8, 'horse_name': 'コックピットサイト',  'jockey': '浜中',     'sire': 'ドレフォン',                   'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 15, 'odds': 55.0},
        {'horse_no':  9, 'horse_name': 'ルージュサウダージ',  'jockey': '斎藤',     'sire': 'フィレンツェファイア',         'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 19, 'odds': 82.4},
        {'horse_no': 10, 'horse_name': 'ファムマルキーズ',    'jockey': '西村淳',   'sire': 'キタサンブラック',             'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity':  5, 'odds':  9.9},
        {'horse_no': 11, 'horse_name': 'ロジケープ',          'jockey': '丹内',     'sire': 'ロジユニヴァース',             'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  7, 'odds': 12.5},
        {'horse_no': 12, 'horse_name': 'タガノアラリア',      'jockey': '鮫島駿',   'sire': 'ミスターメロディ',             'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  1, 'odds':  5.2},
        {'horse_no': 13, 'horse_name': 'トップアタック',      'jockey': '小沢',     'sire': 'サトノダイヤモンド',           'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 16, 'odds': 62.6},
        {'horse_no': 14, 'horse_name': 'テーオーグレーザー',  'jockey': '酒井',     'sire': 'マテラスカイ',                 'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  9, 'odds': 19.4},
        {'horse_no': 15, 'horse_name': 'メランコリニスタ',    'jockey': '団野',     'sire': 'ミッキーアイル',               'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 13, 'odds': 32.4},
        {'horse_no': 16, 'horse_name': 'フォーゲル',          'jockey': '坂井',     'sire': 'アルアイン',                   'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  6, 'odds': 10.6},
        {'horse_no': 17, 'horse_name': 'ショウナンカリス',    'jockey': '池添',     'sire': 'リアルスティール',             'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 14, 'odds': 34.8},
        {'horse_no': 18, 'horse_name': 'エイシンディード',    'jockey': '川又',     'sire': 'ファインニードル',             'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity':  3, 'odds':  7.2},
        {'horse_no': 19, 'horse_name': 'シラヌイ',            'jockey': '吉村',     'sire': 'フィレンツェファイア',         'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 17, 'odds': 68.0},
        {'horse_no': 20, 'horse_name': 'ウチュウノセカイ',    'jockey': '原',       'sire': 'タワーオブロンドン',           'dam_sire': '', 'age': 3, 'weight': 57.0, 'popularity': 18, 'odds': 75.5},
        {'horse_no': 21, 'horse_name': 'デアヴェローチェ',    'jockey': '北村友',   'sire': 'マテラスカイ',                 'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity':  8, 'odds': 12.6},
        {'horse_no': 22, 'horse_name': 'ガラベイヤ',          'jockey': '丸山',     'sire': 'アルアイン',                   'dam_sire': '', 'age': 3, 'weight': 55.0, 'popularity': 12, 'odds': 30.6},
    ]
}

if __name__ == '__main__':
    print('=' * 76)
    print('  葵S GⅢ 2026-05-30（京都11R 芝1200m 良 22頭）')
    print('=' * 76)
    engine = load_engine()
    chaos = calc_chaos_index(RACE)
    prediction = run_prediction(engine, RACE)
    print_result(RACE, prediction, chaos)
