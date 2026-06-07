"""
COURSE MASTER - 未来レース予測スクリプト
前走データを自動補完してSI/PD/FR/SPD軸を有効化する

使い方:
  predict_future.py に馬名・騎手・血統などを直接記入して実行

[v7.3からの改善点]
  SI軸: 今走上がり3F(未確定=50) → 前走上がり3Fタイム(CSV自動取得)
  PD軸: 今走通過順(未確定=50)  → 前走通過順(CSV自動取得)
  FR軸: 固定50                 → 今走馬体重 - 前走馬体重(差分評価)
  SPD軸: 今走走破時計(未確定=50)→ 前走走破時計を距離別z-scoreで評価
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from course_master_v73_engine import CourseMASTERv73

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================
# 前走データ補完クラス
# =========================================

class PrevRaceLookup:
    """全結果CSVを読み込み、馬名から前走データを返す"""

    def __init__(self):
        print("[前走データ] 結果CSVを読み込み中...")
        files = [
            '2015_2016結果.csv', '2017_2018結果.csv',
            '2019_2020結果.csv', '2021_2023結果.csv', '2024_2026結果.csv',
        ]
        dfs = []
        for f in files:
            path = os.path.join(BASE_DIR, f)
            if os.path.exists(path):
                dfs.append(pd.read_csv(path, encoding='cp932', low_memory=False))

        self.df = pd.concat(dfs, ignore_index=True)

        # 数値化
        for col in ['上がり3Fタイム', '走破時計', '馬体重',
                    '通過順1', '通過順2', '通過順3', '通過順4']:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        self.df['確定着順'] = pd.to_numeric(self.df['確定着順'], errors='coerce')

        # 距離別上がり3F統計（SI軸のz-score用）
        g = self.df[self.df['上がり3Fタイム'].notna()].groupby(['芝・ダ', '距離'])['上がり3Fタイム']
        self.agari_stats = g.agg(['mean', 'std']).to_dict('index')

        # 距離別走破時計統計（SPD軸のz-score用）
        g2 = self.df[self.df['走破時計'].notna()].groupby(['芝・ダ', '距離'])['走破時計']
        self.time_stats = g2.agg(['mean', 'std']).to_dict('index')

        print(f"  → {len(self.df):,}件 読み込み完了")

    def get_prev(self, horse_name):
        """
        馬名で前走データを取得。
        戻り値: dict or None
        """
        horse_df = self.df[self.df['馬名'] == horse_name].copy()
        if horse_df.empty:
            return None

        # 最新レースを1件取得
        horse_df = horse_df.sort_values(['年', '月', '日'], ascending=False)
        row = horse_df.iloc[0]

        return {
            '前走上がり3F':  row['上がり3Fタイム'],
            '前走走破時計':  row['走破時計'],
            '前走距離':      row['距離'],
            '前走馬場':      row['芝・ダ'],
            '前走馬体重':    row['馬体重'],
            '前走通過順1':   row['通過順1'],
            '前走通過順2':   row['通過順2'],
            '前走通過順3':   row['通過順3'],
            '前走通過順4':   row['通過順4'],
            '前走着順':      row['確定着順'],
            '前走レース名':  row['レース名'],
            '前走年月':      f"{int(row['年'])}/{int(row['月']):02d}",
        }


# =========================================
# 改善版エンジン
# =========================================

class CourseMASTERv73_Future(CourseMASTERv73):
    """
    前走データを使ってSI/PD/FR/SPD軸を有効化した予測エンジン
    """

    def __init__(self, lookup: PrevRaceLookup):
        super().__init__()
        self.lookup = lookup

    def score_horse_future(self, horse_row, team_type='I'):
        """
        前走データを使った12軸スコア計算
        SI/PD/FR/SPD軸を前走データで置き換える
        """
        axes = {}

        # ── CF: キャリア形成（変更なし）──────────────────────
        horse_name = (horse_row['馬名'].strip()
                      if isinstance(horse_row['馬名'], str)
                      else str(horse_row['馬名']))
        blood_info = self.df_blood[self.df_blood['馬名'] == horse_name]
        if not blood_info.empty:
            total_races = int(
                blood_info['全成績1着数'].iloc[0] + blood_info['全成績2着数'].iloc[0] +
                blood_info['全成績3着数'].iloc[0] + blood_info['全成績着外数'].iloc[0]
            )
            total_wins = int(blood_info['全成績1着数'].iloc[0])
            if total_races > 0:
                raw_win_rate = total_wins / total_races
                confidence = min(1.0, total_races / 10)
                cf_score = raw_win_rate * 100 * confidence + 50 * (1 - confidence)
                cf_score = min(100, cf_score)
                penalty = self.career_penalty_table.get(total_races, 1.0)
                if penalty < 1.0 and cf_score > 50:
                    cf_score = 50 + (cf_score - 50) * penalty
            else:
                cf_score = 20
        else:
            cf_score = 20
        axes['CF'] = cf_score

        # ── BF: 血統適性（変更なし）──────────────────────────
        sire = horse_row['父馬名']
        dam_sire = horse_row['母の父馬名']
        sire_score = 50
        if pd.notna(sire) and sire in self.sire_stats:
            sire_score = min(100, self.sire_stats[sire]['win_rate'] * 100)
        dam_sire_score = 50
        if pd.notna(dam_sire) and dam_sire in self.dam_sire_stats:
            dam_sire_score = min(100, self.dam_sire_stats[dam_sire]['win_rate'] * 100)
        axes['BF'] = (sire_score + dam_sire_score) / 2

        # 前走データを取得
        prev = self.lookup.get_prev(horse_name)

        # ── SI: スピードインデックス（前走上がり3F）────────────
        # 改善: 今走データがない場合、前走上がり3Fをz-score化して使用
        if prev is not None and pd.notna(prev['前走上がり3F']):
            agari = prev['前走上がり3F']
            key = (prev['前走馬場'], int(prev['前走距離'])) if pd.notna(prev['前走距離']) else None
            if key and key in self.lookup.agari_stats:
                stat = self.lookup.agari_stats[key]
                if stat['std'] > 0:
                    z = (agari - stat['mean']) / stat['std']
                    # 速い（小さい値）ほど高スコア
                    si_score = max(10, min(100, 50 - z * 15))
                else:
                    si_score = max(10, 100 - (agari - 30) * 2)
            else:
                si_score = max(10, 100 - (agari - 30) * 2)
        elif pd.notna(horse_row.get('上がり3Fタイム_sec', np.nan)):
            agari = horse_row['上がり3Fタイム_sec']
            si_score = max(10, 100 - (agari - 30) * 2)
        else:
            si_score = 50  # データなし
        axes['SI'] = si_score

        # ── CL: クラス適応性（変更なし）──────────────────────
        class_code = horse_row['クラスコード']
        if class_code in self.class_stats:
            axes['CL'] = min(100, self.class_stats[class_code]['win_rate'] * 100)
        else:
            axes['CL'] = 50

        # ── JT: ジョッキー（変更なし）────────────────────────
        jockey = horse_row['騎手名']
        if pd.notna(jockey) and jockey in self.jockey_stats:
            axes['JT'] = min(100, self.jockey_stats[jockey]['win_rate'] * 100)
        else:
            axes['JT'] = 50

        # ── PD: ペースデザイン（前走通過順）──────────────────
        # 改善: 前走の通過順で馬の脚質・位置取りを評価
        if prev is not None:
            passages = [prev.get(f'前走通過順{i}') for i in range(1, 5)]
            passages = [p for p in passages if p is not None and pd.notna(p) and p > 0]
        else:
            passages = []

        if not passages:
            # 今走データがあればそちらも試みる
            passages = [horse_row.get(f'通過順{i}', np.nan) for i in range(1, 5)]
            passages = [p for p in passages if pd.notna(p) and p > 0]

        if passages:
            avg_passage = np.mean(passages)
            pd_score = max(10, 100 - abs(avg_passage - 7) * 3)
        else:
            pd_score = 50
        axes['PD'] = pd_score

        # ── FR: フィジカルレディネス（馬体重変化）──────────────
        # 改善: 今走馬体重 - 前走馬体重 で変化量を算出。
        # 変化幅が小さいほど高スコア（±0は最高）
        cur_weight = horse_row.get('馬体重_num', np.nan)
        if prev is not None and pd.notna(prev['前走馬体重']) and pd.notna(cur_weight):
            weight_change = float(cur_weight) - float(prev['前走馬体重'])
            # |変化| 0→80点, 6→68点, 12→56点, 20→44点
            fr_score = max(20, 80 - abs(weight_change) * 2)
        else:
            fr_score = 50
        axes['FR'] = fr_score

        # ── TR: トラック適応性（変更なし）────────────────────
        venue = horse_row['場所']
        surface = horse_row['芝・ダ']
        if (venue, surface) in self.track_stats:
            axes['TR'] = self.track_stats[(venue, surface)]['win_rate'] * 100 + 20
        else:
            axes['TR'] = 50

        # ── BL: ベース力（変更なし）──────────────────────────
        if horse_row['人気順'] > 0:
            axes['BL'] = max(10, 100 - horse_row['人気順'] * 5)
        else:
            axes['BL'] = 50

        # ── HP: ハンディキャップ適応（変更なし）──────────────
        if pd.notna(horse_row.get('斤量_num')) and pd.notna(horse_row.get('年齢')):
            weight = horse_row['斤量_num']
            expected = 54 + horse_row['年齢'] * 0.5
            axes['HP'] = max(20, 100 - abs(weight - expected))
        else:
            axes['HP'] = 50

        # ── SPD: スピード能力（前走走破時計）────────────────
        # 改善: 前走走破時計を同一距離・馬場の平均・標準偏差でz-score化
        if prev is not None and pd.notna(prev['前走走破時計']):
            key = (prev['前走馬場'], int(prev['前走距離'])) if pd.notna(prev['前走距離']) else None
            if key and key in self.lookup.time_stats:
                stat = self.lookup.time_stats[key]
                if stat['std'] > 0:
                    z = (prev['前走走破時計'] - stat['mean']) / stat['std']
                    # 速い（小さい値）ほど高スコア
                    spd_score = max(10, min(100, 50 - z * 10))
                else:
                    spd_score = 50
            else:
                spd_score = 50
        elif pd.notna(horse_row.get('走破時計_sec', np.nan)):
            distance = horse_row['距離']
            if distance in self.distance_stats and pd.notna(horse_row['走破時計_sec']):
                ds = self.distance_stats[distance]
                if ds['std_time'] > 0:
                    z = (horse_row['走破時計_sec'] - ds['avg_time']) / ds['std_time']
                    spd_score = max(10, min(100, 50 - z * 10))
                else:
                    spd_score = 50
            else:
                spd_score = 50
        else:
            spd_score = 50
        axes['SPD'] = spd_score

        # ── MK: マーケット（変更なし、v7.3 Fix3適用）─────────
        popularity = horse_row['人気順']
        odds = horse_row.get('単勝オッズ_num', 0.0)
        if pd.isna(odds):
            odds = 0.0

        if 1 <= popularity <= 5:
            mk_score = 100 - popularity * 10
        elif 6 <= popularity <= 10:
            mk_score = 50 - (popularity - 5) * 5
        else:
            mk_score = max(10, 30 - (popularity - 10))

        if team_type == 'I' and popularity > 5:
            mk_score += (popularity - 5) * 2
        elif team_type == 'O' and popularity <= 3:
            mk_score += (4 - popularity) * 5

        if odds > 0:
            for lo, hi, mult in self.odds_mk_table:
                if lo < odds <= hi:
                    if mult != 1.0:
                        mk_score = 50 + (mk_score - 50) * mult
                    break
        axes['MK'] = mk_score

        return np.mean(list(axes.values())), axes  # スコア + 軸別内訳を返す

    def predict_future_race(self, race_df, verbose=True):
        """
        未来レース予測（前走データ補完付き）
        """
        all_scores = {}
        all_axes = {}
        all_prev = {}

        for team in ['I', 'O', 'U', 'S']:
            for idx, row in race_df.iterrows():
                score, axes = self.score_horse_future(row, team)
                if idx not in all_scores:
                    all_scores[idx] = []
                    all_axes[idx] = axes
                all_scores[idx].append(score)

        final_scores = {idx: np.mean(scores) for idx, scores in all_scores.items()}

        # 前走データ収集（表示用）
        for idx, row in race_df.iterrows():
            horse_name = (row['馬名'].strip()
                          if isinstance(row['馬名'], str) else str(row['馬名']))
            all_prev[idx] = self.lookup.get_prev(horse_name)

        # softmax勝率変換
        win_probs = self.score_to_win_prob(final_scores, race_df)

        sorted_horses = sorted(
            [(race_df.loc[idx, '馬名'], final_scores[idx], win_probs[idx], idx)
             for idx in final_scores],
            key=lambda x: x[1], reverse=True
        )

        result = {
            '◎': sorted_horses[0:1],
            '○': sorted_horses[1:4],
            '▲': sorted_horses[4:9],
        }

        if verbose:
            self._print_result(result, race_df, all_axes, all_prev)

        return result, all_axes, all_prev

    def _print_result(self, result, race_df, all_axes, all_prev):
        mark_label = {'◎': '本命', '○': '対抗', '▲': '単穴'}
        print()
        print('=' * 70)
        for mark, horses in result.items():
            for horse_name, score, win_prob, idx in horses:
                pop  = int(race_df.at[idx, '人気順'])
                odds = float(race_df.at[idx, '単勝オッズ_num'])
                prev = all_prev.get(idx)
                prev_info = ''
                if prev:
                    prev_info = (f"  前走: {prev['前走レース名']} {prev['前走年月']} "
                                 f"{prev['前走着順']:.0f}着 "
                                 f"上がり{prev['前走上がり3F']:.1f}秒")
                print(f"  {mark}[{mark_label[mark]}] {str(horse_name).strip():<14} "
                      f"スコア:{score:.1f}  勝率:{win_prob:.1%}  "
                      f"{pop}番人気({odds}倍)")
                if prev_info:
                    print(f"          {prev_info}")
        print('=' * 70)
        print()
        print('  ※ SI=前走上がり3F  PD=前走通過順  FR=馬体重変化  SPD=前走走破時計')


# =========================================
# 金鯱賞での検証（過去レースで精度確認）
# =========================================

if __name__ == '__main__':

    # エンジン初期化
    lookup = PrevRaceLookup()

    engine = CourseMASTERv73_Future(lookup)
    engine.load(os.path.join(BASE_DIR, 'course_master_v70_engine.pkl'))
    engine.df_blood = pd.read_csv(
        os.path.join(BASE_DIR, '20260217血統.csv'),
        encoding='cp932', low_memory=False
    )
    for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
        engine.df_blood[col] = pd.to_numeric(
            engine.df_blood[col], errors='coerce').fillna(0).astype(int)

    print('\n[改善版] 第62回 金鯱賞（G2）予測 ─ 前走データ補完あり')
    print('2026/3/15 中京 芝2000m 14頭立て')

    # 出馬表
    horses = [
        # 馬名, 騎手名, 父馬名, 母の父馬名, 人気順, 単勝オッズ, 斤量, 年齢, 馬体重
        ('ドゥラドーレス',   '戸崎圭太',   'ドゥラメンテ',            'ハービンジャー',         2,   5.6, 57.0, 7, 498),
        ('ジューンテイク',   '武豊',       'キズナ',                  'シンボリクリスエス',      5,   7.7, 58.0, 5, 500),
        ('ジョバンニ',       '松山弘平',   'エピファネイア',           'Footstepsinthesand',     6,   8.7, 57.0, 4, 482),
        ('アーバンシック',   '三浦皇成',   'スワーヴリチャード',       'ハービンジャー',         7,  11.9, 58.0, 5, 522),
        ('ディマイザキッド', '柴田善臣',   'ディーマジェスティ',       'ファスリエフ',          10,  35.0, 57.0, 5, 460),
        ('ヴィレム',         'M.ディー',   'キズナ',                  'Mizzen Mast',            3,   6.4, 57.0, 5, 526),
        ('ニシノレヴナント', '野中悠太郎', 'ネロ',                    'コンデュイット',         13, 102.5, 57.0, 6, 482),
        ('アラタ',           '横山典弘',   'キングカメハメハ',         'ハーツクライ',          14, 142.3, 57.0, 9, 476),
        ('シェイクユアハート','古川吉洋',  'ハーツクライ',            'Sri Pekan',              8,  13.5, 57.0, 6, 462),
        ('セキトバイースト', '浜中俊',     'デクラレーションオブウォー','Footstepsinthesand',    9,  24.8, 55.0, 5, 460),
        ('キングズパレス',   '菊沢一樹',   'キングカメハメハ',         'Dubawi',                11,  73.5, 57.0, 7, 504),
        ('クイーンズウォーク','川田将雅',  'キズナ',                  'Harlington',             1,   3.6, 56.0, 5, 542),
        ('ホウオウビスケッツ','岩田望来',  'マインドユアビスケッツ',   'ルーラーシップ',         4,   7.3, 57.0, 6, 502),
        ('サフィラ',         '丸山元気',   'ハーツクライ',            'Lomitas',               12,  88.9, 55.0, 5, 478),
    ]

    rows = []
    for h in horses:
        rows.append({
            '馬名': h[0], '騎手名': h[1], '父馬名': h[2], '母の父馬名': h[3],
            '人気順': h[4], '単勝オッズ_num': h[5], '斤量_num': h[6],
            '年齢': h[7], '馬体重_num': h[8],
            '確定着順': 0,
            '走破時計_sec': np.nan, '上がり3Fタイム_sec': np.nan,
            '通過順1': np.nan, '通過順2': np.nan,
            '通過順3': np.nan, '通過順4': np.nan,
            'クラスコード': 179,
            '場所': '中京', '芝・ダ': '芝', '距離': 2000,
        })
    race_df = pd.DataFrame(rows)

    engine.predict_future_race(race_df)
