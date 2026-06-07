"""
COURSE MASTER v7.0 - Web予測ツール
起動: python prediction_app.py
ブラウザで http://localhost:5000 を開く
"""

import os
import sys
import json
import webbrowser
import threading
import pandas as pd
from flask import Flask, request, jsonify, render_template_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from course_master_v73_engine import CourseMASTERv73

app = Flask(__name__)
engine = None

# ─────────────────────────────────────────
# HTMLテンプレート
# ─────────────────────────────────────────
HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>COURSE MASTER v7.3</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: 'Meiryo', sans-serif; background: #f4f4f4; color: #333; }

    header {
      background: #1a1a2e;
      color: #fff;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    header h1 { font-size: 1.2rem; letter-spacing: 1px; }
    header span { font-size: 0.75rem; color: #aaa; }

    .container { max-width: 860px; margin: 24px auto; padding: 0 16px; }

    /* 入力フォーム */
    .search-box {
      background: #fff;
      border-radius: 8px;
      padding: 20px 24px;
      box-shadow: 0 1px 4px rgba(0,0,0,.1);
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: flex-end;
    }
    .field { display: flex; flex-direction: column; gap: 4px; }
    .field label { font-size: 0.8rem; color: #666; }
    .field input {
      border: 1px solid #ccc;
      border-radius: 4px;
      padding: 8px 10px;
      font-size: 0.95rem;
      width: 180px;
    }
    .field input:focus { outline: none; border-color: #4a90d9; }

    .btn-predict {
      background: #1a1a2e;
      color: #fff;
      border: none;
      border-radius: 4px;
      padding: 9px 24px;
      font-size: 0.95rem;
      cursor: pointer;
      transition: background .2s;
    }
    .btn-predict:hover { background: #2e2e5e; }
    .btn-predict:disabled { background: #999; cursor: default; }

    .hint {
      margin-top: 8px;
      font-size: 0.78rem;
      color: #888;
      width: 100%;
    }

    /* 結果エリア */
    #result { margin-top: 20px; }

    .race-header {
      background: #1a1a2e;
      color: #fff;
      border-radius: 8px 8px 0 0;
      padding: 12px 20px;
      display: flex;
      gap: 20px;
      align-items: baseline;
    }
    .race-header .race-name { font-size: 1.1rem; font-weight: bold; }
    .race-header .race-meta { font-size: 0.8rem; color: #aaa; }

    .result-table-wrap {
      background: #fff;
      border-radius: 0 0 8px 8px;
      box-shadow: 0 1px 4px rgba(0,0,0,.1);
      overflow: hidden;
    }
    table { width: 100%; border-collapse: collapse; }
    thead { background: #eef2ff; }
    thead th {
      padding: 10px 14px;
      font-size: 0.8rem;
      color: #555;
      text-align: center;
      border-bottom: 1px solid #dde;
    }
    thead th:nth-child(2) { text-align: left; }
    tbody tr { border-bottom: 1px solid #eee; }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: #f9f9ff; }
    tbody td {
      padding: 10px 14px;
      font-size: 0.92rem;
      text-align: center;
    }
    tbody td:nth-child(2) { text-align: left; font-weight: bold; }

    /* 印スタイル */
    .mark {
      display: inline-block;
      width: 28px;
      height: 28px;
      line-height: 28px;
      border-radius: 50%;
      text-align: center;
      font-weight: bold;
      font-size: 1rem;
    }
    .mark-hon  { background: #e63946; color: #fff; }   /* ◎ */
    .mark-niban { background: #457b9d; color: #fff; }  /* ○ */
    .mark-sab  { background: #2a9d8f; color: #fff; }   /* ▲ */

    /* スコアバー */
    .score-bar-wrap { display: flex; align-items: center; gap: 8px; }
    .score-bar {
      height: 8px;
      border-radius: 4px;
      background: linear-gradient(90deg, #4a90d9, #1a1a2e);
      min-width: 4px;
    }
    .score-val { font-size: 0.85rem; color: #555; white-space: nowrap; }

    /* 的中バッジ */
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 0.75rem;
      font-weight: bold;
    }
    .badge-win    { background: #e63946; color: #fff; }
    .badge-place  { background: #457b9d; color: #fff; }
    .badge-miss   { background: #bbb;    color: #fff; }

    /* 判定サマリーバナー */
    .result-summary {
      padding: 10px 20px;
      font-size: 0.95rem;
      font-weight: bold;
      border-radius: 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .summary-win   { background: #fdecea; color: #c0392b; border-left: 4px solid #e63946; }
    .summary-place { background: #eaf0f8; color: #2c5f8a; border-left: 4px solid #457b9d; }
    .summary-miss  { background: #f5f5f5; color: #777;    border-left: 4px solid #bbb; }

    /* 戻るボタン */
    .btn-back {
      background: none;
      border: 1px solid #aaa;
      border-radius: 4px;
      padding: 6px 14px;
      font-size: 0.85rem;
      color: #555;
      cursor: pointer;
      margin-bottom: 12px;
      transition: background .15s;
    }
    .btn-back:hover { background: #eee; }

    /* エラー */
    .error-box {
      background: #fff3f3;
      border: 1px solid #e63946;
      border-radius: 8px;
      padding: 16px 20px;
      color: #c0392b;
    }

    /* ローディング */
    .loading {
      text-align: center;
      padding: 32px;
      color: #888;
      font-size: 0.9rem;
    }

    /* 凡例 */
    .legend {
      margin-top: 12px;
      font-size: 0.78rem;
      color: #888;
      display: flex;
      gap: 16px;
    }
    .legend span { display: flex; align-items: center; gap: 4px; }
  </style>
</head>
<body>

<header>
  <h1>&#x1F3C7; COURSE MASTER v7.3</h1>
  <span>JRA競馬予測エンジン</span>
</header>

<div class="container">

  <div class="search-box">
    <div class="field">
      <label>レース日付</label>
      <input type="date" id="race-date" value="">
    </div>
    <div class="field">
      <label>レースキー（7桁）</label>
      <input type="text" id="race-key" placeholder="例: 5261212" maxlength="9">
    </div>
    <button class="btn-predict" id="btn" onclick="predict()">予測する</button>
    <p class="hint">
      レースキーはレースIDの先頭7桁です。<br>
      日付を選んで「レース一覧を取得」するか、レースキーを直接入力してください。
    </p>
    <button class="btn-predict" id="btn-list" onclick="listRaces()" style="background:#555;">
      日付からレース一覧を取得
    </button>
  </div>

  <!-- レース一覧 -->
  <div id="race-list" style="margin-top:16px;"></div>

  <!-- 予測結果 -->
  <div id="result"></div>

</div>

<script>
function fmtDate(d) {
  // date input value → "YYYYMMDD"
  return d.replace(/-/g, '');
}

async function listRaces() {
  const dateVal = document.getElementById('race-date').value;
  if (!dateVal) { alert('日付を選択してください'); return; }

  document.getElementById('race-list').innerHTML = '<div class="loading">レース一覧を取得中...</div>';
  document.getElementById('result').innerHTML = '';

  const res = await fetch('/api/races', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ date: fmtDate(dateVal) })
  });
  const data = await res.json();

  if (data.error) {
    document.getElementById('race-list').innerHTML =
      `<div class="error-box">${data.error}</div>`;
    return;
  }

  if (data.races.length === 0) {
    document.getElementById('race-list').innerHTML =
      '<div class="error-box">該当日のレースが見つかりませんでした。</div>';
    return;
  }

  let html = '<div style="background:#fff;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.1);padding:16px 20px;">';
  html += `<p style="font-size:.85rem;color:#666;margin-bottom:10px;">`;
  html += `${data.races.length}レース見つかりました。クリックで予測します。</p>`;
  html += '<div style="display:flex;flex-wrap:wrap;gap:8px;">';
  for (const r of data.races) {
    html += `<button onclick="selectRace('${r.key}')"
      style="border:1px solid #ccc;background:#f9f9ff;border-radius:4px;
             padding:6px 12px;cursor:pointer;font-size:.85rem;text-align:left;">
      <strong>${r.key}</strong><br>
      <span style="color:#555;font-size:.75rem;">${r.name} / ${r.venue} / ${r.entries}頭</span>
    </button>`;
  }
  html += '</div></div>';
  document.getElementById('race-list').innerHTML = html;
}

function selectRace(key) {
  document.getElementById('race-key').value = key;
  predict();
}

async function predict() {
  const key = document.getElementById('race-key').value.trim();
  if (!key) { alert('レースキーを入力してください'); return; }

  document.getElementById('result').innerHTML = '<div class="loading">予測計算中...</div>';
  document.getElementById('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
  document.getElementById('btn').disabled = true;

  const res = await fetch('/api/predict', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ race_key: key })
  });
  const data = await res.json();
  document.getElementById('btn').disabled = false;

  if (data.error) {
    document.getElementById('result').innerHTML =
      `<div class="error-box">${data.error}</div>`;
    return;
  }

  renderResult(data);
}

function backToList() {
  document.getElementById('result').innerHTML = '';
  document.getElementById('race-list').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderResult(data) {
  const markClass = { '◎': 'mark-hon', '○': 'mark-niban', '▲': 'mark-sab' };
  const maxScore = Math.max(...data.predictions.map(p => p.score));

  // ◎ 馬の着順を取得して判定サマリーを作成
  const hon = data.predictions.find(p => p.mark === '◎');
  let summaryHtml = '';
  if (hon && hon.finish > 0) {
    if (hon.finish === 1) {
      summaryHtml = `<div class="result-summary summary-win">🎯 ◎ ${hon.horse_name} が1着的中！</div>`;
    } else if (hon.finish <= 3) {
      summaryHtml = `<div class="result-summary summary-place">📍 ◎ ${hon.horse_name} は${hon.finish}着・複勝的中（1着外れ）</div>`;
    } else {
      summaryHtml = `<div class="result-summary summary-miss">✗ ◎ ${hon.horse_name} は${hon.finish}着・外れ</div>`;
    }
  }

  let rows = '';
  for (const p of data.predictions) {
    const barWidth = Math.round((p.score / maxScore) * 120);

    // 着順バッジ（finish > 0 のとき実績を表示）
    let badge = '';
    if (p.finish > 0) {
      if (p.finish === 1)       badge = `<span class="badge badge-win">${p.finish}着 ✓</span>`;
      else if (p.finish <= 3)   badge = `<span class="badge badge-place">${p.finish}着</span>`;
      else                      badge = `<span class="badge badge-miss">${p.finish}着</span>`;
    }

    rows += `<tr>
      <td><span class="mark ${markClass[p.mark]}">${p.mark}</span></td>
      <td>${p.horse_name}</td>
      <td>
        <div class="score-bar-wrap">
          <div class="score-bar" style="width:${barWidth}px"></div>
          <span class="score-val">${p.score.toFixed(1)}</span>
        </div>
      </td>
      <td>${p.popularity > 0 ? p.popularity + '番人気' : '-'}</td>
      <td>${badge}</td>
    </tr>`;
  }

  const html = `
    <button class="btn-back" onclick="backToList()">← レース一覧に戻る</button>
    <div class="race-header">
      <span class="race-name">${data.race_name}</span>
      <span class="race-meta">${data.race_date} ／ ${data.venue} ／ ${data.surface}${data.distance}m ／ ${data.entries}頭立て</span>
    </div>
    ${summaryHtml}
    <div class="result-table-wrap">
      <table>
        <thead>
          <tr>
            <th>印</th>
            <th style="text-align:left">馬名</th>
            <th>スコア</th>
            <th>人気</th>
            <th>実績</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <div class="legend">
      <span><span class="mark mark-hon" style="width:18px;height:18px;line-height:18px;font-size:.7rem;">◎</span>本命（1頭）</span>
      <span><span class="mark mark-niban" style="width:18px;height:18px;line-height:18px;font-size:.7rem;">○</span>対抗（3頭）</span>
      <span><span class="mark mark-sab" style="width:18px;height:18px;line-height:18px;font-size:.7rem;">▲</span>単穴（5頭）</span>
    </div>
  `;

  document.getElementById('result').innerHTML = html;
  document.getElementById('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
</script>

</body>
</html>
"""

# ─────────────────────────────────────────
# エンジン初期化
# ─────────────────────────────────────────
def init_engine():
    global engine
    print("[起動] エンジンをロード中...")
    e = CourseMASTERv73()
    e.load(os.path.join(BASE_DIR, 'course_master_v70_engine.pkl'))
    e.df_blood = pd.read_csv(
        os.path.join(BASE_DIR, '20260217血統.csv'),
        encoding='cp932', low_memory=False
    )
    for col in ['全成績1着数', '全成績2着数', '全成績3着数', '全成績着外数']:
        e.df_blood[col] = pd.to_numeric(e.df_blood[col], errors='coerce').fillna(0).astype(int)
    engine = e
    print("[起動] エンジン準備完了")


def load_result_csv(year_hint=None):
    """結果CSVを読み込む（年の手がかりがあれば該当CSVを優先）"""
    files = [
        ('2024_2026結果.csv', 2024, 2026),
        ('2021_2023結果.csv', 2021, 2023),
        ('2019_2020結果.csv', 2019, 2020),
        ('2017_2018結果.csv', 2017, 2018),
        ('2015_2016結果.csv', 2015, 2016),
    ]
    if year_hint:
        y = int(year_hint)
        files = sorted(files, key=lambda f: 0 if f[1] <= y <= f[2] else 1)

    dfs = []
    for fname, _, _ in files[:2]:  # 速度のため最大2ファイル
        path = os.path.join(BASE_DIR, fname)
        if os.path.exists(path):
            dfs.append(pd.read_csv(path, encoding='cp932', low_memory=False))

    if not dfs:
        return None
    df = pd.concat(dfs, ignore_index=True)

    # 血統データをマージ
    blood_slim = engine.df_blood[['血統登録番号', '種牡馬名', '母名', '母の父名']].copy()
    blood_slim.columns = ['血統登録番号', '父馬名_b', '母馬名_b', '母の父馬名_b']
    df = df.merge(blood_slim, on='血統登録番号', how='left')
    df['父馬名'] = df['父馬名'].fillna(df['父馬名_b'])
    df['母馬名'] = df['母馬名'].fillna(df['母馬名_b'])
    df['母の父馬名'] = df['母の父馬名'].fillna(df['母の父馬名_b'])
    df.drop(['父馬名_b', '母馬名_b', '母の父馬名_b'], axis=1, inplace=True)

    # 数値化
    df['確定着順'] = pd.to_numeric(df['確定着順'], errors='coerce').fillna(0).astype(int)
    df['人気順']   = pd.to_numeric(df['人気順'],   errors='coerce').fillna(0).astype(int)
    df['走破時計_sec']      = pd.to_numeric(df['走破時計'],    errors='coerce')
    df['単勝オッズ_num']    = pd.to_numeric(df['単勝オッズ'],  errors='coerce').fillna(0)
    df['斤量_num']          = pd.to_numeric(df['斤量'],        errors='coerce')
    df['馬体重_num']        = pd.to_numeric(df['馬体重'],      errors='coerce')
    df['上がり3Fタイム_sec'] = pd.to_numeric(df['上がり3Fタイム'], errors='coerce')

    df['レースキー'] = df['レースID'].astype(str).str[:7]
    return df


# ─────────────────────────────────────────
# APIエンドポイント
# ─────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML)


@app.route('/api/races', methods=['POST'])
def api_races():
    """指定日付のレース一覧を返す  date: "YYYYMMDD" 形式"""
    data = request.get_json()
    date_str = data.get('date', '')  # e.g. "20260201"

    if len(date_str) != 8:
        return jsonify({'error': '日付形式が不正です（YYYYMMDD）'})

    year = date_str[:4]   # "2026"
    # CSVの年・月・日カラムと照合するための値
    yy = int(date_str[2:4])  # 年の下2桁（CSVは "26" 形式）
    mm = int(date_str[4:6])
    dd = int(date_str[6:8])

    try:
        df = load_result_csv(year_hint=year)
    except Exception as e:
        return jsonify({'error': f'データ読み込みエラー: {str(e)}'})

    if df is None:
        return jsonify({'error': 'CSVファイルが見つかりません'})

    day_df = df[(df['年'] == yy) & (df['月'] == mm) & (df['日'] == dd)]
    if len(day_df) == 0:
        return jsonify({'races': []})

    races = []
    for key in sorted(day_df['レースキー'].unique()):
        rd = day_df[day_df['レースキー'] == key]
        races.append({
            'key': key,
            'name': str(rd['レース名'].iloc[0]),
            'venue': str(rd['場所'].iloc[0]),
            'entries': len(rd),
        })
    return jsonify({'races': races})


@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.get_json()
    race_key = str(data.get('race_key', '')).strip()

    if not race_key:
        return jsonify({'error': 'レースキーが指定されていません'})

    try:
        # 年の推定（先頭2桁: "52" → 2025-2026年相当）
        year_hint = '20' + race_key[:2] if len(race_key) >= 2 else None
        df = load_result_csv(year_hint=year_hint)
    except Exception as e:
        return jsonify({'error': f'データ読み込みエラー: {str(e)}'})

    if df is None:
        return jsonify({'error': 'CSVファイルが見つかりません'})

    race_df = df[df['レースキー'] == race_key].copy().reset_index(drop=True)
    if len(race_df) < 2:
        return jsonify({'error': f'レースキー "{race_key}" のデータが見つかりません（{len(race_df)}頭）'})

    try:
        predictions = engine.predict_race(race_df)
    except Exception as e:
        return jsonify({'error': f'予測エラー: {str(e)}'})

    results = []
    for mark, horses in predictions.items():
        for horse_name, score, win_prob, idx in horses:
            # reset_index後なので idx は 0-based の整数。.iat で確実にスカラー取得
            finish = int(race_df.at[idx, '確定着順'])
            pop    = int(race_df.at[idx, '人気順'])
            results.append({
                'mark': mark,
                'horse_name': str(horse_name).strip(),
                'score': round(float(score), 1),
                'finish': finish,
                'popularity': pop,
            })

    mark_order = {'◎': 0, '○': 1, '▲': 2}
    results.sort(key=lambda x: (mark_order.get(x['mark'], 3), -x['score']))

    row = race_df.iloc[0]
    return jsonify({
        'race_key':  race_key,
        'race_name': str(row.get('レース名', '')),
        'race_date': f"{int(row['年'])}/{int(row['月']):02d}/{int(row['日']):02d}",
        'venue':     str(row.get('場所', '')),
        'surface':   str(row.get('芝・ダ', '')),
        'distance':  str(row.get('距離', '')),
        'entries':   len(race_df),
        'predictions': results,
    })


# ─────────────────────────────────────────
# 起動
# ─────────────────────────────────────────
if __name__ == '__main__':
    init_engine()
    # 少し遅らせてからブラウザを自動で開く
    def open_browser():
        import time; time.sleep(1.2)
        webbrowser.open('http://localhost:5000')
    threading.Thread(target=open_browser, daemon=True).start()
    print("[起動] http://localhost:5000 で起動します")
    app.run(host='localhost', port=5000, debug=False)
