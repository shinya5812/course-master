# PROGRESS.md — COURSE MASTER 作業ログ

> 旧ログ（〜2026-05-24）は `PROGRESS_archive.md` を参照

---

## 2026-06-10（result_checker.py 自動サイト更新フロー完成）

### 完了タスク

1. **`result_checker.py` 修正（修正1-A/1-B/1-C）**
   - `find_prediction_file()` 追加: race_name + race_date から `predictions_*.json` を自動特定（±2日範囲で検索）
   - `update_honmei_actual_result()` 追加: `--honmei-results` で渡したJSONを `actual_result` として書き込み。`result[]` 配列（1着馬）も生成するので `/results` ページの `winner` 表示と互換
   - `run_make_latest_and_push()` 追加: `make_latest.py` を subprocess 実行 → `git add/commit/push` → Vercel 自動デプロイ
   - `main()` に `--honmei-results` 引数を追加（条件戦照合と同時指定可）
   - 候補なし早期 return でも `--honmei-results` があれば更新・push を実行

2. **`run_saturday.ps1` / `run_sunday.ps1` コメント追記**
   - push のコメントを「予測のみ ※照合後は result_checker.py が push」と明示（コードは変更なし）

### 使い方（重賞 actual_result 更新）

```
python result_checker.py --results '...' --honmei-results '[{"race_name":"安田記念 G1","honmei_finish":9,"winner_name":"シックスペンス","winner_no":4,"winner_popularity":8,"winner_odds":21.6,"verdict_result":"見送り正解（◎9着大敗）","edge_accuracy_note":"..."}]'
```

条件戦候補がない日でも重賞 actual_result のみ更新可能:
```
python result_checker.py --honmei-results '[{...}]'
```
（candidates_*.json が必要なため `--save` で空リスト保存済みが前提）

### 自動更新フロー（完成形）
```
result_checker.py（--honmei-results）
  → predictions_YYYYMMDD_*.json の actual_result を更新
  → make_latest.py → latest_data.json 更新
  → git push → Vercel 自動デプロイ → サイトに反映
```

### 次のアクション
- [ ] **6/13（土）**: 週次フロー実行・result_checker.py + --honmei-results で Vercel 更新を実動確認
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）

---

## 2026-06-10（サイト全リンク設定・暫定ページ作成）

### 完了タスク

1. **全13件リンク設定（`#` → 実URL）**
   - `lib/data.ts` ナビ: 今週の予測→`/weekly`・荒れ指数→`/analysis#adi`・的中実績→`/results`・プラン→`/plan`
   - `components/hero.tsx`: 今週の予測を見る→`/weekly`・的中実績を見る→`/results`・レース結果一覧へ→`/results`
   - `components/weekly-races.tsx`: すべてのレースを見る→`/weekly`
   - `components/ranking-table.tsx`: すべてのランキングを見る→`/weekly`
   - `components/performance-section.tsx`: 詳細を表示→`/results`
   - `components/site-footer.tsx`: 利用規約→`/legal/terms`・プライバシーポリシー→`/legal/privacy`・特定商取引法→`/legal/tokusho`・お問い合わせ→`mailto:shinya.wa5812@gmail.com`

2. **`app/analysis/page.tsx` ADIセクションに `id="adi"` 追加**（`/analysis#adi` アンカー対応）

3. **暫定ページ新規作成（6ページ）**
   - `app/weekly/page.tsx`・`app/results/page.tsx`・`app/plan/page.tsx`
   - `app/legal/terms/page.tsx`・`app/legal/privacy/page.tsx`・`app/legal/tokusho/page.tsx`
   - デザイン統一: ダーク×ゴールド・「準備中」・トップに戻るボタン

4. **ビルド確認**: `next build` 成功・全10ページ静的生成確認

### 次のアクション
- [ ] **6/13（土）**: 週次フロー実行・Vercel自動デプロイ確認
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）

---

## 2026-06-09（分析ページ バックテスト実績セクション修正）

### 完了タスク

1. **バックテスト対象期間の調査**
   - 1,544R バックテスト = 2015〜2026年（全期間・データリーク込み）と確認
   - 時系列分離検証（アプローチC）= 2022〜2026年 588R・真ROI 133.1%
   - stats_cutoff は2021/2022/2023/2024年末の4段階

2. **app/analysis/page.tsx バックテスト実績セクション修正**
   - 誤記（「2015〜2023年の時系列分離検証」）を削除
   - 2カード構成に再設計:
     - 全期間バックテスト（参考値）: 2015〜2026年 1,544R / 35.3% / ROI 227%・「※参考」バッジ付き
     - 時系列分離検証（正式評価値）: 2022〜2026年 588R / 28.1% / ROI 133.1%・「✓ 正式評価値」バッジ・金枠強調
   - ビルド成功確認（/analysis 静的ページ生成）

### 次のアクション
- [ ] **6/13（土）**: 週次フロー実行・自動push→Vercel自動デプロイ確認
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）

---

## 2026-06-09（Next.js サイト 修正3点 + 分析ページ新規作成）

### 完了タスク

1. **お知らせセクション ハードコード削除**
   - `components/features-news.tsx`: `news` インポートを削除し、お知らせ欄を「準備中」プレースホルダーに変更

2. **ナビゲーションリンク修正**
   - `lib/data.ts`: `nav` 配列に `href` フィールドを追加（「分析メソッド」→ `/analysis`）
   - `components/site-header.tsx`: `href="#"` 固定から `item.href ?? "#"` に変更

3. **分析メソッドページ新規作成**
   - `app/analysis/page.tsx` を新規作成（6セクション構成）
   - Section 1: システム概要（v7.3・552,365件・2015〜2026）
   - Section 2: 7軸スコアリング表＋4チーム合議制（I/O/U/S）
   - Section 3: エッジ値の定義・計算式・5段階判定表
   - Section 4: 荒れ指数（ADI）の4ゾーン戦略（ADIバー付き）
   - Section 5: バックテスト実績（1,544R・35.3%・227%・75%）
   - Section 6: 免責事項

4. **ビルド確認**: `next build` 成功・`/analysis` 静的ページ生成確認

### 変更ファイル
- `lib/data.ts`（nav href追加）
- `components/features-news.tsx`（news→準備中プレースホルダー）
- `components/site-header.tsx`（item.href 使用）
- `app/analysis/page.tsx`（新規作成）

### 次のアクション
- [ ] **6/13（土）・6/14（日）**: 次週重賞確認・週次フロー実行（自動push→Vercel自動デプロイ確認）
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）

---

## 2026-06-07（安田記念G1 当日フロー完了・日付フィルター実装）

### 完了タスク（セッション後半: 日付フィルター修正）

1. **grade_race_predictor.py 調査**
   - レース取得ロジック: 自身ではJRAにアクセスしない。Playwright MCP経由でClaude が取得したJSONを `--race`/`--race-file` で受け取る仕組み
   - **日付フィルター: 修正前は grade_race_predictor.py にも run_saturday/sunday.ps1 にも一切なし**

2. **grade_race_predictor.py 修正**（`main()` 関数）
   - `--today` フラグ追加: 実行日を `target_date` に自動設定（`date.today()`）
   - `--date YYYY-MM-DD` フラグ追加: 対象日を明示指定
   - `_check_date()` 関数追加: `race.get('race_date')` と `target_date` を比較し、不一致なら `対象外（日付不一致）: レース名 race_date=XXX 実行日=YYY` を出力してスキップ
   - JSONフォーマット説明・ヘルプ例に `race_date` フィールドを追記

3. **run_saturday.ps1 / run_sunday.ps1 修正**
   - `$todayISO = Get-Date -Format "yyyy-MM-dd"` を取得
   - Claudeへのプロンプト先頭に「`--today` フラグを付けること・`race_date` を含めること」の指示を自動付加

4. **prompt_saturday.txt / prompt_sunday.txt 修正**
   - 「日付フィルタールール（厳守）」セクションを追記
   - 土曜は土曜、日曜は日曜のレースのみを対象にする旨を明示

### 変更ファイル
- `grade_race_predictor.py`（main関数: `--today` / `--date` / `_check_date()` 追加）
- `run_saturday.ps1`（プロンプトへ実行日＋フラグ指示を自動付加）
- `run_sunday.ps1`（同上）
- `prompt_saturday.txt`（日付フィルタールール追記）
- `prompt_sunday.txt`（日付フィルタールール追記）

### 次のアクション
- [ ] **6/7 15:40**: 安田記念G1 レース後 → `result_checker.py` で結果照合
- [ ] TARGET JV CSV更新（2026-04-20〜分）

---

## 2026-06-07（安田記念G1 当日フロー完了）

### 完了タスク

1. **Step1: 馬場状況取得**（JRA公式・Playwright MCP）

   | 競馬場 | 天候 | 芝 | ダート | クッション値 |
   |--------|------|----|--------|------------|
   | 東京 | 曇 | 良 | 良 | 9.9（標準） |
   | 阪神 | 小雨 | 良 | 良 | 9.9（標準） |

   - 週間降雨: 6/3=139.5mm（4日前の大雨）、6/4〜6/7=0.0mm
   - 今日の開催: 東京・阪神のみ

2. **Step2: 条件A〜D フィルター**
   - 東京・阪神のみ開催 → 条件A〜D（中京・福島・新潟）**全て非発動**

3. **Step3: 安田記念G1 当日予測**（grade_race_predictor.py実行・当日オッズ使用）
   - 荒れ指数: **56.9**「波乱の可能性あり（50〜70帯）」
   - ◎馬番17 **トロヴァトーレ**（2人気・4.7倍・エッジ**-0.021**）→ 🔴 見送り
   - ○ パンジャタワー（4人気・9.0倍・エッジ+0.024）
   - ○ レーベンスティール（3人気・8.7倍・エッジ+0.015）
   - ○ ワールズエンド（7人気・20.0倍・エッジ+0.052）
   - ▲ シックスペンス（8人気・24.7倍・エッジ+0.056）
   - ▲ ルクソールカフェ（14人気・71.4倍・エッジ+0.059）

4. **Step4: 判定チェック**

   | ルール | 判定 | 理由 |
   |--------|------|------|
   | 穴馬戦略 | **非該当** | ◎トロヴァトーレが2番人気（4番人気以上条件外） |
   | エッジ閾値 | **未達** | エッジ-0.021（市場過大評価・◎ガイアフォースが1番人気に偏重） |
   | 堅め決着ルール | **参考値** | 荒れ指数56.9（50〜60帯）×良馬場。週間最大139.5mm（6/3）は4日前で当日0mm |
   | **総合判断** | **🔴 見送り** | ◎エッジマイナス・穴馬戦略非該当 |

5. **Step5: candidates保存**
   - `candidates_20260607.json` 空リスト保存
   - `predictions_20260607_yasuda.json` 保存

### 前日比較（重要）

| 項目 | 前日（6/6）事前予測 | 当日（6/7）予測 |
|------|-----------------|--------------|
| ◎ | パンジャタワー（4人気・9.5倍・+0.056） | トロヴァトーレ（2人気・4.7倍・-0.021） |
| 穴馬戦略 | 該当（◎4人気） | **非該当**（◎2人気） |
| 判定 | 🟡 様子見 | 🔴 見送り |
| 変化原因 | — | トロヴァトーレが5.0→4.7倍に短縮、エンジンスコア首位が入れ替わり |

### 結果照合（レース後）

**安田記念 G1（東京芝1600m 良 17頭）**

| 着順 | 馬番 | 馬名 | 人気 | 単勝オッズ | 印 | エッジ |
|------|------|------|------|-----------|-----|--------|
| **1着** | 4 | **シックスペンス** | 8人気 | **21.6倍** | ▲ | +0.056 |
| **2着** | 11 | **ワールズエンド** | 7人気 | 15.1倍 | ○ | +0.052 |
| **2着** | 14 | ガイアフォース | 1人気 | 2.9倍 | ▲ | -0.233 |
| 4着 | 13 | セイウンハーデス | 6人気 | 11.0倍 | ▲ | -0.017 |
| 5着 | 16 | パンジャタワー | 4人気 | 8.3倍 | ○ | +0.024 |
| 7着 | 1 | レーベンスティール | 3人気 | 7.9倍 | ○ | +0.015 |
| **9着** | **17** | **◎トロヴァトーレ** | **2人気** | **4.9倍** | ◎ | **-0.021** |

**収支: 0円（購入なし・見送り正解）**

**エンジン評価**:
- ◎トロヴァトーレ（エッジ-0.021）→ 9着大敗。**見送り判断は完全に正解**
- ▲シックスペンス（エッジ+0.056）→ **1着**。エッジ上位が的中
- ○ワールズエンド（エッジ+0.052）→ **2着（同着）**
- エッジ閾値（+0.06）には届かなかったが、エッジ高い馬が上位に来る傾向は確認

### 次のアクション
- [x] ~~6/7 15:40: 安田記念G1 result_checker.py で結果照合~~ → 完了
- [ ] TARGET JV CSV更新（2026-04-20〜分）
- [ ] 2200m超サンプル累計: 5R（目標30R）

---

## 2026-06-06（安田記念G1 事前予測・週次フロー）

### 完了タスク

1. **馬場状況取得**（JRA公式・Playwright MCP）
   - 東京: 曇・芝良・ダート稍重・クッション値9.9
   - 阪神: 晴・芝良・ダート良・クッション値9.9
   - 週間降雨: 6/3=139.5mm（大雨）、6/4〜6/6=0.0mm

2. **条件A〜D フィルター**
   - 本日開催: 東京・阪神のみ → 条件A〜D（中京・福島・新潟）全て**非発動**

3. **安田記念G1 事前予測**（出馬表取得・blood_mapで血統補完・grade_race_predictor.py実行）
   - ◎馬番16 パンジャタワー（4人気・9.5倍・エッジ+0.056）→ 🟡 様子見
   - 荒れ指数: 59.8「波乱の可能性あり」
   - 穴馬戦略: 該当（◎4番人気×1600m）
   - エッジ基準未達（+0.056 < +0.06）→ **見送り推奨**

4. **candidates_20260606.json** 空リスト保存
5. **predictions_20260606_yasuda.json** 保存
6. `grade_race_predictor.py` に `--race-file` オプション追加（PowerShell対応）

### 次のアクション

- [ ] **6/7（日）**: 安田記念G1 当日オッズ最終確認 → candidates_20260607.json保存 → 結果照合
- [ ] TARGET JV CSV更新（2026-04-20〜分）

---


## 2026-06-08（週次軽量メンテ）

### 完了タスク
- PROGRESS.mdの旧エントリー（2026-05-31〜2026-06-03 詳細ログ）を `PROGRESS_archive.md` に移動（461行 → 147行）
- 一時ファイル確認（*_log.txt・test_*.py）: 該当なし・削除不要
- CLAUDE.mdに本日の作業追記

### 結果・数値
- PROGRESS.md: 461行 → 147行
- PROGRESS_archive.md: 1529行 → 1844行

### 次のアクション
- [ ] **6/13（土）・6/14（日）**: 次週重賞確認・週次フロー実行
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）
- [ ] 補正案Z（G2穴馬戦略優先）検証

---

## 2026-06-08（Vercelトップページ・自動push実装）

### 完了タスク
1. **GitHubリポジトリ初回push**
   - .gitignore整備（*.db/*.pkl/.playwright-mcp/logs/cache/output/*.html/candidates_*.json/predictions_*.json除外）
   - orphan branch（clean-main）でクリーン履歴を作成しpush
   - data/をgit管理から除外
   - ブランチをclean-main→mainに整理
   - リモート: https://github.com/shinya5812/course-master.git

2. **Vercel用 index.html 作成**
   - デザイン: ダーク背景(#1a1a2e)×ゴールド(#c9a84c)
   - ファーストビュー: output/latest_data.jsonをfetchして◎馬名・エッジ値・判定を動的表示
   - JSONが存在しない場合は「次回予測準備中」と表示
   - スクロール後: バックテスト実績（35.3%的中率・回収率227%・黒字年75%）
   - フッター: 毎週土日9:30自動更新・免責

3. **make_latest.py 新規作成**
   - predictions_*.json（最新ファイル）から◎馬名・エッジ値・荒れ指数等を抽出
   - output/latest_data.json を生成（index.htmlがfetchして表示）

4. **run_saturday.ps1 / run_sunday.ps1 更新**
   - 成功時に output/latest.html へHTMLコピー
   - make_latest.py を実行してlatest_data.json生成
   - git add + commit + push origin main を自動実行

5. **.gitignore 更新**
   - !output/latest.html / !output/latest_data.json を追加（除外対象から外す）

### 結果・数値
- GitHubリポジトリ: https://github.com/shinya5812/course-master.git
- git commit: 2927e24 feat: トップページ・自動push実装
- 現在のoutput/latest_data.json: 安田記念G1 ◎トロヴァトーレ edge=-0.021 🔴見送り（6/7分）

### 次のアクション
- [ ] Vercel(https://course-master.vercel.app)でindex.htmlが表示されることを確認
- [ ] **6/13（土）・6/14（日）**: 週次フロー実行時にrun_saturday.ps1の自動pushを実際に確認
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）

---

## 2026-06-08（Vercel公開確認・CLAUDE.md更新）

### 完了タスク
- Vercel公開URL確認: **https://course-master-fawn.vercel.app**
- CLAUDE.md: GitHub/Vercel連携情報・自動更新フローを追記
- index.html表示確認済み

### 結果・数値
- Vercel URL: https://course-master-fawn.vercel.app
- GitHub: https://github.com/shinya5812/course-master.git
- mainブランチpush → Vercel自動デプロイ

### 次のアクション
- [ ] **6/13（土）**: 週次フロー実行時に自動push→Vercel自動デプロイを実動確認
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）

---

## 2026-06-09（全セクション実データ連携 A-1完了）

### 完了タスク

1. **make_latest.py 拡張フォーマット対応**
   - 旧→新フォーマット両対応（`normalize()` で統一スキーマ化）
   - `races[]`: 直近14日の重賞予測一覧（重複排除・actual_result優先）
   - `stats{}`: actual_result 記録済みR から累計◎的中率・複勝率を集計
   - `edge_ranking[]`: 正エッジ馬TOP5（est_win_prob/mkt_win_prob付き）
   - 後方互換フィールド（Hero用12フィールド）を保持

2. **app/page.tsx 型拡張**
   - `LatestData` 型に `races?/stats?/edge_ranking?` を追加
   - `RaceEntry / StatsData / EdgeRankEntry / HonmeiHorse / ActualResult` 型を新規定義
   - 各コンポーネントに実データを渡すよう修正

3. **WeeklyRaces 実データ対応**
   - `races: RaceEntry[]` props に切り替え
   - グレードバッジ: G1=赤 / G2=黄 / G3=青
   - 荒れ指数プログレスバー（0-100・色分け 緑/黄/オレンジ/赤）
   - ◎馬名を中央大表示・エッジ値 +0.XXX 形式
   - 判定バッジ: 強推奨=緑グロー / 推奨=緑 / 様子見=黄 / 見送り=赤
   - 穴馬★バッジ（anaba_flag=true の場合）
   - actual_result 表示（◎X着 的中/複勝圏/外れ＋1着馬名）

4. **PerformanceSection 実データ対応**
   - `stats: StatsData | null` props に切り替え
   - 統計グリッド: ◎的中率 / 複勝率 / 検証R数 / 公開開始
   - 10R未満: 「※公開後X週間・サンプル蓄積中」バッジ＋蓄積中メッセージ
   - ハードコード値（27.1%・248R・148.8%等）全廃

5. **RankingTable 実データ対応**
   - `ranking: EdgeRankEntry[]` props に切り替え
   - エッジ色分け: >=0.06=緑 / >=0=黄 / <0=赤
   - 推定勝率・市場確率を併記
   - ハードコード値（サンプルホース等）全廃

### 結果・数値
- ビルド: ✅ 成功（Next.js 16.2.6 Turbopack）
- ブラウザ確認（localhost:3001）:
  - WeeklyRaces: 安田記念G1（ADIバー56.9・🔴見送り・actual_result: ◎9着外れ）表示確認
  - PerformanceSection: 0.0% / 1R / 04/19 / ※公開後7週間・サンプル蓄積中 表示確認
  - RankingTable: ルクソールカフェ+5.9% / シックスペンス+5.6% / ワールズエンド+5.2% 等表示確認
- git commit: `a81e3c8` feat: A-1完了・全セクション実データ連携
- GitHub push: 成功

### 次のアクション
- [ ] **6/13（土）**: 週次フロー実行 → make_latest.py自動実行 → races[]に今週レースが反映されることを確認
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）
- [ ] 2200m超サンプル累計: 5R（目標30R）
- [ ] app/page.tsx の RadarSection も実データ連携（次フェーズ）

---

## 2026-06-08（v0.app Next.jsデザイン統合）

### 完了タスク
1. **v0.app生成 Next.jsプロジェクトをリポジトリに統合**
   - `web_data/coursemaster-top-page/` のZIPから展開済みファイルを確認
   - `app/` `components/` `lib/` `public/` `next.config.mjs` `tsconfig.json` `postcss.config.mjs` をリポジトリルートにコピー
   - CLAUDE.md等のCOURSE MASTERファイルは保持確認済み

2. **package.json をNext.js構成に更新**
   - Next.js 16.2.6 / React 19 / Tailwind v4 / Recharts / Shadcn等を追加
   - 既存の `docx` 依存も保持

3. **`output/latest_data.json` 連携実装**
   - `app/page.tsx`: サーバーサイドで `fs.readFileSync` により読み込み
   - `components/hero.tsx`: `latestData` propsを受け取り、ヒーローカードにレース名・馬名・人気・オッズ・エッジ・判定を動的表示
   - データなし時は「データ準備中」フォールバック表示

4. **`.gitignore` 更新**: `.next/` / `.env*.local` を追加

5. **ローカル動作確認**（localhost:3001）
   - 安田記念G1・トロヴァトーレ・🔴見送り・単勝4.7倍・エッジ-2.1% が正常表示

6. **CLAUDE.md更新**: GitHub/Vercel連携情報にNext.js構成情報・ディレクトリ説明を追記

7. **git push完了**: コミット `5e9aed1`

### 結果・数値
- npm install: 433パッケージ追加
- 変更ファイル: 33ファイル（7,727行追加）
- コンソールエラー: favicon.ico 404（軽微）・Rechartsサイズ警告のみ
- Vercel自動デプロイ: push完了（VercelでFramework=Next.jsを確認推奨）

### 次のアクション
- [ ] **Vercelダッシュボード確認**: Framework Preset が「Next.js」になっているか確認（「Static」のままだとビルド失敗）
- [ ] **6/13（土）**: 週次フロー実行→自動push→Vercel自動デプロイを実動確認
- [ ] `lib/data.ts` のサンプルデータを実績値に更新（的中率・回収率等）
- [ ] TARGET JV CSV更新（2026-04-20〜分・最優先継続課題）

---
