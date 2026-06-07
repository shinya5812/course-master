"""
COURSE MASTER v7.0 - 着順予測エンジン
12軸スコアリング（CF/BF/SI/CL/JT/PD/FR/TR/BL/HP/SPD/MK）
4チーム合議制（I/O/U/S）+ スコア平均化
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import warnings

warnings.filterwarnings('ignore')

class CourseMASTERv70:
    
    def __init__(self):
        self.df_all = None
        self.df_blood = None
        self.sire_stats = {}
        self.dam_sire_stats = {}
        self.jockey_stats = {}
        self.trainer_stats = {}
        self.class_stats = {}
        self.track_stats = {}
        self.distance_stats = {}
    
    def load_data(self, result_files, blood_file):
        """全結果データと血統データを読み込み"""
        print("[load_data] データ読み込み開始...")
        
        dfs = []
        for file in result_files:
            print(f"  → {file}")
            df = pd.read_csv(file, encoding='cp932', low_memory=False)
            dfs.append(df)
        
        self.df_all = pd.concat(dfs, ignore_index=True)
        print(f"  結果データ: {len(self.df_all)} レコード")
        
        self.df_blood = pd.read_csv(blood_file, encoding='cp932', low_memory=False)
        print(f"  血統データ: {len(self.df_blood)} 馬")
        
        self._clean_data()
    
    def _clean_data(self):
        """データ型修正 + 血統データとの結合"""
        print("[_clean_data] データクリーニング...")
        
        # 数値化
        self.df_all['確定着順'] = pd.to_numeric(self.df_all['確定着順'], errors='coerce').fillna(0).astype(int)
        self.df_all['人気順'] = pd.to_numeric(self.df_all['人気順'], errors='coerce').fillna(0).astype(int)
        self.df_all['走破時計_sec'] = pd.to_numeric(self.df_all['走破時計'], errors='coerce')
        self.df_all['単勝オッズ_num'] = pd.to_numeric(self.df_all['単勝オッズ'], errors='coerce').fillna(0)
        self.df_all['斤量_num'] = pd.to_numeric(self.df_all['斤量'], errors='coerce')
        self.df_all['馬体重_num'] = pd.to_numeric(self.df_all['馬体重'], errors='coerce')
        self.df_all['上がり3Fタイム_sec'] = pd.to_numeric(self.df_all['上がり3Fタイム'], errors='coerce')
        
        # 血統データの数値化
        for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
            self.df_blood[col] = pd.to_numeric(self.df_blood[col], errors='coerce').fillna(0).astype(int)
        
        # 血統データとの結合（血統登録番号キー）
        print("  → 血統データとの結合...")
        blood_slim = self.df_blood[['血統登録番号', '種牡馬名', '母名', '母の父名']].copy()
        blood_slim.columns = ['血統登録番号', '父馬名_from_blood', '母馬名_from_blood', '母の父馬名_from_blood']
        
        self.df_all = self.df_all.merge(blood_slim, left_on='血統登録番号', right_on='血統登録番号', how='left')
        
        # 結果CSVのNaN値を血統データで上書き
        self.df_all['父馬名'] = self.df_all['父馬名'].fillna(self.df_all['父馬名_from_blood'])
        self.df_all['母馬名'] = self.df_all['母馬名'].fillna(self.df_all['母馬名_from_blood'])
        self.df_all['母の父馬名'] = self.df_all['母の父馬名'].fillna(self.df_all['母の父馬名_from_blood'])
        
        # 不要なカラムを削除
        self.df_all.drop(['父馬名_from_blood', '母馬名_from_blood', '母の父馬名_from_blood'], axis=1, inplace=True)
        
        print(f"  ✓ 父馬名マッチ: {self.df_all['父馬名'].notna().sum()}/{len(self.df_all)}")
        print("  ✓ クリーニング完了")
    
    def build_statistics(self):
        """統計マスター構築"""
        print("[build_statistics] 統計マスター構築開始...")
        
        # 1. 種牡馬別統計
        print("  [1/7] 種牡馬統計...")
        for sire in self.df_all['父馬名'].dropna().unique():
            subset = self.df_all[self.df_all['父馬名'] == sire]
            n = len(subset)
            if n < 10:
                continue
            wins = (subset['確定着順'] == 1).sum()
            places = (subset['確定着順'] <= 3).sum()
            self.sire_stats[sire] = {
                'races': n,
                'wins': wins,
                'places': places,
                'win_rate': wins / n,
                'place_rate': places / n
            }
        print(f"       → {len(self.sire_stats)}件")
        
        # 2. 母の父別統計
        print("  [2/7] 母の父統計...")
        for dam_sire in self.df_all['母の父馬名'].dropna().unique():
            subset = self.df_all[self.df_all['母の父馬名'] == dam_sire]
            n = len(subset)
            if n < 10:
                continue
            wins = (subset['確定着順'] == 1).sum()
            places = (subset['確定着順'] <= 3).sum()
            self.dam_sire_stats[dam_sire] = {
                'races': n,
                'wins': wins,
                'places': places,
                'win_rate': wins / n,
                'place_rate': places / n
            }
        print(f"       → {len(self.dam_sire_stats)}件")
        
        # 3. 騎手別統計
        print("  [3/7] 騎手統計...")
        for jockey in self.df_all['騎手名'].dropna().unique():
            subset = self.df_all[self.df_all['騎手名'] == jockey]
            n = len(subset)
            if n < 50:
                continue
            wins = (subset['確定着順'] == 1).sum()
            places = (subset['確定着順'] <= 3).sum()
            self.jockey_stats[jockey] = {
                'races': n,
                'wins': wins,
                'places': places,
                'win_rate': wins / n,
                'place_rate': places / n
            }
        print(f"       → {len(self.jockey_stats)}件")
        
        # 4. 調教師別統計
        print("  [4/7] 調教師統計...")
        for trainer in self.df_all['調教師'].dropna().unique():
            subset = self.df_all[self.df_all['調教師'] == trainer]
            n = len(subset)
            if n < 50:
                continue
            wins = (subset['確定着順'] == 1).sum()
            places = (subset['確定着順'] <= 3).sum()
            self.trainer_stats[trainer] = {
                'races': n,
                'wins': wins,
                'places': places,
                'win_rate': wins / n,
                'place_rate': places / n
            }
        print(f"       → {len(self.trainer_stats)}件")
        
        # 5. クラス別統計
        print("  [5/7] クラス統計...")
        for cls in self.df_all['クラスコード'].unique():
            subset = self.df_all[self.df_all['クラスコード'] == cls]
            n = len(subset)
            wins = (subset['確定着順'] == 1).sum()
            places = (subset['確定着順'] <= 3).sum()
            self.class_stats[cls] = {
                'races': n,
                'wins': wins,
                'places': places,
                'win_rate': wins / n,
                'place_rate': places / n,
                'avg_popularity': subset['人気順'].mean()
            }
        print(f"       → {len(self.class_stats)}件")
        
        # 6. トラック別統計（場所 x 馬場）
        print("  [6/7] トラック統計...")
        for venue in self.df_all['場所'].unique():
            for surface in self.df_all['芝・ダ'].unique():
                subset = self.df_all[(self.df_all['場所'] == venue) & (self.df_all['芝・ダ'] == surface)]
                n = len(subset)
                if n < 50:
                    continue
                wins = (subset['確定着順'] == 1).sum()
                places = (subset['確定着順'] <= 3).sum()
                self.track_stats[(venue, surface)] = {
                    'races': n,
                    'wins': wins,
                    'places': places,
                    'win_rate': wins / n,
                    'place_rate': places / n
                }
        print(f"       → {len(self.track_stats)}件")
        
        # 7. 距離別統計
        print("  [7/7] 距離統計...")
        for dist in self.df_all['距離'].unique():
            subset = self.df_all[self.df_all['距離'] == dist]
            n = len(subset)
            wins = (subset['確定着順'] == 1).sum()
            places = (subset['確定着順'] <= 3).sum()
            self.distance_stats[dist] = {
                'races': n,
                'wins': wins,
                'places': places,
                'win_rate': wins / n,
                'place_rate': places / n,
                'avg_time': subset['走破時計_sec'].mean(),
                'std_time': subset['走破時計_sec'].std()
            }
        print(f"       → {len(self.distance_stats)}件")
        
        print("\n✓ 統計マスター構築完了\n")
    
    def score_horse(self, horse_row, team_type='I'):
        """
        単一馬の12軸スコアを計算
        team_type: 'I'=Upset, 'O'=Mainstream, 'U'=Utility, 'S'=Special
        """
        axes = {}
        
        # CF: キャリア形成
        horse_name = horse_row['馬名'].strip() if isinstance(horse_row['馬名'], str) else str(horse_row['馬名'])
        blood_info = self.df_blood[self.df_blood['馬名'] == horse_name]
        if not blood_info.empty:
            total_races = (blood_info['全成績1着数'] + blood_info['全成績2着数'] + 
                          blood_info['全成績3着数'] + blood_info['全成績着外数']).iloc[0]
            total_wins = blood_info['全成績1着数'].iloc[0]
            if total_races > 0:
                cf_score = min(100, (total_wins / total_races) * 100 + min(total_races / 50, 30))
            else:
                cf_score = 30
        else:
            cf_score = 30
        axes['CF'] = cf_score
        
        # BF: 血統適性（種牡馬 + 母の父）
        sire = horse_row['父馬名']
        dam_sire = horse_row['母の父馬名']
        
        sire_score = 50
        if pd.notna(sire) and sire in self.sire_stats:
            stat = self.sire_stats[sire]
            sire_score = stat['win_rate'] * 100 + stat['place_rate'] * 20
        
        dam_sire_score = 50
        if pd.notna(dam_sire) and dam_sire in self.dam_sire_stats:
            stat = self.dam_sire_stats[dam_sire]
            dam_sire_score = stat['win_rate'] * 100 + stat['place_rate'] * 20
        
        axes['BF'] = (sire_score + dam_sire_score) / 2
        
        # SI: スピードインデックス（上がり3F）
        if pd.notna(horse_row['上がり3Fタイム_sec']):
            agari = horse_row['上がり3Fタイム_sec']
            si_score = max(10, 100 - (agari - 30) * 2)
        else:
            si_score = 50
        axes['SI'] = si_score
        
        # CL: クラス適応性
        class_code = horse_row['クラスコード']
        if class_code in self.class_stats:
            stat = self.class_stats[class_code]
            cl_score = stat['win_rate'] * 100 + 30
        else:
            cl_score = 50
        axes['CL'] = cl_score
        
        # JT: ジョッキー
        jockey = horse_row['騎手名']
        if pd.notna(jockey) and jockey in self.jockey_stats:
            stat = self.jockey_stats[jockey]
            jt_score = stat['win_rate'] * 100 + 30
        else:
            jt_score = 50
        axes['JT'] = jt_score
        
        # PD: ペースデザイン（通過順）
        try:
            passages = [horse_row['通過順1'], horse_row['通過順2'], 
                       horse_row['通過順3'], horse_row['通過順4']]
            passages = [p for p in passages if pd.notna(p) and p > 0]
            if passages:
                avg_passage = np.mean(passages)
                pd_score = 100 - abs(avg_passage - 7) * 3
            else:
                pd_score = 50
        except:
            pd_score = 50
        axes['PD'] = max(10, pd_score)
        
        # FR: フィジカルレディネス（馬体重変化）
        try:
            if pd.notna(horse_row['馬体重_num']):
                fr_score = 50  # 前走データがないため仮設定
            else:
                fr_score = 50
        except:
            fr_score = 50
        axes['FR'] = max(20, fr_score)
        
        # TR: トラック適応性
        venue = horse_row['場所']
        surface = horse_row['芝・ダ']
        if (venue, surface) in self.track_stats:
            stat = self.track_stats[(venue, surface)]
            tr_score = stat['win_rate'] * 100 + 20
        else:
            tr_score = 50
        axes['TR'] = tr_score
        
        # BL: ベース力（人気順ベース）
        if horse_row['人気順'] > 0:
            bl_score = max(10, 100 - horse_row['人気順'] * 5)
        else:
            bl_score = 50
        axes['BL'] = bl_score
        
        # HP: ハンディキャップ適応
        if pd.notna(horse_row['斤量_num']) and pd.notna(horse_row['年齢']):
            age = horse_row['年齢']
            weight = horse_row['斤量_num']
            expected_weight = 54 + age * 0.5
            hp_score = 100 - abs(weight - expected_weight)
        else:
            hp_score = 50
        axes['HP'] = max(20, hp_score)
        
        # SPD: スピード能力（走破時計相対）
        distance = horse_row['距離']
        if distance in self.distance_stats and pd.notna(horse_row['走破時計_sec']):
            dist_stat = self.distance_stats[distance]
            if dist_stat['std_time'] > 0:
                z_score = (horse_row['走破時計_sec'] - dist_stat['avg_time']) / dist_stat['std_time']
                spd_score = 50 - z_score * 10
            else:
                spd_score = 50
        else:
            spd_score = 50
        axes['SPD'] = max(10, min(100, spd_score))
        
        # MK: マーケット（人気順 + オッズ）
        popularity = horse_row['人気順']
        if 1 <= popularity <= 5:
            mk_score = 100 - popularity * 10
        elif 6 <= popularity <= 10:
            mk_score = 50 - (popularity - 5) * 5
        else:
            mk_score = max(10, 30 - (popularity - 10))
        
        # チーム特性による調整
        if team_type == 'I' and popularity > 5:
            mk_score += (popularity - 5) * 2
        elif team_type == 'O' and popularity <= 3:
            mk_score += (4 - popularity) * 5
        
        axes['MK'] = mk_score
        
        return np.mean(list(axes.values()))
    
    def score_race(self, race_data):
        """1レースの全馬スコア計算"""
        scores_by_team = {'I': {}, 'O': {}, 'U': {}, 'S': {}}
        
        for team in ['I', 'O', 'U', 'S']:
            for idx, row in race_data.iterrows():
                scores_by_team[team][idx] = self.score_horse(row, team)
        
        final_scores = {}
        for idx in race_data.index:
            team_scores = [scores_by_team[team][idx] for team in ['I', 'O', 'U', 'S']]
            final_scores[idx] = np.mean(team_scores)
        
        return final_scores
    
    def predict_race(self, race_data, top_n=9):
        """
        1レースの着順予測
        出力: {'◎': [...], '○': [...], '▲': [...]}
        """
        scores = self.score_race(race_data)
        
        sorted_horses = sorted(
            [(race_data.loc[idx, '馬名'], scores[idx], idx) for idx in scores.keys()],
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            '◎': sorted_horses[0:1],
            '○': sorted_horses[1:4],
            '▲': sorted_horses[4:9]
        }
    
    def save(self, filepath):
        """エンジン保存"""
        state = {
            'sire_stats': self.sire_stats,
            'dam_sire_stats': self.dam_sire_stats,
            'jockey_stats': self.jockey_stats,
            'trainer_stats': self.trainer_stats,
            'class_stats': self.class_stats,
            'track_stats': self.track_stats,
            'distance_stats': self.distance_stats,
        }
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
        print(f"✓ エンジン保存: {filepath}")
    
    def load(self, filepath):
        """エンジン読み込み"""
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        self.sire_stats = state['sire_stats']
        self.dam_sire_stats = state['dam_sire_stats']
        self.jockey_stats = state['jockey_stats']
        self.trainer_stats = state['trainer_stats']
        self.class_stats = state['class_stats']
        self.track_stats = state['track_stats']
        self.distance_stats = state['distance_stats']
        print(f"✓ エンジン読み込み: {filepath}")


# =========================================
# メイン処理
# =========================================

if __name__ == '__main__':
    
    engine = CourseMASTERv70()
    
    result_files = [
        '/mnt/project/2015_2016結果.csv',
        '/mnt/project/2017_2018結果.csv',
        '/mnt/project/2019_2020結果.csv',
        '/mnt/project/2021_2023結果.csv',
        '/mnt/project/2024_2026結果.csv'
    ]
    
    engine.load_data(result_files, '/mnt/project/20260217血統.csv')
    engine.build_statistics()
    engine.save('/mnt/user-data/outputs/course_master_v70_engine.pkl')
    
    print("✓ COURSE MASTER v7.0 初期化完了\n")

