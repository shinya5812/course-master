export const nav = [
  { label: "トップ", href: "/", active: true },
  { label: "的中実績", href: "/results", highlight: true },
  { label: "今週の予測", href: "/weekly" },
  { label: "荒れ指数", href: "/analysis#adi" },
  { label: "分析メソッド", href: "/analysis" },
  { label: "プラン", href: "/plan" },
  { label: "ログイン", href: "#" },
]

export const performance = [
  { label: "的中率", mark: "◎", value: "27.1", unit: "%", sub: "248R / 916R" },
  { label: "単勝回収率", value: "148.8", unit: "%", sub: "+488,600 円" },
  { label: "回収率（全体）", value: "112.3", unit: "%", sub: "+123,450 円" },
  { label: "勝率期待値", value: "+6.12", unit: "%", sub: "平均エッジ" },
]

export const returnTrend = [
  { month: "1月", value: -12 },
  { month: "1月中", value: -28 },
  { month: "2月", value: -5 },
  { month: "2月中", value: 8 },
  { month: "3月", value: -2 },
  { month: "3月中", value: 14 },
  { month: "4月", value: 9 },
  { month: "4月中", value: 22 },
  { month: "5月", value: 31 },
  { month: "5月中", value: 47 },
]

export type RaceCard = {
  name: string
  grade: string
  schedule: string
  adi: number
  fri: number
  tag: string
  tagTone: "danger" | "positive" | "warn"
  horseNo: string
  horseName: string
  edge: string
  winProb: string
}

export const weeklyRaces: RaceCard[] = [
  {
    name: "日本ダービー",
    grade: "G1",
    schedule: "5/26 (日) 東京 11R 芝2400m",
    adi: 72,
    fri: 31,
    tag: "大波乱注意",
    tagTone: "danger",
    horseNo: "12番",
    horseName: "サンプルホース",
    edge: "+6.1%",
    winProb: "14.2%",
  },
  {
    name: "安田記念",
    grade: "G1",
    schedule: "6/2 (日) 東京 11R 芝1600m",
    adi: 48,
    fri: 22,
    tag: "安定予想",
    tagTone: "positive",
    horseNo: "8番",
    horseName: "サンプルホース",
    edge: "+4.3%",
    winProb: "12.6%",
  },
  {
    name: "宝塚記念",
    grade: "G1",
    schedule: "6/23 (日) 阪神 11R 芝2200m",
    adi: 63,
    fri: 28,
    tag: "波乱含み",
    tagTone: "danger",
    horseNo: "6番",
    horseName: "サンプルホース",
    edge: "+5.7%",
    winProb: "11.8%",
  },
  {
    name: "目黒記念",
    grade: "G2",
    schedule: "5/26 (日) 東京 10R 芝2500m",
    adi: 55,
    fri: 27,
    tag: "中波乱",
    tagTone: "warn",
    horseNo: "3番",
    horseName: "サンプルホース",
    edge: "+3.9%",
    winProb: "10.1%",
  },
]

export const ranking = [
  { rank: 1, no: "12", name: "サンプルホース", race: "日本ダービー", est: "14.2%", mkt: "8.1%", edge: "+6.1%" },
  { rank: 2, no: "8", name: "サンプルホース", race: "安田記念", est: "12.6%", mkt: "8.3%", edge: "+4.3%" },
  { rank: 3, no: "6", name: "サンプルホース", race: "宝塚記念", est: "11.8%", mkt: "6.1%", edge: "+5.7%" },
  { rank: 4, no: "9", name: "サンプルホース", race: "日本ダービー", est: "9.3%", mkt: "5.4%", edge: "+5.9%" },
  { rank: 5, no: "3", name: "サンプルホース", race: "目黒記念", est: "10.1%", mkt: "6.2%", edge: "+3.9%" },
]

export const radarData = [
  { axis: "ペース", adi: 72, fri: 48 },
  { axis: "血統", adi: 58, fri: 40 },
  { axis: "マーケット", adi: 80, fri: 35 },
  { axis: "騎手", adi: 50, fri: 52 },
  { axis: "スピード", adi: 66, fri: 30 },
  { axis: "人気偏り", adi: 75, fri: 44 },
]

export const features = [
  {
    title: "データドリブン",
    desc: "過去11年超のレースデータを基に統計マスターを構築",
  },
  {
    title: "多角的な分析",
    desc: "12軸スコア×4チーム合議制で精度の高い予測を実現",
  },
  {
    title: "市場の歪みを可視化",
    desc: "エッジ値で妙味のある馬を明確に特定",
  },
  {
    title: "検証と改善の継続",
    desc: "バックテストと実運用の両輪でモデルを進化",
  },
]

export const news = [
  { date: "2026.05.24", text: "日本ダービーの予測を公開しました" },
  { date: "2026.05.21", text: "騎手×コース相性データを更新しました" },
  { date: "2026.05.20", text: "エンジン v7.3 rev2 をリリースしました" },
]
