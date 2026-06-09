import { SiteHeader } from "@/components/site-header"

const axes = [
  { id: "CF", name: "キャリア形成", basis: "血統CSV全成績（勝率＋走数）", weight: "×2.0" },
  { id: "SI", name: "スピードインデックス", basis: "上がり3Fタイム", weight: "×2.0" },
  { id: "JT", name: "ジョッキー", basis: "騎手別統計勝率", weight: "×2.0" },
  { id: "SPD", name: "スピード能力", basis: "走破時計のz-score", weight: "×2.0" },
  { id: "PD", name: "ペースデザイン", basis: "通過順（1〜4F）の位置取り", weight: "×1.0" },
  { id: "BL", name: "ベース力", basis: "人気順ベース評価", weight: "×0.3" },
  { id: "MK", name: "マーケット", basis: "人気順＋オッズ帯補正", weight: "×0.3" },
]

const teams = [
  { id: "I", desc: "インサイダー視点：血統・適性を重視" },
  { id: "O", desc: "アウトサイダー視点：市場乖離を重視" },
  { id: "U", desc: "アンダードッグ視点：穴馬ポテンシャルを重視" },
  { id: "S", desc: "スピード視点：タイム指数を重視" },
]

const verdicts = [
  {
    emoji: "🟢🟢",
    label: "強推奨",
    condition: "穴馬戦略（◎4番人気以上）かつエッジ +0.06以上",
    action: "単勝購入を強く推奨",
    rowCls: "border-positive/40 bg-positive/10",
    labelCls: "text-positive",
  },
  {
    emoji: "🟢",
    label: "推奨",
    condition: "エッジ +0.06以上",
    action: "購入検討",
    rowCls: "border-positive/25 bg-positive/5",
    labelCls: "text-positive",
  },
  {
    emoji: "🟡",
    label: "様子見",
    condition: "エッジ 0〜+0.06",
    action: "慎重に判断",
    rowCls: "border-warn/30 bg-warn/10",
    labelCls: "text-warn",
  },
  {
    emoji: "🟠",
    label: "保留",
    condition: "距離2200m以上（ベット保留・検証中）",
    action: "検証のみ・ベットなし",
    rowCls: "border-warn/40 bg-warn/15",
    labelCls: "text-warn",
  },
  {
    emoji: "🔴",
    label: "見送り",
    condition: "エッジ 0未満",
    action: "見送り推奨",
    rowCls: "border-danger/30 bg-danger/10",
    labelCls: "text-danger",
  },
]

const adiZones = [
  {
    range: "〜50",
    label: "安定",
    pct: 50,
    strategy: "単勝◎のみ",
    barCls: "bg-positive",
    textCls: "text-positive",
    borderCls: "border-positive/30",
    bgCls: "bg-positive/10",
  },
  {
    range: "50〜70",
    label: "波乱含み",
    pct: 70,
    strategy: "単勝◎＋馬連◎○（エッジ+0.03以上・最大2頭）",
    barCls: "bg-warn",
    textCls: "text-warn",
    borderCls: "border-warn/30",
    bgCls: "bg-warn/10",
  },
  {
    range: "70〜85",
    label: "大波乱注意",
    pct: 85,
    strategy: "単勝◎のみ（馬連は見送り）",
    barCls: "bg-danger",
    textCls: "text-danger",
    borderCls: "border-danger/30",
    bgCls: "bg-danger/10",
  },
  {
    range: "85〜",
    label: "全体見送り候補",
    pct: 100,
    strategy: "全体見送りも選択肢（馬連なし）",
    barCls: "bg-danger",
    textCls: "text-danger",
    borderCls: "border-danger/50",
    bgCls: "bg-danger/20",
  },
]

const backtestFull = [
  { label: "対象R数", value: "1,544", unit: "R", sub: "重賞G1/G2/G3" },
  { label: "◎的中率", value: "35.3", unit: "%", sub: "1番人気比 +5.8%超" },
  { label: "穴馬戦略ROI", value: "227", unit: "%", sub: "◎4番人気以上×2200m未満" },
  { label: "黒字年率", value: "75", unit: "%", sub: "9/12年（2015〜2026）" },
]

const backtestClean = [
  { label: "対象R数", value: "588", unit: "R", sub: "重賞G1/G2/G3" },
  { label: "◎的中率", value: "28.1", unit: "%", sub: "リークなし真値" },
  { label: "単勝ROI", value: "133.1", unit: "%", sub: "アプローチC完成版" },
]

export default function AnalysisPage() {
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />

      <main className="mx-auto max-w-[860px] px-5 py-12 space-y-10">
        {/* ページタイトル */}
        <div className="text-center space-y-3">
          <p className="text-xs font-mono tracking-widest text-gold uppercase">Analysis Method</p>
          <h1 className="font-serif text-3xl font-bold text-gold-gradient">分析メソッド</h1>
          <p className="text-sm text-muted-foreground leading-relaxed">
            COURSE MASTER がどのように競走馬を評価し、
            <br className="hidden sm:block" />
            市場の歪みを検出するかを解説します。
          </p>
        </div>

        {/* Section 1: システム概要 */}
        <section className="rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8">
          <h2 className="font-serif text-xl font-semibold">システム概要</h2>
          <p className="mt-2 text-[11px] font-mono text-gold">COURSE MASTER v7.3</p>
          <p className="mt-4 text-sm leading-relaxed text-foreground/80">
            COURSE MASTER は JRA 競馬の重賞レースにおいて、
            <span className="text-gold font-medium">市場オッズの歪み（エッジ）</span>を定量的に発見するための予測エンジンです。
            単純に「勝つ馬を当てる」のではなく、
            「市場が過小評価している馬に賭ける」という収支最大化の思想で設計されています。
          </p>
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "学習データ", value: "552,365", unit: "件" },
              { label: "対象期間", value: "2015〜2026", unit: "年" },
              { label: "対象テーブル", value: "20", unit: "テーブル" },
              { label: "エンジンバージョン", value: "v7.3", unit: "" },
            ].map((item) => (
              <div key={item.label} className="rounded-lg border border-gold-faint/60 bg-background/40 p-3 text-center">
                <p className="text-[10px] text-muted-foreground">{item.label}</p>
                <p className="mt-1 font-serif text-lg font-bold text-gold-gradient">
                  {item.value}
                  <span className="text-xs font-normal ml-0.5">{item.unit}</span>
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Section 2: 7軸スコアリング */}
        <section className="rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8">
          <h2 className="font-serif text-xl font-semibold">7軸スコアリング</h2>
          <p className="mt-3 text-sm leading-relaxed text-foreground/80">
            各馬を 7 つの観点でスコアリングし、重み付き平均で最終スコアを算出します。
            重み ×2.0 の実力軸が予測精度の中核を担います。
          </p>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[420px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-gold-faint text-[11px] text-muted-foreground">
                  <th className="py-2 text-left font-normal w-12">軸</th>
                  <th className="py-2 text-left font-normal">名称</th>
                  <th className="py-2 text-left font-normal">計算ベース</th>
                  <th className="py-2 text-right font-normal text-gold w-16">重み</th>
                </tr>
              </thead>
              <tbody>
                {axes.map((ax, i) => (
                  <tr
                    key={ax.id}
                    className={`border-b border-gold-faint/50 ${i < 4 ? "bg-positive/5" : ""}`}
                  >
                    <td className="py-2.5 text-left">
                      <span className="font-mono text-xs font-bold text-gold bg-gold/10 px-1.5 py-0.5 rounded">
                        {ax.id}
                      </span>
                    </td>
                    <td className="py-2.5 text-left text-foreground/90 font-medium">{ax.name}</td>
                    <td className="py-2.5 text-left text-xs text-foreground/70">{ax.basis}</td>
                    <td className={`py-2.5 text-right font-mono text-sm font-bold ${i < 4 ? "text-positive" : "text-muted-foreground"}`}>
                      {ax.weight}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            ※ 緑背景は実力軸（重み×2.0）
          </p>

          {/* 4チーム合議制 */}
          <div className="mt-6 rounded-lg border border-gold-faint/60 bg-background/40 p-4">
            <p className="text-xs font-semibold text-gold">4チーム合議制</p>
            <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
              異なる視点を持つ 4 チーム（I / O / U / S）がそれぞれ独立してスコアを算出し、
              その平均を最終スコアとします。単一視点のバイアスを排除します。
            </p>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {teams.map((t) => (
                <div key={t.id} className="rounded border border-gold-faint/40 bg-card/40 p-2">
                  <span className="font-mono text-base font-bold text-gold">{t.id}</span>
                  <p className="mt-0.5 text-[10px] text-muted-foreground leading-snug">{t.desc}</p>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[11px] text-muted-foreground">
              最終スコア → Softmax（温度 T=5.0）で勝率確率に変換
            </p>
          </div>
        </section>

        {/* Section 3: エッジ値 */}
        <section className="rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8">
          <h2 className="font-serif text-xl font-semibold">エッジ値とは</h2>
          <p className="mt-3 text-sm leading-relaxed text-foreground/80">
            エッジ値は「エンジンが推定する勝率」と「市場オッズが示す勝率」の差です。
            プラスが大きいほど、市場が過小評価している馬です。
          </p>

          <div className="mt-5 rounded-lg border border-gold/30 bg-gold/5 p-4 text-center">
            <p className="font-mono text-sm text-gold-gradient">
              エッジ = エンジン推定勝率 − 市場勝率
            </p>
            <p className="mt-2 text-xs text-muted-foreground">
              市場勝率 = 1 ÷ 単勝オッズ × 0.80（還元率補正）
            </p>
          </div>

          <div className="mt-5 space-y-2">
            <p className="text-xs font-medium text-foreground/70 mb-3">購入判定の 5 段階</p>
            {verdicts.map((v) => (
              <div
                key={v.label}
                className={`flex items-center gap-3 rounded-lg border px-4 py-2.5 ${v.rowCls}`}
              >
                <span className="text-base">{v.emoji}</span>
                <span className={`w-16 text-sm font-semibold ${v.labelCls}`}>{v.label}</span>
                <span className="flex-1 text-xs text-foreground/75">{v.condition}</span>
                <span className="hidden sm:block text-xs text-muted-foreground">→ {v.action}</span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted-foreground">
            ※ 購入の最終判断はユーザーが行います。システムは判断材料を提供します。
          </p>
        </section>

        {/* Section 4: 荒れ指数（ADI） */}
        <section id="adi" className="rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8">
          <h2 className="font-serif text-xl font-semibold">
            荒れ指数（ADI）とは
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-foreground/80">
            ADI（Areno-degree Index）はレース全体の「荒れやすさ」を 0〜100 で表す指標です。
            人気の集中度・オッズ分布・血統多様性などから算出します。
            ADI に応じて馬券戦略を切り替えることでリスクをコントロールします。
          </p>

          <div className="mt-6 space-y-3">
            {adiZones.map((zone) => (
              <div
                key={zone.range}
                className={`rounded-lg border ${zone.borderCls} ${zone.bgCls} p-4`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className={`font-mono text-sm font-bold shrink-0 ${zone.textCls}`}>
                      {zone.range}
                    </span>
                    <span className={`rounded px-2 py-0.5 text-[10px] font-medium border ${zone.borderCls} ${zone.bgCls} ${zone.textCls}`}>
                      {zone.label}
                    </span>
                  </div>
                  <div className="w-24 shrink-0">
                    <div className="h-1.5 rounded-full bg-muted-foreground/20">
                      <div
                        className={`h-1.5 rounded-full ${zone.barCls}`}
                        style={{ width: `${zone.pct}%` }}
                      />
                    </div>
                  </div>
                </div>
                <p className="mt-2 text-xs text-foreground/75">{zone.strategy}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Section 5: バックテスト実績 */}
        <section className="rounded-xl border border-gold-faint bg-card/60 p-6 sm:p-8">
          <h2 className="font-serif text-xl font-semibold">バックテスト実績</h2>
          <p className="mt-2 text-xs text-muted-foreground">
            2種類の検証を実施しています。信頼性の観点から時系列分離検証を正式な評価値としています。
          </p>

          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* 参考値カード */}
            <div className="rounded-lg border border-gold-faint/60 bg-background/40 p-4">
              <div className="flex items-center justify-between gap-2 mb-3">
                <p className="text-sm font-semibold text-foreground/80">全期間バックテスト</p>
                <span className="shrink-0 rounded border border-muted-foreground/30 bg-muted-foreground/10 px-2 py-0.5 text-[10px] text-muted-foreground">
                  ※参考
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground mb-3">
                対象: 2015〜2026年 重賞1,544R（G1/G2/G3）
              </p>
              <div className="grid grid-cols-2 gap-2">
                {backtestFull.map((stat) => (
                  <div key={stat.label} className="rounded border border-gold-faint/40 bg-card/40 p-2 text-center">
                    <p className="text-[10px] text-muted-foreground leading-snug">{stat.label}</p>
                    <p className="mt-1 font-serif text-xl font-bold text-foreground/70">
                      {stat.value}
                      <span className="text-xs font-normal ml-0.5">{stat.unit}</span>
                    </p>
                    <p className="mt-0.5 text-[9px] text-muted-foreground/70">{stat.sub}</p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-[10px] text-muted-foreground/80 leading-relaxed">
                ⚠ 統計構築データと検証データが重複するため、実態より高く出る参考値です。
              </p>
            </div>

            {/* 時系列分離カード（強調） */}
            <div className="rounded-lg border border-gold/40 bg-gold/5 p-4 ring-1 ring-gold/20">
              <div className="flex items-center justify-between gap-2 mb-3">
                <p className="text-sm font-semibold text-gold">時系列分離検証</p>
                <span className="shrink-0 rounded border border-positive/40 bg-positive/15 px-2 py-0.5 text-[10px] font-medium text-positive">
                  ✓ 正式評価値
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground mb-3">
                対象: 2022〜2026年 588R（G1/G2/G3）
              </p>
              <div className="grid grid-cols-3 gap-2">
                {backtestClean.map((stat) => (
                  <div key={stat.label} className="rounded border border-gold/25 bg-background/60 p-2 text-center">
                    <p className="text-[10px] text-muted-foreground leading-snug">{stat.label}</p>
                    <p className="mt-1 font-serif text-xl font-bold text-gold-gradient">
                      {stat.value}
                      <span className="text-xs font-normal ml-0.5">{stat.unit}</span>
                    </p>
                    <p className="mt-0.5 text-[9px] text-muted-foreground">{stat.sub}</p>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-[10px] text-foreground/70 leading-relaxed">
                ✓ 学習データとテストデータを時系列で完全分離。データリークなしの検証値です。
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-lg border border-gold-faint/60 bg-background/40 p-4">
            <p className="text-xs font-medium text-foreground/80 mb-2">主要な検証知見</p>
            <ul className="space-y-1.5 text-xs text-foreground/70 list-disc list-inside">
              <li>7軸化（BF/HP除外）で 9軸比 +3.1% 改善（32.2% → 35.3%）</li>
              <li>穴馬戦略（◎4番人気以上×2200m未満）: 単勝ROI 227.7%（150R）</li>
              <li>G2 での穴馬戦略回収率 310.7% が最も高い</li>
              <li>時系列分離後の真ROI 133.1%（条件C・全軸リーク排除版）</li>
            </ul>
          </div>
        </section>

        {/* Section 6: ご注意・免責事項 */}
        <section className="rounded-xl border border-gold-faint/50 bg-card/40 p-6 sm:p-8">
          <h2 className="font-serif text-xl font-semibold text-muted-foreground">ご注意・免責事項</h2>
          <div className="mt-4 space-y-3 text-xs leading-relaxed text-muted-foreground">
            <p>
              本サイトは JRA 公認・認定のサービスではありません。
              競馬の予測・分析情報を提供することを目的としており、
              馬券の購入を勧誘するものではありません。
            </p>
            <p>
              過去のバックテスト結果は将来の利益を保証するものではありません。
              馬券購入は自己の判断と責任のもとで行ってください。
            </p>
            <p>
              掲載している予測・分析は学習・研究目的のものです。
              本サービスの情報に基づく損失について、運営者は一切の責任を負いません。
            </p>
          </div>
        </section>
      </main>

      <footer className="mt-12 border-t border-gold-faint bg-background py-8 text-center">
        <p className="font-serif text-sm text-gold-gradient">COURSE MASTER</p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          © 2026 COURSE MASTER. All rights reserved.
        </p>
      </footer>
    </div>
  )
}
