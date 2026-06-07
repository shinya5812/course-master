// generate_spec.js — COURSE MASTER v7.3 仕様書 Word出力
"use strict";
const path = require("path");
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, WidthType, ShadingType,
  BorderStyle, TableBorders, Header, Footer,
  PageSize, PageOrientation,
} = require("docx");

const OUTPUT_DIR = path.join(__dirname, "仕様書");
const OUTPUT_PATH = path.join(OUTPUT_DIR, "COURSE_MASTER_仕様書_v73.docx");

// ── ヘルパー ──────────────────────────────────────────────────────────────

function h1(text) {
  return new Paragraph({
    text,
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 400, after: 200 },
  });
}

function h2(text) {
  return new Paragraph({
    text,
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 300, after: 150 },
  });
}

function body(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: 24 })],
    spacing: { after: 100 },
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Arial", size: 24 })],
    bullet: { level },
    spacing: { after: 80 },
  });
}

// グレーヘッダー付きテーブル
// headers: string[], rows: string[][]
function makeTable(headers, rows) {
  const HEADER_SHADING = {
    type: ShadingType.CLEAR,
    fill: "BFBFBF",
    color: "auto",
  };
  const BORDERS = {
    top: { style: BorderStyle.SINGLE, size: 4, color: "888888" },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: "888888" },
    left: { style: BorderStyle.SINGLE, size: 4, color: "888888" },
    right: { style: BorderStyle.SINGLE, size: 4, color: "888888" },
    insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: "888888" },
    insideVertical: { style: BorderStyle.SINGLE, size: 4, color: "888888" },
  };

  const headerRow = new TableRow({
    tableHeader: true,
    children: headers.map(
      (h) =>
        new TableCell({
          shading: HEADER_SHADING,
          borders: BORDERS,
          children: [
            new Paragraph({
              children: [
                new TextRun({ text: h, bold: true, font: "Arial", size: 22, color: "FFFFFF" }),
              ],
              alignment: AlignmentType.CENTER,
            }),
          ],
        })
    ),
  });

  const dataRows = rows.map(
    (row) =>
      new TableRow({
        children: row.map(
          (cell) =>
            new TableCell({
              borders: BORDERS,
              children: [
                new Paragraph({
                  children: [new TextRun({ text: cell, font: "Arial", size: 22 })],
                }),
              ],
            })
        ),
      })
  );

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [headerRow, ...dataRows],
  });
}

function spacer() {
  return new Paragraph({ text: "", spacing: { after: 150 } });
}

// ── 表紙 ─────────────────────────────────────────────────────────────────

function coverPage() {
  return [
    new Paragraph({ text: "", spacing: { after: 2000 } }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: "COURSE MASTER v7.3 仕様書",
          bold: true,
          font: "Arial",
          size: 56,
        }),
      ],
      spacing: { after: 400 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: "JRA 競馬着順予測システム", font: "Arial", size: 32, color: "444444" }),
      ],
      spacing: { after: 800 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "作成日：2026-05-13", font: "Arial", size: 24 })],
      spacing: { after: 200 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "バージョン：v7.3（現行）", font: "Arial", size: 24 })],
      spacing: { after: 200 },
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "格納場所：C:\\Users\\shiny\\Dropbox\\shinya_wa\\coursemaster\\", font: "Arial", size: 20, color: "666666" })],
    }),
  ];
}

// ── 第1章 システム概要 ──────────────────────────────────────────────────

function chap1() {
  return [
    h1("1. システム概要"),
    h2("1.1 目的・背景"),
    body("JRA Grade競走（G1/G2/G3）において、馬券市場に生じる非効率（オッズが実力を過大/過小評価している状態）を12軸スコアリングで定量化し、正ROIを実現することを目的とする。"),
    body("単純な人気順ベットでは単勝回収率が約75〜79%に収束するのに対し、本システムはエッジ値（エンジン推定勝率 − 市場含意確率）を用いてベット対象を絞り込むことで、長期的なプラス収支を目指す。"),
    spacer(),
    h2("1.2 バージョン履歴"),
    makeTable(
      ["バージョン", "変更内容", "備考"],
      [
        ["v7.0", "初期実装。12軸スコアリング＋4チーム合議制。Pickle形式でモデル保存。", "現在もPKLとして利用"],
        ["v7.2", "スコア計算式の微調整（中間リリース）。正式リリース前の試験版。", "非公開"],
        ["v7.3", "Fix1: 勝率変換式の修正（place_rate補正廃止）。Fix2: キャリア走数ペナルティ追加。Fix3: MK軸オッズ帯補正（過大評価を減点のみ）。", "現行版"],
      ]
    ),
    spacer(),
    h2("1.3 現在の稼働バージョン"),
    body("現行エンジン：v7.3（course_master_v73_engine.py）"),
    body("PKL：course_master_v70_engine.pkl（v7.0形式・v7.3が後方互換で読み込む）"),
    body("Webアプリ：prediction_app.py（Flask・localhost:5000）"),
  ];
}

// ── 第2章 データ基盤 ────────────────────────────────────────────────────

function chap2() {
  return [
    h1("2. データ基盤"),
    h2("2.1 結果データ"),
    makeTable(
      ["ファイル", "対象期間", "件数"],
      [
        ["2015_2016結果.csv", "2015〜2016年", "100,068件"],
        ["2017_2018結果.csv", "2017〜2018年", "97,917件"],
        ["2019_2020結果.csv", "2019〜2020年", "95,856件"],
        ["2021_2023結果.csv", "2021〜2023年", "142,713件"],
        ["2024_2026結果.csv", "2024〜2026年", "99,548件"],
        ["2026結果.csv / 202602280331結果.csv", "2026年最新", "追加分"],
      ]
    ),
    spacer(),
    body("DB合計：race_results テーブル 549,604件（2026-05-10時点）"),
    body("エンコーディング：cp932（Shift-JIS）— TARGET JV出力CSVに合わせた設定"),
    spacer(),
    h2("2.2 血統データ"),
    body("ファイル：20260217血統.csv（51,740件・2026-05-13時点）"),
    body("エンコーディング：cp932（Shift-JIS）"),
    body("血統カテゴリ：スタミナ系 / マイラー系 / 速力系（blood_category フィールドで管理）"),
    spacer(),
    h2("2.3 DBファイル"),
    body("ファイル名：course_master.db（SQLite・約23MB）"),
    makeTable(
      ["テーブル名", "件数", "内容"],
      [
        ["blood_map", "50,989件", "血統マッピング（馬名→父馬名→blood_category）"],
        ["bms_profile", "730件", "BMS（母の父）プロファイル"],
        ["field_bias", "66件", "コース・馬場バイアス"],
        ["horse_career", "17,431件", "馬別キャリア統計"],
        ["horse_condition", "15,611件", "馬体状態データ"],
        ["horse_speed", "15,964件", "馬別スピード指数"],
        ["jockey_grade", "130件", "騎手グレード評価"],
        ["jockey_specialty", "944件", "騎手コース得意傾向"],
        ["jockey_stats", "252件", "騎手統計（2026-05-13更新）"],
        ["jockey_trainer_combo", "10,865件", "騎手×調教師組み合わせ統計"],
        ["jockey_trend", "127件", "騎手トレンド"],
        ["kinryo_band", "15件", "斤量帯区分"],
        ["sire_profile", "490件", "種牡馬プロファイル（2026-05-13更新）"],
        ["speed_base", "381件", "距離別スピード基準"],
        ["style_ev_map", "280件", "脚質別期待値マップ"],
        ["trainer_grade", "187件", "調教師グレード評価"],
        ["trainer_stats", "262件", "調教師統計（2026-05-13更新）"],
      ]
    ),
    spacer(),
    h2("2.4 更新スクリプト"),
    body("db_update_0513.py：次回以降の定期更新テンプレート"),
    body("rebuild_pkl.py：統計再集計＋PKL再生成を一括実行"),
    body("更新手順：TARGET JVからCSV出力 → coursemasterフォルダへ追加 → db_update_0513.py 実行 → rebuild_pkl.py 実行"),
  ];
}

// ── 第3章 12軸スコアリング ──────────────────────────────────────────────

function chap3() {
  return [
    h1("3. 12軸スコアリング"),
    body("各馬を以下の12軸で評価し、重み付き平均で最終スコアを算出する。現行v7.3では7軸（CF/SI/JT/SPD/PD/BL/MK）を使用し、残5軸は統計として保持する。"),
    spacer(),
    makeTable(
      ["軸", "名称", "重み", "説明", "v7.3修正点"],
      [
        ["CF", "キャリア形成", "×2.0", "血統CSV全成績の勝率＋走数から算出", "走数ペナルティ追加（1〜3走：0.70、4〜5走：0.85）。未出走は20点"],
        ["SI", "スピードインデックス", "×2.0", "上がり3Fタイムのz-scoreを正規化", "変更なし"],
        ["JT", "ジョッキー", "×2.0", "騎手別通算勝率（jockey_stats）", "固定加算+30廃止。win_rate×100のみ"],
        ["SPD", "スピード能力", "×2.0", "走破時計のコース内z-score", "変更なし"],
        ["PD", "ペースデザイン", "×1.0", "通過順（1〜4F）の位置取り評価", "欠損時は50点フォールバック"],
        ["BL", "ベース力", "×0.3", "人気順ベース評価", "変更なし"],
        ["MK", "マーケット", "×0.3", "人気順＋オッズ帯補正", "3倍超への加点（×1.05）廃止。過大評価帯のみ減点"],
        ["BF", "血統適性", "—（除外）", "血統×コース×馬場の適性スコア", "重賞1,544Rで相関+0.020→逆効果。2026-04-03除外"],
        ["HP", "ハンデ適応", "—（除外）", "斤量×年齢の適応評価", "重賞1,544Rで相関-0.030→ほぼ無効。2026-04-03除外"],
        ["FR", "前走状態", "—（保留）", "前走馬体重データベース", "前走馬体重データ非対応のため常に50点"],
        ["CL", "クラス適応", "—（保留）", "同一レース内クラスコード", "同一レース内全馬が同値→鑑別不能"],
        ["TR", "コース適性", "—（保留）", "同一レース内コース条件", "同一レース内全馬が同値→鑑別不能"],
      ]
    ),
    spacer(),
    h2("3.1 MK軸オッズ帯補正（v7.3 Fix3）"),
    body("バックテスト（2024〜2026年 Grade 277R）の結果に基づき、過大評価帯のみ減点する設計。"),
    makeTable(
      ["オッズ帯", "MK補正係数", "理由"],
      [
        ["〜2倍", "×0.85", "実勝率が市場期待を−0.038下回る"],
        ["2〜3倍", "×0.90", "実勝率が市場期待を−0.043下回る"],
        ["3倍超", "×1.00（補正なし）", "過去加点（×1.05）は1/2人気誤誘導が発生したため撤廃"],
      ]
    ),
    spacer(),
    h2("3.2 キャリア走数ペナルティ（v7.3 Fix2）"),
    makeTable(
      ["走数", "CF係数", "理由"],
      [
        ["1〜3走目", "0.70", "実データ比で32%低い勝率"],
        ["4〜5走目", "0.85", "実データ比で15%低い勝率"],
        ["6走以上", "1.00（ペナルティなし）", "安定した実力が発揮される"],
        ["未出走・未知馬", "cf_score = 20", "旧30点から引き下げ"],
      ]
    ),
  ];
}

// ── 第4章 4チーム合議制 ─────────────────────────────────────────────────

function chap4() {
  return [
    h1("4. 4チーム合議制"),
    h2("4.1 チーム構成と重み"),
    body("4チームがそれぞれ独立してスコアリングを行い、重み付き平均で最終予測を出す。"),
    makeTable(
      ["チーム", "特性", "重み", "重視軸"],
      [
        ["I（Instinct）", "直感型・スピード重視", "3", "SI・SPD中心"],
        ["O（Order）", "秩序型・実績重視", "1", "CF・JT中心"],
        ["U（Unity）", "協調型・バランス重視", "1", "全軸均等"],
        ["S（Strike）", "一撃型・人気逆張り", "1", "MK・PD中心"],
      ]
    ),
    spacer(),
    h2("4.2 softmax勝率変換"),
    body("各チームのスコアをsoftmax関数（温度パラメータ T=5.0）で勝率確率に変換する。"),
    body("計算式：P(win_i) = exp(score_i / T) / Σ exp(score_j / T)"),
    body("T=5.0は「極端な差をつけすぎない」バランスに調整済み（T=1.0は過激・T=10.0は均等すぎる）。"),
    spacer(),
    h2("4.3 P(win) <= P(place)/3 原則"),
    body("生の勝率推定は過大になりがちなため、複勝率との整合性を担保する補正を適用する。"),
    body("条件：P(win) > P(place)/3 の場合、P(win) を P(place)/3 に引き下げる。"),
    body("この原則により◎の単勝過信を防ぎ、エッジ値計算の信頼性を高める。"),
  ];
}

// ── 第5章 エッジ値計算とベッティングルール ──────────────────────────────

function chap5() {
  return [
    h1("5. エッジ値計算とベッティングルール"),
    h2("5.1 エッジ値の定義"),
    body("エッジ値 = エンジン推定勝率 − 市場含意確率"),
    body("市場含意確率 = 1 / 単勝オッズ × 0.80（JRAの控除率25%を20%と近似）"),
    body("エッジ値がプラスであれば「市場が過小評価している馬」、マイナスであれば「過大評価」を意味する。"),
    spacer(),
    h2("5.2 ベッティング閾値"),
    makeTable(
      ["条件", "閾値", "根拠・備考"],
      [
        ["通常重賞（G1/G2/G3）", "エッジ +0.06以上", "バックテスト検証回収率247.8%（2024〜2026年）"],
        ["阪神 稍重", "エッジ +0.07以上", "阪神稍重での+0.05は回収率62.5%（赤字）。+0.07で100%に回復"],
        ["距離2200m以上", "全閾値で見送り（検証記録のみ）", "サンプル不足（2026-05-13時点 2R）。30R超で再評価"],
      ]
    ),
    spacer(),
    h2("5.3 判定ラベル"),
    makeTable(
      ["ラベル", "条件", "推奨アクション"],
      [
        ["★★ 強推奨", "エッジ +0.10以上", "単勝200円"],
        ["★ 推奨", "エッジ +0.06〜+0.10", "単勝100円"],
        ["△ 様子見", "エッジ 0〜+0.06", "見送り"],
        ["✗ 見送り", "エッジ マイナス", "見送り"],
      ]
    ),
    spacer(),
    h2("5.4 穴馬戦略"),
    body("◎が4番人気以上 かつ 距離2200m未満 → 単勝購入"),
    makeTable(
      ["指標", "数値"],
      [
        ["バックテスト対象", "重賞G1/G2/G3 2015〜2026年 150R"],
        ["単勝回収率", "227.7%"],
        ["安定性", "9/12年（75%）黒字"],
        ["G1回収率", "158.8%"],
        ["G2回収率", "310.7%（最優先グレード）"],
        ["G3回収率", "227.3%"],
        ["主戦距離", "1600〜2000m（258.8%）"],
        ["年間ベット数", "約12.5R"],
      ]
    ),
    spacer(),
    h2("5.5 条件B（福島ダ1700m）"),
    body("福島ダート1700m × スタミナ系種牡馬 × 10番人気以上 × 馬場「良」または「重」のみ"),
    makeTable(
      ["指標", "数値"],
      [
        ["サンプル（フィルター後）", "1,407R（良+重のみ）"],
        ["回収率", "147.8%"],
        ["安定性", "7/9年（78%）← 4条件中最高"],
        ["1着馬平均オッズ", "77.8倍"],
        ["見送り馬場", "稍重・不良"],
      ]
    ),
    spacer(),
    h2("5.6 条件C（新潟芝2000m）"),
    body("新潟芝2000m × スタミナ系種牡馬 × 10番人気以上 × 重馬場・4月・7月は見送り"),
    makeTable(
      ["指標", "数値"],
      [
        ["サンプル（フィルター後）", "663R（重・4月・7月除外）"],
        ["回収率", "129.9%"],
        ["安定性", "6/9年（67%）"],
        ["1着馬平均オッズ", "65.4倍"],
        ["見送り条件", "重馬場・4月開催・7月開催"],
      ]
    ),
  ];
}

// ── 第6章 バックテスト済みルール一覧 ────────────────────────────────────

function chap6() {
  return [
    h1("6. バックテスト済みルール一覧"),
    h2("6.1 採用済みルール"),
    makeTable(
      ["ルール", "採用日", "検証データ", "結果サマリー"],
      [
        ["エッジ閾値 +0.06（通常）", "2026-04-17", "重賞1,561R", "回収率247.8%・黒字年率67%（6/9年）"],
        ["エッジ閾値 +0.07（阪神稍重）", "2026-04-17", "阪神稍重 20R", "回収率100%（+0.05は62.5%から改善）"],
        ["穴馬戦略（◎4番人気以上×2200m未満）", "2026-04-15", "150R（2015〜2026年）", "回収率227.7%・安定性75%"],
        ["条件B（福島ダ1700m×スタミナ×10番人気以上×良重）", "2026-03-19", "1,407R", "回収率147.8%・安定性78%"],
        ["条件C（新潟芝2000m×スタミナ×10番人気以上）", "2026-03-19", "663R", "回収率129.9%・安定性67%"],
        ["7軸化（BF/HP除外）", "2026-04-03", "重賞1,544R", "的中率32.2%→35.3%（+3.1%）"],
        ["MK軸 過大評価帯のみ減点", "2026-04-15", "Grade 277R", "3倍超加点廃止・薄人気フラグ廃止"],
      ]
    ),
    spacer(),
    h2("6.2 却下済みルール"),
    makeTable(
      ["ルール", "却下日", "検証データ", "却下理由"],
      [
        ["同一コース経験フィルター", "2026-04-16", "重賞G1初出走", "G1初出走の成績改善なし（確認バイアス）"],
        ["直近3走トレンドフラグ（G3少キャリア）", "2026-04-16", "G3 3走未満", "改善効果なし・不採用"],
        ["堅め決着ルール（前日悪→当日良）", "2026-04-17", "208件", "前日悪→当日良の1番人気回収率56.1%（通常79.6%より−23.5%）"],
        ["Fix3 MK軸加点（3〜8倍×1.05）", "2026-04-15", "重賞277R", "2人気→1人気への誤誘導が発生"],
        ["◎未達×高エッジ馬連ルール", "2026-05-11", "重賞 3年", "ROI129.3%・黒字1/3年（2024年0/25全外れ）"],
        ["5月良馬場加点（条件C）", "2026-05-11", "663R月別", "高倍率2回依存・安定性4/8年50%で採用基準未達"],
        ["○以下エッジ馬連ルール", "2026-04-25", "重賞 3年", "ベースライン275.1%に対し馬連129.3%（下回る）"],
      ]
    ),
  ];
}

// ── 第7章 ADI/FRI指標 ──────────────────────────────────────────────────

function chap7() {
  return [
    h1("7. ADI/FRI指標（荒れ指数・フィールド乱高下指数）"),
    h2("7.1 ADI（荒れ指数）"),
    body("ADI（Aree Difficulty Index）：レースの波乱度を0〜100で表す指標。"),
    body("閾値：18（低波乱境界）/ 30（中波乱境界）—修正後。"),
    makeTable(
      ["ADI範囲", "パターン", "戦略"],
      [
        ["〜50", "A（安定）", "単勝◎のみ"],
        ["50〜70", "波乱注意", "単勝◎＋馬連◎○（○はエッジ+0.03以上・最大2頭・馬連=単勝の半額）"],
        ["70〜85", "B（大波乱注意）", "単勝◎のみ（馬連見送り）"],
        ["85〜", "超高波乱", "全体見送りも選択肢（馬連なし）"],
      ]
    ),
    spacer(),
    h2("7.2 FRI（フィールド乱高下指数）"),
    body("FRI（Field Range Index）：フィールド内のオッズ分散から算出。閾値：25。"),
    body("FRI > 25 は「オッズが極端に偏っているレース」を意味し、穴馬戦略の参考指標として使用する。"),
    spacer(),
    h2("7.3 ADI 50〜70帯での馬連プラン詳細"),
    body("grade_race_predictor.py の build_umaren_plan() が自動判定して出力する。"),
    bullet("○候補：エッジ+0.03以上の○馬（最大2頭・エッジ降順で選出）"),
    bullet("金額：単勝★★→200円・単勝★→100円 / 馬連=単勝の半額（最小50円）"),
    bullet("根拠：ADI50-70帯では◎が2着止まりのケースも多く、○との組み合わせが有効"),
  ];
}

// ── 第8章 週次運用フロー ────────────────────────────────────────────────

function chap8() {
  return [
    h1("8. 週次運用フロー"),
    h2("8.1 /weeklyスキルの手順概要"),
    body("毎週土曜・日曜の朝9:00〜10:30に以下を順次実行する。"),
    makeTable(
      ["ステップ", "内容", "ツール・コマンド"],
      [
        ["①天気取得", "Yahoo天気（競馬場別）で午後の降水確率・降水量を確認", "Playwright MCP"],
        ["②馬場確認", "JRA公式3ページからクッション値・芝/ダート馬場状態を取得", "Playwright MCP"],
        ["③条件フィルター", "条件A〜Dの該当馬を馬場状態に基づき抽出", "手動判断"],
        ["④重賞予測", "grade_race_predictor.py を全重賞に対して実行", "python grade_race_predictor.py"],
        ["⑤候補保存", "result_checker.py --save でcandidates_YYYYMMDD.json保存", "python result_checker.py --save"],
        ["⑥結果照合", "レース後にresult_checker.pyを実行して収支確認", "python result_checker.py"],
        ["⑦コミット", "git add -A && git commit", "git"],
      ]
    ),
    spacer(),
    h2("8.2 セッション開始プロンプト（テンプレート）"),
    body("今日（YYYY-MM-DD）の週次フローを実行してください。"),
    bullet("馬場状態を取得して条件A〜Dの該当馬を確認"),
    bullet("grade_race_predictor.py を今日開催の全重賞に対して実行"),
    bullet("購入候補をresult_checker.pyで保存"),
    spacer(),
    h2("8.3 結果照合プロンプト（テンプレート）"),
    body("今日（YYYY-MM-DD）のレース結果を照合してください。"),
    bullet("result_checker.py を実行して candidates_YYYYMMDD.json を自動読み込み"),
    bullet("収支をPROGRESS.mdに記録してgit commit"),
    spacer(),
    h2("8.4 見送りルール早見表"),
    makeTable(
      ["条件", "見送り馬場・月", "購入推奨馬場"],
      [
        ["A（中京ダ1401〜1800m×マイラー系×7〜9人気）", "なし（全馬場購入可）", "全馬場"],
        ["B（福島ダ1700m×スタミナ系×10番人気以上）", "稍重・不良", "良・重"],
        ["C（新潟芝2000m×スタミナ系×10番人気以上）", "重馬場・4月・7月", "良・稍重・不（・5月〜6月・8月〜）"],
        ["D（中京芝1200/1400m×速力系×7〜9番人気）", "不良のみ", "良・稍重・重"],
      ]
    ),
  ];
}

// ── 第9章 ファイル構成 ──────────────────────────────────────────────────

function chap9() {
  return [
    h1("9. ファイル構成"),
    makeTable(
      ["ファイル名", "用途", "最終更新"],
      [
        ["course_master_v73_engine.py", "現行エンジン（CourseMASTERv73クラス）", "2026-04-15"],
        ["course_master_v70_engine.py", "旧エンジン（参照用）", "2026-03-17"],
        ["course_master_v70_engine.pkl", "学習済みモデル（Pickle・v7.3が後方互換で読み込む）", "2026-05-13"],
        ["prediction_app.py", "Flask製Webアプリ（localhost:5000）", "2026-03-17"],
        ["course_master.db", "SQLiteデータベース（約23MB・549,604件）", "2026-05-13"],
        ["grade_race_predictor.py", "重賞予測＋荒れ指数＋エッジ値判定＋購入サマリー", "2026-04-26"],
        ["result_checker.py", "購入候補保存・結果照合・P&L集計", "2026-04-20"],
        ["predict_future.py", "未来レース予測（前走データ自動補完）", "2026-03-17"],
        ["weather_checker.py", "開催場の天気予報表示・馬場悪化リスク警告", "2026-03-17"],
        ["db_update_0513.py", "定期DB更新テンプレート（2026-05-13作成）", "2026-05-13"],
        ["rebuild_pkl.py", "統計再集計＋PKL再生成一括スクリプト", "2026-05-13"],
        ["20260217血統.csv", "血統データ（51,740件・cp932）", "2026-05-13"],
        ["2024_2026結果.csv", "TARGET JV出力結果CSV（2024〜2026年）", "2026-05-10"],
        ["仕様書/COURSE_MASTER_仕様書_v73.docx", "本仕様書", "2026-05-13"],
        ["CLAUDE.md", "Claude Code向け開発・運用指示", "2026-05-13"],
        ["PROGRESS.md", "作業ログ（直近・アーカイブ別管理）", "2026-05-13"],
        ["logs/", "バックテストログ・baselineJSON保存先", "随時"],
      ]
    ),
  ];
}

// ── 第10章 今後の開発課題 ───────────────────────────────────────────────

function chap10() {
  return [
    h1("10. 今後の開発課題"),
    h2("10.1 優先度：高"),
    makeTable(
      ["課題", "内容", "期待効果"],
      [
        ["前走比較情報の組み込み", "距離変更（前走比距離差）・斤量変化（前走比kg差）・レース間隔（週数）をスコア軸として追加", "コース適性・仕上がりを定量化。特に斤量変化は馬の得手不得手に直結"],
      ]
    ),
    spacer(),
    h2("10.2 優先度：中"),
    makeTable(
      ["課題", "内容", "期待効果"],
      [
        ["騎手×コース相性の精緻化", "現行jockey_specialtyは粗い分類。距離帯×馬場×コース（右/左/直線）別の勝率マトリクスに強化", "JT軸の精度向上。特に東京・阪神の芝長距離で差が出やすい"],
      ]
    ),
    spacer(),
    h2("10.3 保留（課題として記録・実装未定）"),
    makeTable(
      ["課題", "保留理由", "再評価条件"],
      [
        ["maiden race プロファイリング", "未出走・新馬戦は過去実績がなくスコア根拠が弱い。過学習リスクおよびサンプル不足（30R未満）", "新馬戦サンプルが50R以上蓄積された時点で再評価"],
        ["2200m以上のベット対象化", "現在2Rのみ（天皇賞春・京都新聞杯）。◎的中率100%だがサンプル不足で判断不可", "累計30R以上蓄積後に回収率・的中率で判断"],
        ["Siyouni（欧州産血統）DB登録", "シンエンペラーの父Siyouniがblood_mapに未登録。blood_categoryをフォールバック扱い", "blood_map更新時に手動で「マイラー系」として登録"],
      ]
    ),
  ];
}

// ── メイン ───────────────────────────────────────────────────────────────

async function main() {
  const sections = [
    ...coverPage(),
    ...chap1(),
    ...chap2(),
    ...chap3(),
    ...chap4(),
    ...chap5(),
    ...chap6(),
    ...chap7(),
    ...chap8(),
    ...chap9(),
    ...chap10(),
  ];

  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: "Arial", size: 24 },
        },
        heading1: {
          run: { font: "Arial", size: 28, bold: true, color: "1F3864" },
          paragraph: { spacing: { before: 400, after: 200 } },
        },
        heading2: {
          run: { font: "Arial", size: 24, bold: true, color: "2E4899" },
          paragraph: { spacing: { before: 300, after: 150 } },
        },
      },
    },
    sections: [
      {
        properties: {
          page: {
            size: { width: 11906, height: 16838 }, // A4
          },
        },
        children: sections,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(OUTPUT_PATH, buffer);
  console.log("生成完了:", OUTPUT_PATH);
  console.log("ファイルサイズ:", (buffer.length / 1024).toFixed(1), "KB");
}

main().catch((err) => {
  console.error("エラー:", err.message);
  process.exit(1);
});
