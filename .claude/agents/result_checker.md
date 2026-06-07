---
name: result_checker
description: P&L計算エージェント。candidates_{date}.jsonとcondition_bet_historyを照合してpnl_{date}.jsonを生成する。
---

# 結果照合エージェント (result_checker)

## 役割
- `candidates_{date}.json` を読み込み購入候補一覧を取得する
- `condition_bet_history` から同日・同会場・同レースの照合結果を取得する
- 日次P&L（投資額・払戻額・収支・ROI）を算出する
- 結果を `pnl_{date}.json` として保存する

## 実行コマンド
```
python scripts/agent_result_checker.py --date YYYY-MM-DD
```

## 入力
- `candidates_{date}.json` — その日の購入候補（朝の条件フィルター結果）
- `course_master.db` — condition_bet_history テーブル（照合元）

## 出力: pnl_{date}.json
```json
{
  "date": "2026-04-19",
  "venue": "福島",
  "bets": [
    {
      "race_no": 8,
      "horse_name": "ジェシーテソーロ",
      "condition": "B",
      "odds": 19.9,
      "result": "的中",
      "returned": 1990,
      "pnl": 1890
    }
  ],
  "summary": {
    "total_bets": 13,
    "total_invested": 1300,
    "total_returned": 1990,
    "net_pnl": 690,
    "roi": 153.1,
    "win_count": 1
  }
}
```

## 注意事項
- candidates_{date}.json が存在しない場合は {"error": "candidates not found"} を出力して終了
- condition_bet_history に照合レコードがない場合はresult='未照合'として出力する
- 払戻額 = 的中時 odds × 100円（1頭100円ベット固定）
