"""
COURSE MASTER v7.0 - Windows用クイックスタート
quickstart_v70.py のパスをWindows環境に合わせて修正したもの
"""

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import pandas as pd
import pickle
from course_master_v70_engine import CourseMASTERv70


def load_engine():
    engine = CourseMASTERv70()
    engine.load(os.path.join(BASE_DIR, 'course_master_v70_engine.pkl'))
    # .pklには統計データのみ保存されているため、df_bloodを別途ロードする
    engine.df_blood = pd.read_csv(
        os.path.join(BASE_DIR, '20260217血統.csv'),
        encoding='cp932', low_memory=False
    )
    for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
        engine.df_blood[col] = pd.to_numeric(engine.df_blood[col], errors='coerce').fillna(0).astype(int)
    return engine


def prepare_race_data(race_key):
    """
    race_key: レースIDの先頭7桁（レース単位の識別子）
              例: '5261212' → 2026年2月1日東京12Rの全出走馬を取得
    """
    df_result = pd.read_csv(os.path.join(BASE_DIR, '2024_2026結果.csv'), encoding='cp932', low_memory=False)

    blood_df = pd.read_csv(os.path.join(BASE_DIR, '20260217血統.csv'), encoding='cp932', low_memory=False)
    blood_slim = blood_df[['血統登録番号', '種牡馬名', '母名', '母の父名']].copy()
    blood_slim.columns = ['血統登録番号', '父馬名_b', '母馬名_b', '母の父馬名_b']

    df_result = df_result.merge(blood_slim, on='血統登録番号', how='left')
    df_result['父馬名'] = df_result['父馬名'].fillna(df_result['父馬名_b'])
    df_result['母馬名'] = df_result['母馬名'].fillna(df_result['母馬名_b'])
    df_result['母の父馬名'] = df_result['母の父馬名'].fillna(df_result['母の父馬名_b'])
    df_result.drop(['父馬名_b', '母馬名_b', '母の父馬名_b'], axis=1, inplace=True)

    # レースIDの先頭7桁でレース単位に絞り込む
    df_result['レースキー'] = df_result['レースID'].astype(str).str[:7]
    race_df = df_result[df_result['レースキー'] == str(race_key)].copy()
    if len(race_df) == 0:
        return None

    race_df['確定着順'] = pd.to_numeric(race_df['確定着順'], errors='coerce').fillna(0).astype(int)
    race_df['人気順'] = pd.to_numeric(race_df['人気順'], errors='coerce').fillna(0).astype(int)
    race_df['走破時計_sec'] = pd.to_numeric(race_df['走破時計'], errors='coerce')
    race_df['単勝オッズ_num'] = pd.to_numeric(race_df['単勝オッズ'], errors='coerce').fillna(0)
    race_df['斤量_num'] = pd.to_numeric(race_df['斤量'], errors='coerce')
    race_df['馬体重_num'] = pd.to_numeric(race_df['馬体重'], errors='coerce')
    race_df['上がり3Fタイム_sec'] = pd.to_numeric(race_df['上がり3Fタイム'], errors='coerce')

    return race_df


def predict_and_display(engine, race_id):
    print(f"\n{'='*70}")
    print(f" COURSE MASTER v7.0 - レース予測")
    print(f"{'='*70}")

    race_df = prepare_race_data(race_id)

    if race_df is None or len(race_df) < 5:
        print(f"  ✗ レースID {race_id} が見つからないか、出走数が不足しています")
        return False

    race_name = race_df['レース名'].iloc[0] if 'レース名' in race_df.columns else "Unknown"
    race_date = f"{int(race_df['年'].iloc[0])}/{int(race_df['月'].iloc[0])}/{int(race_df['日'].iloc[0])}"

    print(f"\n  レースキー: {race_id}")
    print(f"  日程: {race_date}")
    print(f"  レース: {race_name}")
    print(f"  出走数: {len(race_df)}頭")
    print(f"\n{'-'*70}")

    predictions = engine.predict_race(race_df)

    all_preds = []
    for mark, horses in predictions.items():
        for horse_name, score, idx in horses:
            actual_finish = int(race_df.loc[idx, '確定着順'])
            popularity = int(race_df.loc[idx, '人気順'])
            all_preds.append({
                'mark': mark,
                'horse_name': horse_name.strip(),
                'score': score,
                'finish': actual_finish,
                'popularity': popularity
            })

    mark_order = {'◎': 0, '○': 1, '▲': 2}
    all_preds.sort(key=lambda x: (mark_order.get(x['mark'], 3), -x['score']))

    print(f"\n  【予測結果】\n")
    for pred in all_preds:
        if pred['finish'] == 1:
            result = "✓ 的中"
        elif pred['finish'] <= 3:
            result = "◇ 複勝"
        else:
            result = ""

        print(f"  {pred['mark']} {pred['horse_name']:15} | "
              f"スコア: {pred['score']:6.1f} | "
              f"実績: {pred['finish']:2d}着 | "
              f"人気順: {pred['popularity']:2d} | "
              f"{result}")

    print(f"\n{'-'*70}\n")
    return True


def main():
    print("\n" + "="*70)
    print(" COURSE MASTER v7.0 クイックスタート (Windows版)")
    print("="*70)

    print("\n[1] エンジンロード中...")
    engine = load_engine()
    print("  ✓ エンジン正常にロード")

    print(f"\n  統計マスター情報:")
    print(f"    種牡馬: {len(engine.sire_stats)}件")
    print(f"    騎手:   {len(engine.jockey_stats)}件")
    print(f"    調教師: {len(engine.trainer_stats)}件")
    print(f"    距離:   {len(engine.distance_stats)}件")

    print("\n[2] レース予測実行")

    if len(sys.argv) > 1:
        race_id = sys.argv[1]
        predict_and_display(engine, race_id)
    else:
        print("  引数なし → サンプルレース3件を予測します...\n")
        df_result = pd.read_csv(os.path.join(BASE_DIR, '2024_2026結果.csv'), encoding='cp932', low_memory=False)
        # レースIDの先頭7桁がレース単位キー（末尾2桁は馬番）
        df_result['レースキー'] = df_result['レースID'].astype(str).str[:7]
        sample_races = df_result['レースキー'].unique()[:3]
        for race_key in sample_races:
            predict_and_display(engine, race_key)


if __name__ == '__main__':
    main()
