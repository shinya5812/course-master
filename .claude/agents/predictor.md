---
name: predictor
description: 重賞レース予測エージェント。candidates_{date}.jsonを読み込み、grade_race_predictor.pyのロジックでDBから全馬データを復元して予測JSONを生成する。
---

# 予測エージェント (predictor)

## 役割
- `candidates_{date}.json` から対象レースを特定する
- `race_results` テーブルから当該レースの全馬データを復元する
- CourseMASTERv73エンジンで◎/○/▲・エッジ値・荒れ指数を算出する
- 結果を `predictions_{date}.json` として保存する

## 実行コマンド
```
python scripts/agent_predictor.py --date YYYY-MM-DD
```

## 入力
- `candidates_{date}.json` — 購入候補リスト（venue・race_no・horse_no・condition_type・odds）
- `course_master.db` — race_results / blood_category / sire_profile などの統計テーブル
- `course_master_v70_engine.pkl` — 学習済みモデル

## 出力: predictions_{date}.json
```json
{
  "date": "2026-04-19",
  "venue": "福島",
  "races": [
    {
      "race_no": 8,
      "horse_count": 12,
      "honmei": {"horse_name": "ジェシーテソーロ", "score": 72.1, "edge": 0.12},
      "chaos_index": 65.4,
      "top5": [...]
    }
  ],
  "generated_at": "2026-04-19T09:00:00"
}
```

## 注意事項
- race_results から復元できない馬は予測からスキップし警告を出す
- pkl が存在しない場合はエラーで終了する
- エンジンのBASE_DIRはプロジェクトルートを基準にする
