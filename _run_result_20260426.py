# -*- coding: utf-8 -*-
"""
2026-04-26 結果照合・P&L記録スクリプト
  フローラS G2  (東京11R)  ◎エンネ(馬番13)         → 外れ
  マイラーズC G2 (京都11R)  ◎ランスオブカオス(馬番18) → 外れ(11着)
  条件B 福島7R              3頭(12/2/15)            → 全外れ
"""
import sys, io, os, json, sqlite3
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path  = os.path.join(BASE_DIR, 'course_master.db')

# ── 購入候補読み込み ──────────────────────────────────────
candidates_file = os.path.join(BASE_DIR, 'candidates_20260426.json')
with open(candidates_file, encoding='utf-8') as f:
    data = json.load(f)

RACE_DATE = data['date']   # "2026-04-26"
VENUE     = data['venue']  # "東京/京都/福島"

# ── 実際の買い目（単勝+馬連含む全ベット） ─────────────────
# [レース, 馬券種, 馬番(◎), 馬番(○), 金額, 説明]
BETS = [
    # フローラS G2 東京11R (ADI=57.7: 単勝+馬連)
    {"race": "フローラS G2 東京11R",   "type": "単勝", "horse_no": 13, "horse_name": "エンネ",          "amount": 200},
    {"race": "フローラS G2 東京11R",   "type": "馬連", "horse_no": 13, "horse_name": "エンネ−ペンダント", "amount": 100,
     "umaren": (13, 6)},  # ◎13 - ○6ペンダント
    # マイラーズC G2 京都11R (ADI=71.9: 単勝のみ)
    {"race": "マイラーズC G2 京都11R", "type": "単勝", "horse_no": 18, "horse_name": "ランスオブカオス", "amount": 200},
    # 条件B 福島7R
    {"race": "条件B 福島7R",           "type": "単勝", "horse_no": 12, "horse_name": "レイフロレット",  "amount": 100},
    {"race": "条件B 福島7R",           "type": "単勝", "horse_no":  2, "horse_name": "グランコネクシオン","amount": 100},
    {"race": "条件B 福島7R",           "type": "単勝", "horse_no": 15, "horse_name": "ノアチュロス",    "amount": 100},
]

# ── 実際のレース結果 ──────────────────────────────────────
RESULTS = {
    "フローラS G2 東京11R": {
        "winner_no": 7, "winner_name": "ゴールデンハインド",
        "tansho_odds": 16.6, "tansho_payout": 1660,
        "umaren_combo": (2, 7), "umaren_payout": 2600,
    },
    "マイラーズC G2 京都11R": {
        "winner_no": 9, "winner_name": "アドマイヤズーム",
        "tansho_odds": 4.1,  "tansho_payout": 410,
        "umaren_combo": None, "umaren_payout": None,
    },
    "条件B 福島7R": {
        "winner_no": 10, "winner_name": "ユージュアーナ",
        "tansho_odds": 5.2,  "tansho_payout": 520,
        "umaren_combo": None, "umaren_payout": None,
    },
}

# ── 的中判定 ─────────────────────────────────────────────
total_bet    = 0
total_return = 0
detail_rows  = []

print('=' * 65)
print(f'  2026-04-26 結果照合  {VENUE}')
print('=' * 65)

for bet in BETS:
    res = RESULTS[bet["race"]]
    total_bet += bet["amount"]

    if bet["type"] == "単勝":
        hit = (bet["horse_no"] == res["winner_no"])
        payout = int(res["tansho_odds"] * bet["amount"]) if hit else 0

    elif bet["type"] == "馬連":
        combo = bet.get("umaren", ())
        win_combo = res.get("umaren_combo")
        hit = (win_combo is not None and set(combo) == set(win_combo))
        if hit:
            payout = int(res["umaren_payout"] / 100 * bet["amount"])
        else:
            payout = 0

    total_return += payout
    mark = '◎的中！' if hit else '×'
    print(f'  [{mark}] {bet["race"]}  {bet["type"]}  {bet["horse_name"]}  {bet["amount"]}円'
          + (f'  → 払戻 {payout}円' if hit else ''))
    detail_rows.append({
        "race":       bet["race"],
        "type":       bet["type"],
        "horse_no":   bet["horse_no"],
        "horse_name": bet["horse_name"],
        "amount":     bet["amount"],
        "hit":        hit,
        "payout":     payout,
        "winner":     f'馬番{res["winner_no"]} {res["winner_name"]}({res["tansho_odds"]}倍)',
    })

print()
net = total_return - total_bet
roi = (total_return / total_bet * 100) if total_bet > 0 else 0
print(f'  投資: {total_bet}円  払戻: {total_return}円  収支: {"+" if net>=0 else ""}{net}円  回収率: {roi:.1f}%')
print('=' * 65)

# ── pnl_20260426.json 保存 ─────────────────────────────────
pnl = {
    "date":         RACE_DATE,
    "venue":        VENUE,
    "total_bet":    total_bet,
    "total_return": total_return,
    "net":          net,
    "roi_pct":      round(roi, 1),
    "detail":       detail_rows,
    "race_results": {
        "フローラS G2 東京11R":  "1着 馬番7 ゴールデンハインド(16.6倍) / 馬連2-7(2600円)",
        "マイラーズC G2 京都11R": "1着 馬番9 アドマイヤズーム(4.1倍) / ◎ランスオブカオス11着",
        "条件B 福島7R":          "1着 馬番10 ユージュアーナ(5.2倍) / 条件B3頭全外れ",
    },
    "umaren_first_result": {
        "race":    "フローラS G2 東京11R",
        "combo":   "◎13エンネ − ○6ペンダント",
        "winner_combo": "2-7",
        "hit":     False,
        "note":    "ADI57.7にて馬連初戦。1着ゴールデンハインド(馬番7)・2着ソーダズリング(馬番2)でともに予測外",
    },
}

pnl_path = os.path.join(BASE_DIR, 'pnl_20260426.json')
with open(pnl_path, 'w', encoding='utf-8') as f:
    json.dump(pnl, f, ensure_ascii=False, indent=2)
print(f'\npnl_20260426.json 保存完了: {pnl_path}')

# ── DB記録（condition_bet_history） ───────────────────────
conn = sqlite3.connect(db_path)
conn.execute('''
    CREATE TABLE IF NOT EXISTS condition_bet_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_date TEXT, venue TEXT, race_no INTEGER,
        horse_no INTEGER, horse_name TEXT, condition_type TEXT,
        tansho_odds REAL, finish_pos INTEGER, result TEXT, notes TEXT
    )
''')

# candidates_20260426.jsonの5頭をDBに記録
cand_map = {
    (11, 13): ("edge+anababa", 7.2,  None,     "不的中", "1着馬番7 ゴールデンハインド"),
    (11, 18): ("edge+anababa", 18.6, None,     "不的中", "1着馬番9 アドマイヤズーム / 11着"),
    (7,  12): ("condB",        21.0, None,     "不的中", "1着馬番10 ユージュアーナ"),
    (7,   2): ("condB",        34.3, None,     "不的中", "1着馬番10 ユージュアーナ"),
    (7,  15): ("condB",        56.9, None,     "不的中", "1着馬番10 ユージュアーナ"),
}
horse_names = {(11,13): "エンネ", (11,18): "ランスオブカオス",
               (7,12): "レイフロレット", (7,2): "グランコネクシオン", (7,15): "ノアチュロス"}

inserted = 0
skipped  = 0
for (rno, hno), (cond, odds, fpos, res_str, note) in cand_map.items():
    dup = conn.execute(
        'SELECT id FROM condition_bet_history WHERE race_date=? AND venue=? AND race_no=? AND horse_no=?',
        (RACE_DATE, VENUE, rno, hno)
    ).fetchone()
    if dup:
        skipped += 1
        continue
    conn.execute(
        '''INSERT INTO condition_bet_history
           (race_date,venue,race_no,horse_no,horse_name,condition_type,tansho_odds,finish_pos,result,notes)
           VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (RACE_DATE, VENUE, rno, hno, horse_names[(rno,hno)], cond, odds, fpos, res_str, note)
    )
    inserted += 1

conn.commit()
conn.close()
print(f'DB記録: {inserted}件追加 / {skipped}件スキップ（重複）')
