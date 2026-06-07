# -*- coding: utf-8 -*-
"""
_compare_weights.py
旧スコアリング（9軸単純平均）vs 新スコアリング（実力軸×2・人気依存軸×0.3）の比較

  1. 高松宮記念（2026-03-29）での◎○▲変化
  2. 条件A〜D該当レースのバックテスト的中率比較
"""

import sys
import os
import io
import json
import sqlite3

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

PKL_PATH  = os.path.join(BASE_DIR, 'course_master_v70_engine.pkl')
BLOOD_CSV = os.path.join(BASE_DIR, '20260217血統.csv')
DB_PATH   = os.path.join(BASE_DIR, 'course_master.db')

# ──────────────────────────────────────────────
# 重みテーブル定義
# ──────────────────────────────────────────────
WEIGHTS_NEW = {
    'CF': 2.0, 'BF': 2.0, 'SI': 2.0, 'SPD': 2.0, 'JT': 2.0,
    'PD': 1.0, 'HP': 1.0,
    'BL': 0.3, 'MK': 0.3,
}
WEIGHTS_OLD = {k: 1.0 for k in WEIGHTS_NEW}  # 均等重み（旧方式）


def load_engine(use_new_weights: bool):
    """エンジンを読み込み、score_horse を指定の重みでパッチする。"""
    from course_master_v73_engine import CourseMASTERv73
    engine = CourseMASTERv73()
    engine.load(PKL_PATH)
    engine.df_blood = pd.read_csv(BLOOD_CSV, encoding='cp932')

    weights_to_use = WEIGHTS_NEW if use_new_weights else WEIGHTS_OLD

    # score_horse の最終計算部分をモンキーパッチ
    original_score_horse = engine.score_horse.__func__

    def patched_score_horse(self, horse_row, team_type='I'):
        # 元のメソッドを呼んでaxesを返させる前段階を再利用するため
        # ─ axes を再構築する必要があるため、内部実装を直接呼ぶのではなく
        # ─ エンジン自体のコードを書き換えた新版で実行させている。
        # ここでは「旧版の均等平均」に戻す場合のみパッチを適用する。
        import numpy as _np
        import pandas as _pd

        axes = {}
        horse = horse_row

        # CF軸
        blood_df = self.df_blood
        name_col = blood_df.columns[0]
        match = blood_df[blood_df[name_col].str.strip() == str(horse.get('馬名', '')).strip()]
        if not match.empty:
            row = match.iloc[0]
            sire_col = blood_df.columns[1] if len(blood_df.columns) > 1 else None
            sire_name = str(row[sire_col]).strip() if sire_col else ''
            if sire_name in self.sire_stats:
                stat = self.sire_stats[sire_name]
                wr   = stat.get('win_rate', 0.0)
                cnt  = stat.get('count', 0)
                if cnt < 10:
                    cf_score = 50 + (wr * 100 - 50) * (cnt / 10)
                else:
                    cf_score = min(100, wr * 100)
                penalty = self.career_penalty_table.get(
                    int(horse.get('career_count', 99)), 1.0)
                cf_score *= penalty
            else:
                cf_score = 20
        else:
            cf_score = 20
        axes['CF'] = cf_score

        # BF軸
        sire_str = str(horse.get('父馬名', '')).strip() if _pd.notna(horse.get('父馬名', '')) else ''
        bms_str  = str(horse.get('母の父馬名', '')).strip() if _pd.notna(horse.get('母の父馬名', '')) else ''
        distance = int(horse.get('距離', 0))
        if distance <= 1400:
            dist_key = 'sprint_wr'
        elif distance <= 1800:
            dist_key = 'mile_wr'
        elif distance <= 2100:
            dist_key = 'middle_wr'
        else:
            dist_key = 'long_wr'

        sire_score = 50
        if sire_str and sire_str in self.sire_dist_stats:
            v = self.sire_dist_stats[sire_str].get(dist_key)
            if v is not None:
                sire_score = min(100, v * 100)
            elif sire_str in self.sire_stats:
                sire_score = min(100, self.sire_stats[sire_str].get('win_rate', 0) * 100)
        elif sire_str and sire_str in self.sire_stats:
            sire_score = min(100, self.sire_stats[sire_str].get('win_rate', 0) * 100)

        dam_sire_score = 50
        if bms_str and bms_str in self.bms_dist_stats:
            v = self.bms_dist_stats[bms_str].get(dist_key)
            if v is not None:
                dam_sire_score = min(100, v * 100)
            elif bms_str in self.dam_sire_stats:
                dam_sire_score = min(100, self.dam_sire_stats[bms_str].get('win_rate', 0) * 100)
        elif bms_str and bms_str in self.dam_sire_stats:
            dam_sire_score = min(100, self.dam_sire_stats[bms_str].get('win_rate', 0) * 100)
        axes['BF'] = (sire_score + dam_sire_score) / 2

        # SI軸
        agari = horse.get('上がり3Fタイム_sec', 0)
        if _pd.notna(agari) and agari > 0:
            axes['SI'] = max(10, 100 - (agari - 30) * 2)
        else:
            axes['SI'] = 50

        # JT軸
        jockey = str(horse.get('騎手名', '')).strip()
        if jockey in self.jockey_stats:
            axes['JT'] = min(100, self.jockey_stats[jockey].get('win_rate', 0) * 100)
        else:
            axes['JT'] = 50

        # PD軸
        try:
            passages = [horse['通過順1'], horse['通過順2'],
                        horse['通過順3'], horse['通過順4']]
            passages = [p for p in passages if _pd.notna(p) and p > 0]
            if passages:
                avg_p = _np.mean(passages)
                axes['PD'] = max(10, 100 - abs(avg_p - 7) * 3)
            else:
                axes['PD'] = 50
        except:
            axes['PD'] = 50

        # BL軸
        pop = horse.get('人気順', 0)
        axes['BL'] = max(10, 100 - int(pop) * 5) if int(pop) > 0 else 50

        # HP軸
        try:
            w = float(horse.get('斤量_num', 0))
            a = int(horse.get('年齢', 0))
            if w > 0 and a > 0:
                expected = 56 if a >= 4 else (54 if a == 3 else 52)
                axes['HP'] = max(20, 100 - abs(w - expected))
            else:
                axes['HP'] = 50
        except:
            axes['HP'] = 50

        # SPD軸
        jikan = horse.get('走破時計_sec', 0)
        dist  = int(horse.get('距離', 1600))
        if _pd.notna(jikan) and jikan > 0 and dist in self.distance_stats:
            mu  = self.distance_stats[dist].get('mean', jikan)
            std = self.distance_stats[dist].get('std', 1)
            if std > 0:
                z = (mu - jikan) / std
                axes['SPD'] = max(10, min(100, 50 + z * 15))
            else:
                axes['SPD'] = 50
        else:
            axes['SPD'] = 50

        # MK軸
        try:
            pop2 = int(horse.get('人気順', 0))
            if pop2 > 0:
                mk_score = max(10, 100 - pop2 * 4)
            else:
                mk_score = 50
            odds_val = float(horse.get('単勝オッズ_num', 0))
            odds_mult = 1.0
            for lo, hi, mult in self.odds_mk_table:
                if lo <= odds_val < hi:
                    odds_mult = mult
                    break
            if odds_mult != 1.0:
                mk_score = 50 + (mk_score - 50) * odds_mult
            axes['MK'] = mk_score
        except:
            axes['MK'] = 50

        # 重み付き平均
        keys   = list(axes.keys())
        vals   = [axes[k] for k in keys]
        w_list = [weights_to_use.get(k, 1.0) for k in keys]
        return float(_np.average(vals, weights=w_list))

    import types
    engine.score_horse = types.MethodType(patched_score_horse, engine)
    return engine


def run_pred_for_race(engine, race_data: dict) -> list:
    """予測実行 → (horse_no, horse_name, score, popularity) リスト（スコア降順）"""
    from grade_race_predictor import build_race_df
    df = build_race_df(race_data)
    scores = engine.score_race(df)
    sorted_s = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for rank, (idx, score) in enumerate(sorted_s):
        hn    = df.loc[idx, '馬名']
        pop   = df.loc[idx, '人気順']
        hno   = race_data['horses'][idx]['horse_no']
        result.append({'rank': rank + 1, 'horse_no': hno, 'horse_name': hn,
                       'score': score, 'popularity': int(pop)})
    return result


def fmt_mark(entries, mark='◎', n=1):
    lines = []
    for e in entries[:n]:
        lines.append(f"  {mark} 馬番{e['horse_no']:2} {e['horse_name']:<18} "
                     f"スコア:{e['score']:5.1f}  {e['popularity']}人気")
    return '\n'.join(lines)


# ──────────────────────────────────────────────
# 1. 高松宮記念 比較
# ──────────────────────────────────────────────
import warnings
warnings.filterwarnings('ignore')

# レースデータ読み込み
with open(os.path.join(BASE_DIR, '_run_takamatsu_pred.py'), encoding='utf-8') as f:
    src = f.read()

# JSONを抽出
import re
m = re.search(r"json\.dumps\((\{.*\}),\s*ensure_ascii", src, re.DOTALL)
if not m:
    print("[エラー] _run_takamatsu_pred.py からレースデータを抽出できませんでした")
    sys.exit(1)
race_json_str = m.group(1)
TAKAMATSU_RACE = eval(race_json_str)  # dict として評価

print("=" * 68)
print("  エンジン読み込み中（旧）...")
engine_old = load_engine(use_new_weights=False)
pred_old   = run_pred_for_race(engine_old, TAKAMATSU_RACE)

print("  エンジン読み込み中（新）...")
engine_new = load_engine(use_new_weights=True)
pred_new   = run_pred_for_race(engine_new, TAKAMATSU_RACE)

print()
print("=" * 68)
print("  高松宮記念 GⅠ（2026-03-29）中京・芝1200m・良・18頭")
print("  実際の結果: 1着 サトノレーヴ(2人気) / 2着 レッドモンレーヴ(15人気)")
print("=" * 68)

MARKS = [('◎', 0, 1), ('○', 1, 4), ('▲', 4, 9)]

print(f"\n{'印':3}  {'旧（均等重み）':<30}  {'新（実力軸×2/人気軸×0.3）'}")
print('─' * 68)

for mark, s, e in MARKS:
    old_entries = pred_old[s:e]
    new_entries = pred_new[s:e]
    max_len = max(len(old_entries), len(new_entries))
    for i in range(max_len):
        oe = old_entries[i] if i < len(old_entries) else None
        ne = new_entries[i] if i < len(new_entries) else None
        m_str = mark if i == 0 else '  '
        o_str = (f"馬番{oe['horse_no']:2} {oe['horse_name']:<12} {oe['popularity']}人気") if oe else ''
        n_str = (f"馬番{ne['horse_no']:2} {ne['horse_name']:<12} {ne['popularity']}人気") if ne else ''
        changed = '← 変化' if oe and ne and oe['horse_name'] != ne['horse_name'] else ''
        print(f"{m_str:3}  {o_str:<30}  {n_str}  {changed}")

# ◎変化サマリ
old_hon  = pred_old[0]['horse_name']
new_hon  = pred_new[0]['horse_name']
old_mark = {e['horse_name'] for e in pred_old[:9]}
new_mark = {e['horse_name'] for e in pred_new[:9]}
added    = new_mark - old_mark
removed  = old_mark - new_mark
print()
print(f"  ◎: {'変化なし' if old_hon == new_hon else f'{old_hon} → {new_hon}（変化）'}")
if added:
    print(f"  新規入選: {', '.join(added)}")
if removed:
    print(f"  圏外へ: {', '.join(removed)}")

# ──────────────────────────────────────────────
# 2. 条件A〜D バックテスト比較
# ──────────────────────────────────────────────
print()
print("=" * 68)
print("  条件A〜D バックテスト（race_results × blood_category）")
print("  ◎的中率（旧 vs 新）比較")
print("=" * 68)

conn = sqlite3.connect(DB_PATH)

# 条件定義
CONDITIONS = {
    'A': {'venue': '中京', 'surface': 'ダ', 'dist_min': 1401, 'dist_max': 1800,
          'category': 'マイラー系', 'pop_min': 7, 'pop_max': 9, 'bad_cond': []},
    'B': {'venue': '福島', 'surface': 'ダ', 'dist_min': 1600, 'dist_max': 1800,
          'category': 'スタミナ系', 'pop_min': 10, 'pop_max': 99, 'bad_cond': ['稍重', '不良']},
    'C': {'venue': '新潟', 'surface': '芝', 'dist_min': 1801, 'dist_max': 2100,
          'category': 'スタミナ系', 'pop_min': 10, 'pop_max': 99, 'bad_cond': ['重']},
    'D': {'venue': '中京', 'surface': '芝', 'dist_min': 0,    'dist_max': 1400,
          'category': '速力系',    'pop_min': 7,  'pop_max': 9,  'bad_cond': ['不良']},
}

def get_condition_races(cond):
    c = cond
    bad_str = ','.join(f"'{b}'" for b in c['bad_cond']) if c['bad_cond'] else "''"
    query = f"""
    SELECT rr.race_date, rr.venue, rr.surface, rr.distance, rr.track_cond,
           rr.race_no,  rr.horse_name, rr.sire_name, rr.finish_pos, rr.popularity,
           rr.tansho_odds, bc.category
    FROM race_results rr
    LEFT JOIN blood_map bm ON TRIM(rr.horse_name) = TRIM(bm.name)
    LEFT JOIN blood_category bc ON TRIM(bm.sire) = TRIM(bc.sire_name)
    WHERE rr.venue = '{c['venue']}'
      AND rr.surface = '{c['surface']}'
      AND rr.distance BETWEEN {c['dist_min']} AND {c['dist_max']}
      AND rr.popularity BETWEEN {c['pop_min']} AND {c['pop_max']}
      AND bc.category = '{c['category']}'
      {'AND rr.track_cond NOT IN (' + bad_str + ')' if c['bad_cond'] else ''}
    ORDER BY rr.race_date, rr.venue, rr.race_no
    """
    return pd.read_sql(query, conn)


# バックテスト用エンジンは軽量化のため score_horse を直接モンキーパッチ済みのものを使用
# ここでは DB の race_results からスコアを擬似的に計算する簡略バックテスト
# （sire_dist_stats + blood_category_map を使った BF軸と BL/MK を変えた場合の差分）

def simple_backtest(df_cond, old_engine, new_engine):
    """
    条件該当馬群でレースごとに◎を決め、1着との一致を確認する。
    スコア計算: sire_dist_stats の BF 軸 + popularity ベースの BL/MK のみで簡略計算。
    （フル計算は重いため、旧版と新版の差が出る軸に絞る）
    """
    races = df_cond.groupby(['race_date', 'venue', 'race_no'])
    hit_old, hit_new, total = 0, 0, 0

    for (date, venue, rno), group in races:
        if len(group) < 2:
            continue

        # 全出走馬（同レース）を取得して旧/新スコアを計算
        # 簡略: BF・BL・MK の3軸差分のみを反映
        scores_old = {}
        scores_new = {}

        for _, row in group.iterrows():
            sire = str(row.get('sire_name', '') or '').strip()
            pop  = int(row.get('popularity', 0) or 0)
            dist = int(row.get('distance', 1600) or 1600)

            # 距離帯キー
            if dist <= 1400:   dk = 'sprint_wr'
            elif dist <= 1800: dk = 'mile_wr'
            elif dist <= 2100: dk = 'middle_wr'
            else:              dk = 'long_wr'

            # BF スコア
            bf = 50
            if sire in old_engine.sire_dist_stats:
                v = old_engine.sire_dist_stats[sire].get(dk)
                bf = min(100, v * 100) if v is not None else 50
            elif sire in old_engine.sire_stats:
                bf = min(100, old_engine.sire_stats[sire].get('win_rate', 0) * 100)

            # BL スコア
            bl = max(10, 100 - pop * 5) if pop > 0 else 50

            # MK スコア（人気順ベースのみ）
            mk = max(10, 100 - pop * 4) if pop > 0 else 50

            # 他の軸は旧/新で同じ（CF/SI/SPD/JT/PD/HP は同値）
            fixed = 50.0  # CF・SI・SPD・JT・PD・HP の近似代表値

            # 旧: 均等 1/9
            s_old = (fixed * 5 + bf + bl + mk + 50) / 9  # PD・HP=50近似

            # 新: 重み付き
            # CF×2(50) + BF×2 + SI×2(50) + SPD×2(50) + JT×2(50) + PD×1(50) + HP×1(50) + BL×0.3 + MK×0.3
            total_w = 2 + 2 + 2 + 2 + 2 + 1 + 1 + 0.3 + 0.3  # = 12.6
            s_new = (50*2 + bf*2 + 50*2 + 50*2 + 50*2 + 50*1 + 50*1 + bl*0.3 + mk*0.3) / total_w

            hname = row['horse_name']
            scores_old[hname] = s_old
            scores_new[hname] = s_new

        if not scores_old:
            continue

        best_old = max(scores_old, key=scores_old.get)
        best_new = max(scores_new, key=scores_new.get)

        # 1着馬（finish_pos=1 かつ popularity が条件範囲内の馬がいるレース）
        winner_rows = group[group['finish_pos'] == 1]
        if winner_rows.empty:
            continue
        winner = winner_rows.iloc[0]['horse_name']

        total += 1
        if best_old == winner:
            hit_old += 1
        if best_new == winner:
            hit_new += 1

    return total, hit_old, hit_new


print()
print(f"{'条件':^4}  {'レース数':>7}  {'旧的中率':>8}  {'新的中率':>8}  {'差分':>7}")
print('─' * 50)

for cond_id, cond in CONDITIONS.items():
    df_c = get_condition_races(cond)
    if df_c.empty:
        print(f"  {cond_id}   データなし")
        continue
    total, hit_old, hit_new = simple_backtest(df_c, engine_old, engine_new)
    if total == 0:
        print(f"  {cond_id}   有効レース0")
        continue
    r_old = hit_old / total * 100
    r_new = hit_new / total * 100
    diff  = r_new - r_old
    arrow = '▲' if diff >= 0 else '▼'
    print(f"  {cond_id}   {total:7d}R  {r_old:7.2f}%  {r_new:7.2f}%  "
          f"{arrow}{abs(diff):.2f}%")

conn.close()

print()
print("=" * 68)
print("  バックアップ: course_master_v73_engine_backup_20260330.py")
print("  変更ファイル: course_master_v73_engine.py")
print("=" * 68)
