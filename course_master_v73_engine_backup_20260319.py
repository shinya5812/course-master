"""
COURSE MASTER v7.3 - 着順予測エンジン
12軸スコアリング（CF/BF/SI/CL/JT/PD/FR/TR/BL/HP/SPD/MK）
4チーム合議制（I/O/U/S）+ スコア平均化

[v7.3 修正内容]
  Fix1: 勝率変換式の修正
    - CF軸: place_rate補正を廃止 → 純win_rateベースに統一
    - BF軸: place_rate*20加算を廃止 → win_rateのみでスコア算出
    - CL軸: place_rate加算廃止 → win_rateのみ
    - JT軸: place_rate加算廃止 → win_rateのみ
    - predict_race: softmax勝率変換レイヤー追加
        P(win) <= P(place)/3 の原則を適用
        温度パラメータT=5.0でスコア → 確率変換
        レース内の相対確率として正規化

  Fix3: 市場低オッズ馬への負エッジ補正（MK軸・rev2）
    - バックテスト（2024-2026 Grade 277R）で以下を確認:
        加点（3〜8倍×1.05）: ◎変更24件で的中率 29.2%→16.7%（-12.5%）
          → 2人気→1人気への誤誘導が主因。撤廃。
        薄人気フラグ（1〜2人気×4倍超×0.80）: 勝馬が薄い人気の44件で
          v7.0=50.0% → v7.3=36.4%（-13.6%）。削除。
    - 残す補正: 低オッズ帯の過大評価を減点するのみ
        単勝オッズ〜2倍: MK×0.85（実データ: 実勝率 < 市場期待 -0.038）
        単勝オッズ2〜3倍: MK×0.90（実データ: 実勝率 < 市場期待 -0.043）
        単勝オッズ3倍超: 補正なし（1.00）
    - 設計原則: 「割安を加点」より「過大評価を減点」に絞る
"""

import pandas as pd
import numpy as np
from datetime import datetime
import pickle
import sqlite3
import os
import warnings

warnings.filterwarnings('ignore')

class CourseMASTERv73:
    
    def __init__(self):
        self.df_all = None
        self.df_blood = None
        self.sire_stats = {}
        self.dam_sire_stats = {}
        self.jockey_stats = {}
        self.trainer_stats = {}
        self.class_stats = {}
        self.track_stats = {}
        self.course_stats = {}   # [v7.4] (venue, surface, distance, condition) → win_rate
        self.distance_stats = {}
        # [v7.3 Fix2] 走数別ペナルティ係数テーブル
        # 実データ（Grade53万走）から導出: 走数1-5は6-7走比で勝率15-32%低
        self.career_penalty_table = {
            1: 0.70, 2: 0.70, 3: 0.70,   # 1〜3走: 32%低 → 係数0.70
            4: 0.85, 5: 0.85,             # 4〜5走: 15%低 → 係数0.85
        }
        # 6走以上はペナルティなし（係数1.0）

        # [v7.3 Fix3] オッズ帯別MKスコア補正テーブル
        # 実データ（Grade10444R）から導出: 低オッズ帯は市場が過大評価
        # (odds_min, odds_max): multiplier
        # [v7.3 Fix3 rev2] バックテスト結果（277R）から3〜8倍加点を撤廃。
        # 加点（×1.05）は「2人気→1人気への誤誘導」を引き起こし変更24件で的中率-12.5%。
        # 「過大評価を減点する」のみに絞る。正エッジ帯への加点は効果なし。
        self.odds_mk_table = [
            (0.0,  2.0,  0.85),    # 〜2倍: エッジ -0.038 → 過大評価補正
            (2.0,  3.0,  0.90),    # 2〜3倍: エッジ -0.043 → 過大評価補正
            (3.0,  999.0, 1.00),   # 3倍超: 補正なし
        ]
    
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
        
        # 8. コース別統計（venue × surface × distance × condition）
        # [v7.4] course_win_rateテーブルをDBから読み込み、TRスコアの精度を向上
        print("  [8/8] コース別統計（course_win_rate）...")
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(BASE_DIR, 'course_master.db')
        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                'SELECT venue, surface, distance, condition, win_rate FROM course_win_rate'
            ).fetchall()
            conn.close()
            for venue, surface, distance, condition, win_rate in rows:
                # course_win_rateのwin_rateはパーセント値（例:6.68）で格納されているため
                # track_statsと単位を合わせるために100で割って小数値に変換
                self.course_stats[(venue, surface, distance, condition)] = {
                    'win_rate': win_rate / 100.0
                }
            print(f"       → {len(self.course_stats)}件")
        except Exception as e:
            print(f"       ⚠ course_win_rate 読み込みスキップ: {e}")

        # [v7.3 Fix2] 走数別ペナルティテーブルの確認出力
        print("  [Fix2] 走数別ペナルティテーブル:")
        for runs, penalty in sorted(self.career_penalty_table.items()):
            print(f"       {runs}走目: 係数 {penalty:.2f}")
        print(f"       6走以上: 係数 1.00（ペナルティなし）")

        # [v7.3 Fix3] オッズ帯補正テーブルの確認出力
        print("  [Fix3] MKオッズ帯補正テーブル:")
        for lo, hi, mult in self.odds_mk_table:
            label = f"{lo:.0f}〜{hi:.0f}倍" if hi < 999 else f"{lo:.0f}倍超"
            print(f"       {label}: MK×{mult:.2f}")
        
        print("\n✓ 統計マスター構築完了\n")
    
    def score_horse(self, horse_row, team_type='I'):
        """
        単一馬の12軸スコアを計算
        team_type: 'I'=Upset, 'O'=Mainstream, 'U'=Utility, 'S'=Special
        """
        axes = {}
        
        # CF: キャリア形成
        # [v7.3 Fix1] 純win_rateベース。place_rateによる補正を廃止。
        # [v7.3 Fix2] 走数ペナルティ係数を乗算。
        #   走数5走以下はコールドスタート問題 → CF軸を引き下げ。
        #   「デビュー12ヶ月以内」は物理的に存在しないため走数で代替。
        horse_name = horse_row['馬名'].strip() if isinstance(horse_row['馬名'], str) else str(horse_row['馬名'])
        blood_info = self.df_blood[self.df_blood['馬名'] == horse_name]
        if not blood_info.empty:
            total_races = int(
                blood_info['全成績1着数'].iloc[0] + blood_info['全成績2着数'].iloc[0] +
                blood_info['全成績3着数'].iloc[0] + blood_info['全成績着外数'].iloc[0]
            )
            total_wins = int(blood_info['全成績1着数'].iloc[0])
            if total_races > 0:
                raw_win_rate = total_wins / total_races
                # Fix1: 信頼度係数（10走未満はデフォルト50点に引き戻す）
                confidence = min(1.0, total_races / 10)
                cf_score = raw_win_rate * 100 * confidence + 50 * (1 - confidence)
                cf_score = min(100, cf_score)
                # Fix2: 走数ペナルティ係数を乗算
                # ペナルティは「スコアを常に50点方向（下方向のみ）に圧縮」
                # 50未満の馬をさらに上げることは意図しないため、下方向のみ適用
                penalty = self.career_penalty_table.get(total_races, 1.0)
                if penalty < 1.0 and cf_score > 50:
                    # 50点超の部分のみ圧縮（50以下は触らない）
                    cf_score = 50 + (cf_score - 50) * penalty
            else:
                # 走数0 = 血統CSVにはいるが未出走 → コールドスタート最悪ケース
                cf_score = 20  # Fix2: 旧30 → 20に引き下げ
        else:
            # 血統CSVにない馬 = 完全未知 → Fix2: 旧30 → 20に引き下げ
            cf_score = 20
        axes['CF'] = cf_score
        
        # BF: 血統適性（種牡馬 + 母の父）
        # [v7.3 Fix1] place_rate*20加算を廃止。win_rateのみでスコア算出。
        # 旧: win_rate*100 + place_rate*20  ← 複勝率を追加加算していた（二重計上）
        # 新: win_rate*100 のみ。スケールは変わらず0〜100に収まる。
        sire = horse_row['父馬名']
        dam_sire = horse_row['母の父馬名']
        
        sire_score = 50
        if pd.notna(sire) and sire in self.sire_stats:
            stat = self.sire_stats[sire]
            sire_score = min(100, stat['win_rate'] * 100)
        
        dam_sire_score = 50
        if pd.notna(dam_sire) and dam_sire in self.dam_sire_stats:
            stat = self.dam_sire_stats[dam_sire]
            dam_sire_score = min(100, stat['win_rate'] * 100)
        
        axes['BF'] = (sire_score + dam_sire_score) / 2
        
        # SI: スピードインデックス（上がり3F）
        if pd.notna(horse_row['上がり3Fタイム_sec']):
            agari = horse_row['上がり3Fタイム_sec']
            si_score = max(10, 100 - (agari - 30) * 2)
        else:
            si_score = 50
        axes['SI'] = si_score
        
        # CL: クラス適応性
        # [v7.3 Fix1] +30固定加算を廃止。win_rate*100のみでスコア算出。
        # 旧: win_rate*100 + 30  ← +30はスケール調整の意図だったが全馬一律加算で意味なし
        class_code = horse_row['クラスコード']
        if class_code in self.class_stats:
            stat = self.class_stats[class_code]
            cl_score = min(100, stat['win_rate'] * 100)
        else:
            cl_score = 50
        axes['CL'] = cl_score
        
        # JT: ジョッキー
        # [v7.3 Fix1] +30固定加算を廃止。win_rate*100のみでスコア算出。
        jockey = horse_row['騎手名']
        if pd.notna(jockey) and jockey in self.jockey_stats:
            stat = self.jockey_stats[jockey]
            jt_score = min(100, stat['win_rate'] * 100)
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
        # [v7.4] course_stats（venue×surface×distance×condition）を優先参照。
        # キーが存在しない場合は旧 track_stats（venue×surface）にフォールバック。
        # +20固定加算を廃止（BF/CLと同様に win_rate*100 のみに統一）。
        venue = horse_row['場所']
        surface = horse_row['芝・ダ']
        distance = horse_row['距離']
        condition = horse_row.get('馬場状態', None)
        course_key = (venue, surface, distance, condition)
        track_key = (venue, surface)
        if course_key in self.course_stats:
            # 詳細コース統計: venue×surface×distance×condition
            tr_score = self.course_stats[course_key]['win_rate'] * 100
        elif track_key in self.track_stats:
            # フォールバック: venue×surface のみ（+20固定加算なし）
            tr_score = self.track_stats[track_key]['win_rate'] * 100
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
        # [v7.3 Fix3] 人気順だけでなくオッズ帯を見てMKスコアを補正。
        # 旧: 人気順のみ → 低オッズ馬を自動的に高評価 → 過大評価バグ
        # 新: オッズ帯別に市場の正確度を補正係数で反映
        popularity = horse_row['人気順']
        odds = horse_row['単勝オッズ_num'] if pd.notna(horse_row.get('単勝オッズ_num', None)) else 0.0

        if 1 <= popularity <= 5:
            mk_score = 100 - popularity * 10
        elif 6 <= popularity <= 10:
            mk_score = 50 - (popularity - 5) * 5
        else:
            mk_score = max(10, 30 - (popularity - 10))

        # チーム特性による調整（既存ロジック維持）
        if team_type == 'I' and popularity > 5:
            mk_score += (popularity - 5) * 2
        elif team_type == 'O' and popularity <= 3:
            mk_score += (4 - popularity) * 5

        # [Fix3 rev2] オッズ帯補正（減点のみ）
        # バックテスト検証: 3〜8倍加点は2人気→1人気への誤誘導を引き起こしたため撤廃。
        # 薄い人気フラグ（1〜2人気×4倍超×0.80）も削除:
        #   勝馬が薄い人気だった44件でv7.0=50%→v7.3=36.4%と逆効果だったため。
        # 残す補正: 低オッズ帯（〜3倍）の過大評価を減点するのみ。
        if odds > 0:
            odds_mult = 1.0
            for lo, hi, mult in self.odds_mk_table:
                if lo < odds <= hi:
                    odds_mult = mult
                    break
            if odds_mult != 1.0:
                mk_score = 50 + (mk_score - 50) * odds_mult

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
    
    def score_to_win_prob(self, scores: dict, race_data: pd.DataFrame, temperature: float = 5.0) -> dict:
        """
        スコア → 勝率確率への変換（v7.3 Fix1 核心）

        [修正の背景]
        v7.2では build_statistics() の place_rate（複勝率）を
        そのまま softmax に渡していた。
        複勝率は「3着以内」の確率 = P(win)+P(2nd)+P(3rd) であり、
        理論上 P(win) <= P(place)/3 が成立する。
        この制約を無視すると、複勝率58%の馬の「勝率」が33%と
        過大推定される（実際の上限は約19%）。

        [修正内容]
        1. スコア → softmax確率 (温度T=5.0)
           高温度ほど確率が均一化。T=5.0はスコア差5点で確率比~e^1≈2.7倍。
        2. 統計マスターの place_rate から馬個別の win_rate 上限を推定
           win_rate_cap = place_rate / 3.0
           ※ place_rateがない場合はsoftmax確率をそのまま使用
        3. softmax確率と win_rate_cap の最小値を採用
        4. 正規化（合計=1）

        Parameters
        ----------
        scores : dict  {idx: float}  score_race()の出力
        race_data : DataFrame
        temperature : float  softmax温度（デフォルト5.0）

        Returns
        -------
        dict {idx: float}  推定勝率確率（合計=1.0）
        """
        indices = list(scores.keys())
        score_arr = np.array([scores[i] for i in indices])

        # Step1: softmax変換
        shifted = score_arr - score_arr.max()   # オーバーフロー防止
        softmax_probs = np.exp(shifted / temperature)
        softmax_probs = softmax_probs / softmax_probs.sum()

        # Step2: place_rateから win_rate_cap を算出
        win_caps = []
        for i, idx in enumerate(indices):
            row = race_data.loc[idx]
            # 統計マスターから該当馬の父の place_rate を取得（代理指標）
            # ※ 個別馬の place_rate はキャリアデータから取得
            horse_name = row['馬名'].strip() if isinstance(row['馬名'], str) else str(row['馬名'])
            blood_info = self.df_blood[self.df_blood['馬名'] == horse_name]
            cap = 1.0  # デフォルト: 制約なし
            if not blood_info.empty:
                total_races = (
                    blood_info['全成績1着数'] + blood_info['全成績2着数'] +
                    blood_info['全成績3着数'] + blood_info['全成績着外数']
                ).iloc[0]
                if total_races >= 5:  # 5走以上で統計的に意味がある
                    total_place = (
                        blood_info['全成績1着数'] + blood_info['全成績2着数'] +
                        blood_info['全成績3着数']
                    ).iloc[0]
                    place_rate = float(total_place) / float(total_races)
                    # P(win) <= P(place) / 3 の原則を適用
                    cap = place_rate / 3.0
            win_caps.append(cap)

        win_caps = np.array(win_caps)

        # Step3: softmax確率と cap の最小値
        capped_probs = np.minimum(softmax_probs, win_caps)

        # Step4: 正規化（合計が0になるケースは softmax にフォールバック）
        total = capped_probs.sum()
        if total < 1e-9:
            capped_probs = softmax_probs
        else:
            capped_probs = capped_probs / total

        return {idx: float(p) for idx, p in zip(indices, capped_probs)}

    def predict_race(self, race_data, top_n=9):
        """
        1レースの着順予測
        出力: {'◎': [...], '○': [...], '▲': [...]}

        [v7.3 Fix1] score_race() のスコアに加え、
        score_to_win_prob() で変換した推定勝率を付与。
        ソートはスコアベース（既存ロジック）を維持しつつ、
        win_prob を出力に追加して EV計算で参照可能にする。
        """
        scores = self.score_race(race_data)
        win_probs = self.score_to_win_prob(scores, race_data)

        sorted_horses = sorted(
            [
                (race_data.loc[idx, '馬名'], scores[idx], win_probs[idx], idx)
                for idx in scores.keys()
            ],
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
            'course_stats': self.course_stats,                   # [v7.4]
            'distance_stats': self.distance_stats,
            'career_penalty_table': self.career_penalty_table,  # [v7.3 Fix2]
            'odds_mk_table': self.odds_mk_table,                 # [v7.3 Fix3]
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
        self.course_stats = state.get('course_stats', {})        # [v7.4] 旧pkl互換
        self.distance_stats = state['distance_stats']
        # [v7.3 Fix2] 旧pkl互換: career_penalty_tableがない場合はデフォルト値を使用
        self.career_penalty_table = state.get(
            'career_penalty_table',
            {1: 0.70, 2: 0.70, 3: 0.70, 4: 0.85, 5: 0.85}
        )
        self.odds_mk_table = state.get(
            'odds_mk_table',
            [
                (0.0,  2.0,  0.85),
                (2.0,  3.0,  0.90),
                (3.0,  8.0,  1.05),
                (8.0,  999.0, 1.00),
            ]
        )
        print(f"✓ エンジン読み込み: {filepath}")


# =========================================
# メイン処理
# =========================================

if __name__ == '__main__':
    
    engine = CourseMASTERv73()
    
    result_files = [
        '/mnt/project/2015_2016結果.csv',
        '/mnt/project/2017_2018結果.csv',
        '/mnt/project/2019_2020結果.csv',
        '/mnt/project/2021_2023結果.csv',
        '/mnt/project/2024_2026結果.csv'
    ]
    
    engine.load_data(result_files, '/mnt/project/20260217血統.csv')
    engine.build_statistics()
    engine.save('/mnt/user-data/outputs/course_master_v73_engine.pkl')
    
    print("✓ COURSE MASTER v7.3 初期化完了\n")

