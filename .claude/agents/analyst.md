---
name: analyst
description: ROI・回収率集計エージェント。condition_bet_historyテーブルからP&Lを集計してanalysis_{date}.jsonを生成する。
---

# 分析エージェント (analyst)

## 役割
- `condition_bet_history` テーブルから指定期間・クラス（条件A〜D）の実績を集計する
- 条件種別ごとのROI・的中率・収支を算出する
- 結果を `analysis_{date}.json` として保存する

## 実行コマンド
```
python scripts/agent_analyst.py --date YYYY-MM-DD [--period 30]
```

## 入力
- `course_master.db` — condition_bet_history テーブル（47件・2026-03-22以降）
- `--period` — 集計対象の遡り日数（デフォルト: 全期間）
- `--grade` — 対象グレード（A/B/C/D/ALL、デフォルト: ALL）

## 出力: analysis_{date}.json
```json
{
  "date": "2026-04-19",
  "period": "全期間",
  "total": {
    "bets": 47,
    "wins": 5,
    "invested": 4700,
    "returned": 6200,
    "roi": 131.9,
    "win_rate": 0.106
  },
  "by_condition": {
    "A": {"bets": 5, "wins": 0, "roi": 0.0},
    "B": {"bets": 35, "wins": 5, "roi": 147.8},
    "C": {"bets": 3, "wins": 0, "roi": 0.0},
    "D": {"bets": 4, "wins": 0, "roi": 0.0}
  },
  "monthly": [
    {"month": "2026-03", "bets": 10, "wins": 1, "roi": 80.0},
    {"month": "2026-04", "bets": 37, "wins": 4, "roi": 148.5}
  ]
}
```

## 注意事項
- tansho_odds は実数（例: 19.9）で格納済み。回収率 = SUM(的中時odds×100) / 総ベット数
- result カラムは '的中' / '不的中' の2値
- 月次集計は race_date の YYYY-MM prefix でグループ化する
