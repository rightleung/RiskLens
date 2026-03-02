/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useEffect, Fragment, useMemo } from 'react'
import { Search, Loader2, Monitor, Sun, Moon, ArrowRight, CheckCircle2, AlertTriangle, ExternalLink, Info, Palette, Download } from 'lucide-react'
import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Tooltip, TooltipProvider } from '@/components/ui/tooltip'

interface Period {
  fiscal_year: string;
  assessment: {
    overall_rating: string;
    risk_score: number;
    implied_rating: string;
    strengths: string[];
    weaknesses: string[];
  };
  ratios: Record<string, number | null>;
  raw_metrics: Record<string, number | null>;
  statements: Record<string, Record<string, number>>;
}

interface AssessmentResponse {
  results?: Array<{
    ticker: string;
    company_name: string;
    company_name_localized?: Record<string, string>;
    currency?: string;
    history: Period[];
  }>;
  errors?: string[];
  suggestions?: Record<string, Array<{ symbol: string; name: string }>>;
}

// Format "Q3 '25 (U)" → "25Q3", "FY24" → "FY24"
function formatPeriodLabel(label: string): string {
  // Quarterly: e.g. "Q3 '25 (U)" → "25Q3"
  const qMatch = label.match(/Q(\d)\s+'?(\d{2})/);
  if (qMatch) return `${qMatch[2]}Q${qMatch[1]}`;
  return label;
}

function formatCurrency(val: number | null | undefined, format: 'compact' | 'full' = 'compact', lang: Language = 'en') {
  if (val === null || val === undefined || isNaN(val)) return '--';

  if (format === 'full') {
    return val.toLocaleString(lang === 'zh-CN' || lang === 'zh-TW' ? 'zh-CN' : 'en-US');
  }

  const abs = Math.abs(val);
  const sign = val < 0 ? '-' : '';
  if (abs >= 1e9) return sign + (abs / 1e9).toFixed(1) + 'B';
  if (abs >= 1e6) return sign + (abs / 1e6).toFixed(1) + 'M';
  if (abs >= 1e3) return sign + (abs / 1e3).toFixed(1) + 'K';
  return sign + abs.toFixed(1);
}

function getYahooUrl(ticker: string) {
  return `https://finance.yahoo.com/quote/${encodeURIComponent(ticker)}/financials/`;
}

type Language = 'en' | 'zh-CN' | 'zh-TW' | 'ja';
type ColorMode = 'system' | 'light' | 'dark';

const COLOR_MODE_STORAGE_KEY = 'risklens-color-mode';

const getInitialColorMode = (): ColorMode => {
  if (typeof window === 'undefined') return 'system';
  const savedMode = window.localStorage.getItem(COLOR_MODE_STORAGE_KEY);
  if (savedMode === 'light' || savedMode === 'dark' || savedMode === 'system') {
    return savedMode;
  }
  return 'system';
};

const translations = {
  en: {
    title: 'Institutional Credit Risk',
    subtitle: 'Enter a ticker or comma-separated list to synthesize risk.',
    placeholder: 'e.g. AAPL, MSFT, 0700.HK, 000002',
    synthesize: 'Synthesize',
    synthesizing: 'Synthesizing',
    failed: 'Assessment Failed',
    didYouMean: 'Did you mean:',
    zScore: 'Altman Z-Score',
    impliedRating: 'Implied Rating',
    strengths: 'Strengths',
    watchItems: 'Watch Items',
    noStrengths: 'No major strengths detected.',
    noWatchItems: 'No critical watch items.',
    source: 'Source: Yahoo Finance',
    sourceAKShare: 'Source: AKShare',
    akshareDisclaimer: 'Due to the use of an open-source API, a direct web verification link is not available for A-shares.',
    noData: 'No data available',
    incomeStatement: 'Income Statement',
    balanceSheet: 'Balance Sheet',
    cashFlow: 'Cash Flow',
    value: 'Value',
    ebit: 'EBIT',
    ebitda: 'EBITDA',
    totalDebt: 'Total Debt',
    debtToEbitda: 'Debt / EBITDA',
    interestCoverage: 'Interest Coverage',
    freeCf: 'Free Cash Flow',
    fcfToDebt: 'FCF / Debt',
    currentRatio: 'Current Ratio',
    themeSelect: 'Theme',
    otherNames: 'Other Names:',
    tickerCol: 'Ticker',
    companyCol: 'Company Name',
    zScoreCol: 'Z-Score',
    ratingCol: 'Implied Rating',
    metricCol: 'Metric',
    itemCol: 'Item',
    mainInfoTab: 'Main Info',
    financialsTab: 'Financials',
    excelKpiSheet: 'KPI Trends',
    excelStatementsSheet: 'Financial Statements',
    excelPortfolioKpiSheet: 'Portfolio KPI Comparison',
    excelPortfolioStatementsSheet: 'Portfolio Statement Comparison',
    excelCompanySheetSuffix: 'Statements',
    varVs: 'vs',
    varPct: 'Var (%)',
    exportAll: 'Export All',
    finComparisonTab: 'Fin Comparison',
    periodGuideTitle: 'How to Use Period Views',
    periodGuideBody: 'Click an FY chip to open that year’s financial statements. Export Excel to review cross-year comparisons.',
    periodButtonTitle: 'Open financial statements for this period'
  },
  'zh-CN': {
    title: '机构信用风险评估',
    subtitle: '输入股票代码或以逗号分隔的代码列表以综合评估风险。',
    placeholder: '例如：AAPL, MSFT, 0700.HK, 000002',
    synthesize: '综合分析',
    synthesizing: '分析中',
    failed: '评估失败',
    didYouMean: '您是指：',
    zScore: '奥特曼 Z-Score',
    impliedRating: '隐含评级',
    strengths: '优势',
    watchItems: '关注事项',
    noStrengths: '未发现主要优势。',
    noWatchItems: '未发现严重关注事项。',
    source: '来源：Yahoo Finance',
    sourceAKShare: '来源：AKShare',
    akshareDisclaimer: '由于采用开源本地 API 接口，此 A 股数据暂无法提供直接的网页版验证链接。',
    noData: '暂无数据',
    incomeStatement: '利润表',
    balanceSheet: '资产负债表',
    cashFlow: '现金流量表',
    value: '数值',
    ebit: '息税前利润 (EBIT)',
    ebitda: 'EBITDA',
    totalDebt: '总债务',
    debtToEbitda: '债务 / EBITDA',
    interestCoverage: '利息保障倍数',
    freeCf: '自由现金流',
    fcfToDebt: 'FCF / 债务',
    currentRatio: '流动比率',
    themeSelect: '主题选择',
    otherNames: '其他名称：',
    tickerCol: '代码',
    companyCol: '公司名称',
    zScoreCol: 'Z-Score评分',
    ratingCol: '隐含评级',
    metricCol: '指标',
    itemCol: '项目',
    mainInfoTab: '主要信息',
    financialsTab: '财务报表',
    excelKpiSheet: '关键指标趋势',
    excelStatementsSheet: '财务报表明细',
    excelPortfolioKpiSheet: '组合指标对比',
    excelPortfolioStatementsSheet: '组合报表对比',
    excelCompanySheetSuffix: '报表',
    varVs: '对比',
    varPct: '变动比例(%)',
    exportAll: '全部导出',
    finComparisonTab: '财报横向对比',
    periodGuideTitle: '期间查看说明',
    periodGuideBody: '点击 FY 年份按钮可查看对应期间的财务报表；导出 Excel 可查看跨年份对比。',
    periodButtonTitle: '打开该期间财务报表'
  },
  'zh-TW': {
    title: '機構信用風險評估',
    subtitle: '輸入股票代碼或以逗號分隔的代碼列表以綜合評估風險。',
    placeholder: '例如：AAPL, MSFT, 0700.HK, 000002',
    synthesize: '綜合分析',
    synthesizing: '分析中',
    failed: '評估失敗',
    didYouMean: '您是指：',
    zScore: '奧特曼 Z-Score',
    impliedRating: '隱含評級',
    strengths: '強項',
    watchItems: '關注事項',
    noStrengths: '未發現主要優勢。',
    noWatchItems: '未發現嚴重關注事項。',
    source: '來源：Yahoo Finance',
    sourceAKShare: '來源：AKShare',
    akshareDisclaimer: '由於採用開源本地 API 接口，此 A 股數據暫無法提供直接的網頁版驗證鏈接。',
    noData: '暫無數據',
    incomeStatement: '損益表',
    balanceSheet: '資產負債表',
    cashFlow: '現金流量表',
    value: '數值',
    ebit: '息稅前利潤 (EBIT)',
    ebitda: 'EBITDA',
    totalDebt: '總債務',
    debtToEbitda: '債務 / EBITDA',
    interestCoverage: '利息保障倍數',
    freeCf: '自由現金流',
    fcfToDebt: 'FCF / 債務',
    currentRatio: '流動比率',
    themeSelect: '主題選擇',
    otherNames: '其他名稱：',
    tickerCol: '代碼',
    companyCol: '公司名稱',
    zScoreCol: 'Z-Score評分',
    ratingCol: '隱含評級',
    metricCol: '指標',
    itemCol: '項目',
    mainInfoTab: '主要資訊',
    financialsTab: '財務報表',
    excelKpiSheet: '關鍵指標趨勢',
    excelStatementsSheet: '財務報表明細',
    excelPortfolioKpiSheet: '組合指標對比',
    excelPortfolioStatementsSheet: '組合報表對比',
    excelCompanySheetSuffix: '報表',
    varVs: '對比',
    varPct: '變動比例(%)',
    exportAll: '全部匯出',
    finComparisonTab: '財報橫向對比',
    periodGuideTitle: '期間檢視說明',
    periodGuideBody: '點擊 FY 年份按鈕可查看對應期間的財務報表；匯出 Excel 可查看跨年份對比。',
    periodButtonTitle: '開啟該期間財務報表'
  },
  ja: {
    title: '機関的信用リスク評価',
    subtitle: 'ティッカーまたはカンマ区切りのリストを入力してリスクを総合評価します。',
    placeholder: '例: AAPL, MSFT, 0700.HK, 000002',
    synthesize: '分析する',
    synthesizing: '分析中',
    failed: '評価失敗',
    didYouMean: 'もしかして：',
    zScore: 'アルトマン Z-Score',
    impliedRating: '予想格付け',
    strengths: '強み',
    watchItems: '懸念事項',
    noStrengths: '主な強みは見つかりませんでした。',
    noWatchItems: '深刻な懸念事項は見つかりませんでした。',
    source: 'ソース: Yahoo Finance',
    sourceAKShare: 'ソース: AKShare',
    akshareDisclaimer: 'オープンソースのAPIを使用しているため、A株の財務データを確認するための直接のWebリンクはありません。',
    noData: 'データなし',
    incomeStatement: '損益計算書',
    balanceSheet: '貸借対照表',
    cashFlow: 'キャッシュフロー計算書',
    value: '値',
    ebit: 'EBIT (利払前税引前利益)',
    ebitda: 'EBITDA',
    totalDebt: '総有利子負債',
    debtToEbitda: '有利子負債 / EBITDA',
    interestCoverage: 'ｲﾝﾀﾚｽﾄ・ｶﾊﾞﾚｯｼﾞ',
    freeCf: 'フリー・キャッシュフロー',
    fcfToDebt: 'FCF / 有利子負債',
    currentRatio: '流動比率',
    themeSelect: 'テーマ選択',
    otherNames: 'その他の名称：',
    tickerCol: 'ティッカー',
    companyCol: '会社名',
    zScoreCol: 'Z-Score',
    ratingCol: '予想格付け',
    metricCol: '指標',
    itemCol: '項目',
    mainInfoTab: '主要情報',
    financialsTab: '財務諸表',
    excelKpiSheet: 'KPI推移',
    excelStatementsSheet: '財務諸表明細',
    excelPortfolioKpiSheet: 'ポートフォリオKPI比較',
    excelPortfolioStatementsSheet: 'ポートフォリオ財務諸表比較',
    excelCompanySheetSuffix: '財務諸表',
    varVs: '比較',
    varPct: '増減率(%)',
    exportAll: 'すべてエクスポート',
    finComparisonTab: '財務諸表比較',
    periodGuideTitle: '期間表示の使い方',
    periodGuideBody: 'FY ボタンをクリックすると当該期間の財務諸表を表示します。Excel をエクスポートすると期間比較を確認できます。',
    periodButtonTitle: 'この期間の財務諸表を開く'
  }
};

const THEMES = [
  { id: 'monochrome', name: { en: 'Monochrome', 'zh-CN': '黑白', 'zh-TW': '黑白', ja: 'モノクロ' }, color: 'bg-black' },
  { id: 'celadon', name: { en: 'Celadon', 'zh-CN': '青瓷', 'zh-TW': '青瓷', ja: '青磁' }, color: 'bg-[#5F8F8A]' },
  { id: 'cinnabar', name: { en: 'Cinnabar', 'zh-CN': '朱砂', 'zh-TW': '朱砂', ja: '朱砂' }, color: 'bg-[#C84B31]' },
  { id: 'blackjade', name: { en: 'Black Jade', 'zh-CN': '墨玉', 'zh-TW': '墨玉', ja: '墨玉' }, color: 'bg-[#315C45]' },
  { id: 'navyblue', name: { en: 'Navy Blue', 'zh-CN': '藏蓝', 'zh-TW': '藏藍', ja: '紺青' }, color: 'bg-[#2B3A67]' },
  { id: 'amber', name: { en: 'Amber', 'zh-CN': '琥珀', 'zh-TW': '琥珀', ja: '琥珀' }, color: 'bg-[#D98E04]' },
  { id: 'carmine', name: { en: 'Carmine', 'zh-CN': '胭脂', 'zh-TW': '胭脂', ja: '臙脂' }, color: 'bg-[#9D2933]' },
  { id: 'clearsky', name: { en: 'Clear Sky', 'zh-CN': '晴空', 'zh-TW': '晴空', ja: '晴空' }, color: 'bg-[#3B82F6]' },
];

const getT = (lang: Language) => (key: keyof typeof translations['en']): string => translations[lang]?.[key] || translations['en'][key];

const getStatementTabs = (t: ReturnType<typeof getT>) => [
  { key: 'income', label: t('incomeStatement') },
  { key: 'balance', label: t('balanceSheet') },
  { key: 'cash', label: t('cashFlow') },
] as const;

export const exportToExcel = async (results: any[], t: ReturnType<typeof getT>, lang: Language) => {
  const wb = new ExcelJS.Workbook();

  const getColName = (n: number) => {
    // n is 0-indexed
    const ordA = 'A'.charCodeAt(0);
    const ordZ = 'Z'.charCodeAt(0);
    const len = ordZ - ordA + 1;
    let s = "";
    while (n >= 0) {
      s = String.fromCharCode(n % len + ordA) + s;
      n = Math.floor(n / len) - 1;
    }
    return s;
  };

  const addRowWithFormat = (ws: ExcelJS.Worksheet, rowData: any[]) => {
    const row = ws.addRow(rowData.map(v => {
      if (v && typeof v === 'object' && v.f) {
        return { formula: v.f };
      }
      return v;
    }));

    row.eachCell((cell: ExcelJS.Cell, colNumber: number) => {
      const orig = rowData[colNumber - 1];
      if (orig && typeof orig === 'object' && orig.f) {
        cell.numFmt = orig.z || '#,##0.00';
      } else if (typeof orig === 'number') {
        cell.numFmt = '#,##0.00';
      }
    });
    return row;
  };

  const toNumber = (value: unknown): number | null =>
    typeof value === 'number' && Number.isFinite(value) ? value : null;

  const formatActual = (value: number | null) => (value === null ? '--' : value);

  const riskTextByLang: Record<Language, {
    sheetName: string;
    title: string;
    ticker: string;
    companyName: string;
    latestPeriod: string;
    currency: string;
    altman: string;
    zone: string;
    impliedRating: string;
    strengths: string;
    watchItems: string;
    none: string;
    na: string;
    covenantPreCheck: string;
    metric: string;
    actual: string;
    threshold: string;
    status: string;
    signal: string;
    notes: string;
    dataQuality: string;
    breachCount: string;
    missingKeyInputs: string;
    missingItems: string;
    statusBreachMissing: string;
    statusBreach: string;
    statusPass: string;
    signalWatch: string;
    signalStrong: string;
    signalNeutral: string;
    noteMissingInput: string;
    noteBelowMinimum: (threshold: number) => string;
    noteAboveMaximum: (threshold: number) => string;
    noteComfortableAbove: string;
    noteComfortableBelow: string;
    noteWithinThreshold: string;
  }> = {
    en: {
      sheetName: 'Risk Report',
      title: 'Risk Report',
      ticker: 'Ticker',
      companyName: 'Company Name',
      latestPeriod: 'Latest Period',
      currency: 'Currency',
      altman: 'Altman Z-Score',
      zone: 'Z-Score Zone',
      impliedRating: 'Implied Rating',
      strengths: 'Strengths',
      watchItems: 'Watch Items',
      none: 'None',
      na: 'N/A',
      covenantPreCheck: 'Covenant Pre-Check',
      metric: 'Metric',
      actual: 'Actual',
      threshold: 'Threshold',
      status: 'Status',
      signal: 'Signal',
      notes: 'Notes',
      dataQuality: 'Data Quality',
      breachCount: 'Breach Count',
      missingKeyInputs: 'Missing Key Inputs',
      missingItems: 'Missing Items',
      statusBreachMissing: 'BREACH (DATA MISSING)',
      statusBreach: 'BREACH',
      statusPass: 'PASS',
      signalWatch: 'Watch',
      signalStrong: 'Strong',
      signalNeutral: 'Neutral',
      noteMissingInput: 'Missing input',
      noteBelowMinimum: (threshold: number) => `Below minimum ${threshold}`,
      noteAboveMaximum: (threshold: number) => `Above maximum ${threshold}`,
      noteComfortableAbove: 'Comfortable buffer above threshold',
      noteComfortableBelow: 'Comfortable buffer below threshold',
      noteWithinThreshold: 'Within threshold',
    },
    'zh-CN': {
      sheetName: '风险报告',
      title: '风险报告',
      ticker: '代码',
      companyName: '公司名称',
      latestPeriod: '最新期间',
      currency: '币种',
      altman: 'Altman Z-Score',
      zone: 'Z-Score 分区',
      impliedRating: '隐含评级',
      strengths: '优势',
      watchItems: '关注事项',
      none: '无',
      na: 'N/A',
      covenantPreCheck: '契约预检查',
      metric: '指标',
      actual: '实际值',
      threshold: '阈值',
      status: '状态',
      signal: '信号',
      notes: '备注',
      dataQuality: '数据质量',
      breachCount: '违约计数',
      missingKeyInputs: '关键缺失项数量',
      missingItems: '缺失项目',
      statusBreachMissing: '违约（数据缺失）',
      statusBreach: '违约',
      statusPass: '通过',
      signalWatch: '关注',
      signalStrong: '强',
      signalNeutral: '中性',
      noteMissingInput: '关键输入缺失',
      noteBelowMinimum: (threshold: number) => `低于下限 ${threshold}`,
      noteAboveMaximum: (threshold: number) => `高于上限 ${threshold}`,
      noteComfortableAbove: '高于阈值且缓冲充足',
      noteComfortableBelow: '低于阈值且缓冲充足',
      noteWithinThreshold: '处于阈值范围内',
    },
    'zh-TW': {
      sheetName: '風險報告',
      title: '風險報告',
      ticker: '代碼',
      companyName: '公司名稱',
      latestPeriod: '最新期間',
      currency: '幣別',
      altman: 'Altman Z-Score',
      zone: 'Z-Score 分區',
      impliedRating: '隱含評級',
      strengths: '優勢',
      watchItems: '關注事項',
      none: '無',
      na: 'N/A',
      covenantPreCheck: '契約預檢查',
      metric: '指標',
      actual: '實際值',
      threshold: '門檻',
      status: '狀態',
      signal: '訊號',
      notes: '備註',
      dataQuality: '資料品質',
      breachCount: '違約計數',
      missingKeyInputs: '關鍵缺失項數量',
      missingItems: '缺失項目',
      statusBreachMissing: '違約（資料缺失）',
      statusBreach: '違約',
      statusPass: '通過',
      signalWatch: '關注',
      signalStrong: '強',
      signalNeutral: '中性',
      noteMissingInput: '關鍵輸入缺失',
      noteBelowMinimum: (threshold: number) => `低於下限 ${threshold}`,
      noteAboveMaximum: (threshold: number) => `高於上限 ${threshold}`,
      noteComfortableAbove: '高於門檻且緩衝充足',
      noteComfortableBelow: '低於門檻且緩衝充足',
      noteWithinThreshold: '位於門檻範圍內',
    },
    ja: {
      sheetName: 'リスクレポート',
      title: 'リスクレポート',
      ticker: 'ティッカー',
      companyName: '会社名',
      latestPeriod: '最新期間',
      currency: '通貨',
      altman: 'Altman Z-Score',
      zone: 'Z-Score 区分',
      impliedRating: '予想格付け',
      strengths: '強み',
      watchItems: '懸念事項',
      none: 'なし',
      na: 'N/A',
      covenantPreCheck: 'コベナンツ事前チェック',
      metric: '指標',
      actual: '実績値',
      threshold: '閾値',
      status: '判定',
      signal: 'シグナル',
      notes: '備考',
      dataQuality: 'データ品質',
      breachCount: '違反件数',
      missingKeyInputs: '主要欠損入力数',
      missingItems: '欠損項目',
      statusBreachMissing: '違反（データ欠損）',
      statusBreach: '違反',
      statusPass: '適合',
      signalWatch: '注意',
      signalStrong: '強い',
      signalNeutral: '中立',
      noteMissingInput: '入力データ欠損',
      noteBelowMinimum: (threshold: number) => `下限 ${threshold} を下回る`,
      noteAboveMaximum: (threshold: number) => `上限 ${threshold} を上回る`,
      noteComfortableAbove: '閾値上方の余裕が大きい',
      noteComfortableBelow: '閾値下方の余裕が大きい',
      noteWithinThreshold: '閾値範囲内',
    },
  };

  const riskText = riskTextByLang[lang];

  type CovenantEval = {
    status: 'data_missing' | 'breach' | 'pass';
    signal: 'watch' | 'strong' | 'neutral';
    note: 'missing_input' | 'below_minimum' | 'above_maximum' | 'comfortable_above' | 'comfortable_below' | 'within_threshold';
  };

  const evaluateCovenant = (value: number | null, threshold: number, comparator: 'min' | 'max'): CovenantEval => {
    if (value === null) {
      return {
        status: 'data_missing',
        signal: 'watch',
        note: 'missing_input',
      };
    }
    if (comparator === 'min') {
      if (value < threshold) return { status: 'breach', signal: 'watch', note: 'below_minimum' };
      if (value >= threshold * 1.25) return { status: 'pass', signal: 'strong', note: 'comfortable_above' };
      return { status: 'pass', signal: 'neutral', note: 'within_threshold' };
    }
    if (value > threshold) return { status: 'breach', signal: 'watch', note: 'above_maximum' };
    if (value <= threshold * 0.75) return { status: 'pass', signal: 'strong', note: 'comfortable_below' };
    return { status: 'pass', signal: 'neutral', note: 'within_threshold' };
  };

  const localizeStatus = (status: CovenantEval['status']) => {
    if (status === 'data_missing') return riskText.statusBreachMissing;
    if (status === 'breach') return riskText.statusBreach;
    return riskText.statusPass;
  };

  const localizeSignal = (signal: CovenantEval['signal']) => {
    if (signal === 'watch') return riskText.signalWatch;
    if (signal === 'strong') return riskText.signalStrong;
    return riskText.signalNeutral;
  };

  const localizeNote = (note: CovenantEval['note'], threshold: number) => {
    if (note === 'missing_input') return riskText.noteMissingInput;
    if (note === 'below_minimum') return riskText.noteBelowMinimum(threshold);
    if (note === 'above_maximum') return riskText.noteAboveMaximum(threshold);
    if (note === 'comfortable_above') return riskText.noteComfortableAbove;
    if (note === 'comfortable_below') return riskText.noteComfortableBelow;
    return riskText.noteWithinThreshold;
  };

  if (results.length === 1) {
    // === SINGLE COMPANY LOGIC ===
    const res = results[0];
    const latest = res.history[0];
    const latestAssessment = latest?.assessment;
    const wsRisk = wb.addWorksheet(riskText.sheetName, { properties: { tabColor: { argb: 'FF8064A2' } } });
    const covenantRows = [
      {
        metric: t('interestCoverage'),
        actual: toNumber(latest?.ratios?.interest_coverage),
        threshold: '>= 3.0',
        comparator: 'min' as const,
        thresholdValue: 3.0,
      },
      {
        metric: t('debtToEbitda'),
        actual: toNumber(latest?.ratios?.debt_to_ebitda),
        threshold: '<= 4.0',
        comparator: 'max' as const,
        thresholdValue: 4.0,
      },
      {
        metric: t('currentRatio'),
        actual: toNumber(latest?.ratios?.current_ratio),
        threshold: '>= 1.2',
        comparator: 'min' as const,
        thresholdValue: 1.2,
      },
      {
        metric: t('fcfToDebt'),
        actual: toNumber(latest?.ratios?.fcf_to_debt),
        threshold: '>= 0.05',
        comparator: 'min' as const,
        thresholdValue: 0.05,
      },
    ].map((row) => {
      const result = evaluateCovenant(row.actual, row.thresholdValue, row.comparator);
      return {
        ...row,
        status: localizeStatus(result.status),
        signal: localizeSignal(result.signal),
        note: localizeNote(result.note, row.thresholdValue),
        isBreach: result.status === 'breach' || result.status === 'data_missing',
        isMissing: result.status === 'data_missing',
      };
    });

    const breachCount = covenantRows.filter((row) => row.isBreach).length;
    const missingItems = covenantRows.filter((row) => row.isMissing).map((row) => row.metric);

    addRowWithFormat(wsRisk, [riskText.title, '']);
    addRowWithFormat(wsRisk, [riskText.ticker, res.ticker]);
    addRowWithFormat(wsRisk, [riskText.companyName, res.company_name_localized?.[lang] || res.company_name]);
    addRowWithFormat(wsRisk, [riskText.latestPeriod, latest ? formatPeriodLabel(latest.fiscal_year) : riskText.na]);
    addRowWithFormat(wsRisk, [riskText.currency, res.currency || riskText.na]);
    addRowWithFormat(wsRisk, [riskText.altman, toNumber(latestAssessment?.risk_score) ?? riskText.na]);
    addRowWithFormat(wsRisk, [riskText.zone, latestAssessment?.overall_rating || riskText.na]);
    addRowWithFormat(wsRisk, [riskText.impliedRating, translateRatingStatus(latestAssessment?.implied_rating || riskText.na, lang)]);
    addRowWithFormat(wsRisk, [riskText.strengths, Array.isArray(latestAssessment?.strengths) && latestAssessment.strengths.length > 0 ? latestAssessment.strengths.join(' | ') : riskText.none]);
    addRowWithFormat(wsRisk, [riskText.watchItems, Array.isArray(latestAssessment?.weaknesses) && latestAssessment.weaknesses.length > 0 ? latestAssessment.weaknesses.join(' | ') : riskText.none]);
    addRowWithFormat(wsRisk, []);
    addRowWithFormat(wsRisk, [riskText.covenantPreCheck, '', '', '', '', '']);
    addRowWithFormat(wsRisk, [riskText.metric, riskText.actual, riskText.threshold, riskText.status, riskText.signal, riskText.notes]);
    covenantRows.forEach((row) => {
      addRowWithFormat(wsRisk, [row.metric, formatActual(row.actual), row.threshold, row.status, row.signal, row.note]);
    });
    addRowWithFormat(wsRisk, []);
    addRowWithFormat(wsRisk, [riskText.dataQuality, '']);
    addRowWithFormat(wsRisk, [riskText.breachCount, breachCount]);
    addRowWithFormat(wsRisk, [riskText.missingKeyInputs, missingItems.length]);
    addRowWithFormat(wsRisk, [riskText.missingItems, missingItems.length > 0 ? missingItems.join(', ') : riskText.none]);

    const ws1 = wb.addWorksheet(t('excelKpiSheet'), { properties: { tabColor: { argb: 'FF4F81BD' } } });

    addRowWithFormat(ws1, [t('tickerCol'), t('companyCol'), t('zScoreCol'), t('ratingCol')]);
    addRowWithFormat(ws1, [
      res.ticker,
      res.company_name_localized?.[lang] || res.company_name,
      latest?.assessment?.risk_score ?? 'N/A',
      translateRatingStatus(latest?.assessment?.implied_rating || 'N/A', lang)
    ]);
    addRowWithFormat(ws1, []);

    const annuals = res.history.filter((h: any) => !h.is_quarterly);
    let hasYoY = false;
    const yoyMap: { yearCode: string, prevYearCode: string, p1: any, p2: any }[] = [];

    if (annuals.length >= 2) {
      hasYoY = true;
      yoyMap.push({
        yearCode: formatPeriodLabel(annuals[0].fiscal_year),
        prevYearCode: formatPeriodLabel(annuals[1].fiscal_year),
        p1: annuals[0],
        p2: annuals[1]
      });
      if (annuals.length >= 3) {
        yoyMap.push({
          yearCode: formatPeriodLabel(annuals[1].fiscal_year),
          prevYearCode: formatPeriodLabel(annuals[2].fiscal_year),
          p1: annuals[1],
          p2: annuals[2]
        });
      }
    }

    const baseYearsLabels = res.history.map((h: any) => formatPeriodLabel(h.fiscal_year));
    const yearsRow = [t('metricCol'), ...baseYearsLabels];
    if (hasYoY) {
      yearsRow.push(''); // Spacer column
      yoyMap.forEach(cmp => {
        yearsRow.push(`${cmp.yearCode} ${t('varVs')} ${cmp.prevYearCode}`);
        yearsRow.push(t('varPct'));
      });
    }
    addRowWithFormat(ws1, yearsRow);

    const metricRowsLocal = [
      { key: 'operating_income', label: t('ebit'), src: 'raw_metrics' },
      { key: 'ebitda', label: t('ebitda'), src: 'ratios' },
      { key: 'total_debt', label: t('totalDebt'), src: 'raw_metrics' },
      { key: 'debt_to_ebitda', label: t('debtToEbitda'), src: 'ratios' },
      { key: 'interest_coverage', label: t('interestCoverage'), src: 'ratios' },
      { key: 'free_cf', label: t('freeCf'), src: 'raw_metrics' },
      { key: 'fcf_to_debt', label: t('fcfToDebt'), src: 'ratios' },
      { key: 'current_ratio', label: t('currentRatio'), src: 'ratios' },
    ];

    const baseColMap: Record<string, string> = {};
    res.history.forEach((h: any, i: number) => {
      baseColMap[h.fiscal_year] = getColName(i + 1); // 1-indexed to skip label
    });

    metricRowsLocal.forEach(row => {
      const rowData: (any)[] = [row.label];
      const rLabel = ws1.rowCount + 1;

      res.history.forEach((h: any) => {
        const sourceObj = row.src === 'ratios' ? h.ratios : h.raw_metrics;
        const rawVal = sourceObj ? sourceObj[row.key] : null;
        rowData.push(rawVal !== null && rawVal !== undefined ? rawVal : '--');
      });

      if (hasYoY) {
        rowData.push(''); // Spacer
        yoyMap.forEach(cmp => {
          const s1 = row.src === 'ratios' ? cmp.p1.ratios : cmp.p1.raw_metrics;
          const s2 = row.src === 'ratios' ? cmp.p2.ratios : cmp.p2.raw_metrics;

          const v1 = s1 ? s1[row.key] : null;
          const v2 = s2 ? s2[row.key] : null;

          if (v1 !== null && v2 !== null && v1 !== undefined && v2 !== undefined) {
            const col1 = baseColMap[cmp.p1.fiscal_year];
            const col2 = baseColMap[cmp.p2.fiscal_year];
            rowData.push({ t: 'n', z: '#,##0.00', f: `${col1}${rLabel}-${col2}${rLabel}` });
            rowData.push({ t: 'n', z: '0.00%', f: `IFERROR((${col1}${rLabel}-${col2}${rLabel})/ABS(${col2}${rLabel}), "-")` });
          } else {
            rowData.push('--');
            rowData.push('--');
          }
        });
      }

      addRowWithFormat(ws1, rowData);
    });

    const ws2 = wb.addWorksheet(t('excelStatementsSheet'), { properties: { tabColor: { argb: 'FF9BBB59' } } });

    const finHeaderRow = [t('itemCol'), ...res.history.map((h: any) => formatPeriodLabel(h.fiscal_year))];
    if (hasYoY) {
      finHeaderRow.push(''); // Spacer column
      yoyMap.forEach(cmp => {
        finHeaderRow.push(`${cmp.yearCode} ${t('varVs')} ${cmp.prevYearCode}`);
        finHeaderRow.push(t('varPct'));
      });
    }
    addRowWithFormat(ws2, finHeaderRow);

    const allKeys = new Set<string>();
    res.history.forEach((h: any) => {
      if (h.statements) {
        Object.keys(h.statements).forEach(tab => {
          Object.keys(h.statements[tab]).forEach(k => allKeys.add(k));
        });
      }
    });

    Array.from(allKeys).forEach(k => {
      const rowData: (any)[] = [prettifyKey(k, lang)];
      const rLabel = ws2.rowCount + 1;

      res.history.forEach((h: any) => {
        let val: any = '--';
        if (h.statements) {
          for (const tab of ['income', 'balance', 'cash']) {
            if (h.statements[tab] && h.statements[tab][k] !== undefined) {
              val = h.statements[tab][k];
              break;
            }
          }
        }
        rowData.push(val);
      });

      if (hasYoY) {
        rowData.push(''); // Spacer
        yoyMap.forEach(cmp => {
          let v1: number | null = null;
          let v2: number | null = null;

          if (cmp.p1.statements) {
            for (const tab of ['income', 'balance', 'cash']) {
              if (cmp.p1.statements[tab] && cmp.p1.statements[tab][k] !== undefined) {
                v1 = cmp.p1.statements[tab][k];
                break;
              }
            }
          }
          if (cmp.p2.statements) {
            for (const tab of ['income', 'balance', 'cash']) {
              if (cmp.p2.statements[tab] && cmp.p2.statements[tab][k] !== undefined) {
                v2 = cmp.p2.statements[tab][k];
                break;
              }
            }
          }

          if (v1 !== null && v2 !== null && v1 !== undefined && v2 !== undefined) {
            const col1 = baseColMap[cmp.p1.fiscal_year];
            const col2 = baseColMap[cmp.p2.fiscal_year];
            rowData.push({ t: 'n', z: '#,##0.00', f: `${col1}${rLabel}-${col2}${rLabel}` });
            rowData.push({ t: 'n', z: '0.00%', f: `IFERROR((${col1}${rLabel}-${col2}${rLabel})/ABS(${col2}${rLabel}), "-")` });
          } else {
            rowData.push('--');
            rowData.push('--');
          }
        });
      }
      addRowWithFormat(ws2, rowData);
    });

    const buffer = await wb.xlsx.writeBuffer();
    saveAs(new Blob([buffer]), `${res.ticker}_Financial_Data.xlsx`);
    return;
  }

  // === MULTI-COMPANY LOGIC ===
  const allPeriodsArr: string[] = [];
  results.forEach(res => {
    res.history.forEach((h: any) => {
      if (!allPeriodsArr.includes(h.fiscal_year)) {
        allPeriodsArr.push(h.fiscal_year);
      }
    });
  });

  const sortPeriods = (a: string, b: string) => {
    const fA = formatPeriodLabel(a);
    const fB = formatPeriodLabel(b);

    const yrFromStr = (s: string) => {
      const match = s.match(/\d{2}/);
      return match ? parseInt(match[0]) : 0;
    };
    const yrA = yrFromStr(fA);
    const yrB = yrFromStr(fB);

    if (yrA !== yrB) return yrB - yrA;

    const isQA = fA.includes('Q');
    const isQB = fB.includes('Q');

    if (isQA && !isQB) return 1;
    if (!isQA && isQB) return -1;

    if (isQA && isQB) {
      const qA = parseInt(fA.split('Q')[1] || '0');
      const qB = parseInt(fB.split('Q')[1] || '0');
      return qB - qA;
    }
    return 0;
  };
  allPeriodsArr.sort(sortPeriods);

  const metricRowsLocal = [
    { key: 'operating_income', label: t('ebit'), src: 'raw_metrics' },
    { key: 'ebitda', label: t('ebitda'), src: 'ratios' },
    { key: 'total_debt', label: t('totalDebt'), src: 'raw_metrics' },
    { key: 'debt_to_ebitda', label: t('debtToEbitda'), src: 'ratios' },
    { key: 'interest_coverage', label: t('interestCoverage'), src: 'ratios' },
    { key: 'free_cf', label: t('freeCf'), src: 'raw_metrics' },
    { key: 'fcf_to_debt', label: t('fcfToDebt'), src: 'ratios' },
    { key: 'current_ratio', label: t('currentRatio'), src: 'ratios' },
  ];

  const wsMain = wb.addWorksheet(t('excelPortfolioKpiSheet'), { properties: { tabColor: { argb: 'FF4F81BD' } } });
  const colsPerPeriod = results.length === 1 ? 1 : 1 + (results.length - 1) * 3;

  const header1: any[] = [t('metricCol')];
  allPeriodsArr.forEach(p => {
    header1.push(formatPeriodLabel(p));
    for (let i = 1; i < colsPerPeriod; i++) header1.push(''); // Reserved for merge
  });
  addRowWithFormat(wsMain, header1);

  const header2: any[] = [''];
  allPeriodsArr.forEach(() => {
    const baseCName = results[0].company_name_localized?.[lang] || results[0].company_name;
    header2.push(baseCName);
    for (let i = 1; i < results.length; i++) {
      const cName = results[i].company_name_localized?.[lang] || results[i].company_name;
      header2.push(cName);
      header2.push(`${cName} vs ${baseCName}`);
      header2.push(t('varPct'));
    }
  });
  addRowWithFormat(wsMain, header2);

  metricRowsLocal.forEach(row => {
    const rowData: (any)[] = [row.label];
    const rLabel = wsMain.rowCount + 1;

    allPeriodsArr.forEach((p, pIdx) => {
      const periodStartColIdx = 1 + pIdx * colsPerPeriod;
      const baseExcelCol = getColName(periodStartColIdx);

      const h0 = results[0].history.find((x: any) => x.fiscal_year === p);
      const sourceObj0 = h0 ? (row.src === 'ratios' ? h0.ratios : h0.raw_metrics) : null;
      const val0 = sourceObj0 ? sourceObj0[row.key] : null;
      rowData.push(val0 !== null && val0 !== undefined ? val0 : '--');

      for (let i = 1; i < results.length; i++) {
        const currentExcelCol = getColName(periodStartColIdx + 1 + (i - 1) * 3);

        const hi = results[i].history.find((x: any) => x.fiscal_year === p);
        const sourceObji = hi ? (row.src === 'ratios' ? hi.ratios : hi.raw_metrics) : null;
        const vali = sourceObji ? sourceObji[row.key] : null;
        rowData.push(vali !== null && vali !== undefined ? vali : '--');

        if (val0 !== null && val0 !== undefined && vali !== null && vali !== undefined) {
          rowData.push({ t: 'n', z: '#,##0.00', f: `${currentExcelCol}${rLabel}-${baseExcelCol}${rLabel}` });
          rowData.push({ t: 'n', z: '0.00%', f: `IFERROR((${currentExcelCol}${rLabel}-${baseExcelCol}${rLabel})/ABS(${baseExcelCol}${rLabel}), "-")` });
        } else {
          rowData.push('--');
          rowData.push('--');
        }
      }
    });
    addRowWithFormat(wsMain, rowData);
  });

  // Merge headers in Main Info
  let colIndex = 2; // exceljs cols are 1-indexed, starting at B
  allPeriodsArr.forEach(() => {
    wsMain.mergeCells(1, colIndex, 1, colIndex + colsPerPeriod - 1);
    colIndex += colsPerPeriod;
  });

  // Financial Comparison Sheet
  const wsFinComp = wb.addWorksheet(t('excelPortfolioStatementsSheet'), { properties: { tabColor: { argb: 'FF8064A2' } } });

  const compHeader1: any[] = [t('itemCol')];
  allPeriodsArr.forEach(p => {
    compHeader1.push(formatPeriodLabel(p));
    for (let i = 1; i < colsPerPeriod; i++) compHeader1.push(''); // Span for columns
  });
  addRowWithFormat(wsFinComp, compHeader1);

  const compHeader2: any[] = [''];
  allPeriodsArr.forEach(() => {
    const baseCName = results[0].company_name_localized?.[lang] || results[0].company_name;
    compHeader2.push(baseCName);
    for (let i = 1; i < results.length; i++) {
      const cName = results[i].company_name_localized?.[lang] || results[i].company_name;
      compHeader2.push(cName);
      compHeader2.push(`${cName} vs ${baseCName}`);
      compHeader2.push(t('varPct'));
    }
  });
  addRowWithFormat(wsFinComp, compHeader2);

  const allCompKeys = new Set<string>();
  results.forEach(res => {
    res.history.forEach((h: any) => {
      if (h.statements) {
        Object.keys(h.statements).forEach(tab => {
          Object.keys(h.statements[tab]).forEach(k => allCompKeys.add(k));
        });
      }
    });
  });

  Array.from(allCompKeys).forEach(k => {
    const rowData: (any)[] = [prettifyKey(k, lang)];
    const rLabel = wsFinComp.rowCount + 1;

    allPeriodsArr.forEach((p, pIdx) => {
      const periodStartColIdx = 1 + pIdx * colsPerPeriod;
      const baseExcelCol = getColName(periodStartColIdx);

      const h0 = results[0].history.find((x: any) => x.fiscal_year === p);
      let val0: any = '--';
      if (h0 && h0.statements) {
        for (const tab of ['income', 'balance', 'cash']) {
          if (h0.statements[tab] && h0.statements[tab][k] !== undefined) {
            val0 = h0.statements[tab][k];
            break;
          }
        }
      }
      rowData.push(val0);

      for (let i = 1; i < results.length; i++) {
        const currentExcelCol = getColName(periodStartColIdx + 1 + (i - 1) * 3);

        const hi = results[i].history.find((x: any) => x.fiscal_year === p);
        let vali: any = '--';
        if (hi && hi.statements) {
          for (const tab of ['income', 'balance', 'cash']) {
            if (hi.statements[tab] && hi.statements[tab][k] !== undefined) {
              vali = hi.statements[tab][k];
              break;
            }
          }
        }
        rowData.push(vali);

        if (val0 !== '--' && vali !== '--' && val0 !== null && vali !== null && val0 !== undefined && vali !== undefined) {
          rowData.push({ t: 'n', z: '#,##0.00', f: `${currentExcelCol}${rLabel}-${baseExcelCol}${rLabel}` });
          rowData.push({ t: 'n', z: '0.00%', f: `IFERROR((${currentExcelCol}${rLabel}-${baseExcelCol}${rLabel})/ABS(${baseExcelCol}${rLabel}), "-")` });
        } else {
          rowData.push('--');
          rowData.push('--');
        }
      }
    });
    addRowWithFormat(wsFinComp, rowData);
  });

  colIndex = 2;
  allPeriodsArr.forEach(() => {
    wsFinComp.mergeCells(1, colIndex, 1, colIndex + colsPerPeriod - 1);
    colIndex += colsPerPeriod;
  });

  // Company individual sheets (with YoY)
  results.forEach((res) => {
    const companySheetSuffix = t('excelCompanySheetSuffix');
    const maxBaseLength = Math.max(1, 31 - companySheetSuffix.length - 1);
    const shortName = (res.company_name_localized?.[lang] || res.company_name).substring(0, maxBaseLength);
    const ws = wb.addWorksheet(`${shortName} ${companySheetSuffix}`, { properties: { tabColor: { argb: 'FF9BBB59' } } });

    const allKeys = new Set<string>();
    res.history.forEach((h: any) => {
      if (h.statements) {
        Object.keys(h.statements).forEach(tab => {
          Object.keys(h.statements[tab]).forEach(k => allKeys.add(k));
        });
      }
    });

    const annuals = res.history.filter((h: any) => !h.is_quarterly);
    let hasYoY = false;
    const yoyMap: { yearCode: string, prevYearCode: string, p1: any, p2: any }[] = [];

    if (annuals.length >= 2) {
      hasYoY = true;
      yoyMap.push({
        yearCode: formatPeriodLabel(annuals[0].fiscal_year),
        prevYearCode: formatPeriodLabel(annuals[1].fiscal_year),
        p1: annuals[0],
        p2: annuals[1]
      });
      if (annuals.length >= 3) {
        yoyMap.push({
          yearCode: formatPeriodLabel(annuals[1].fiscal_year),
          prevYearCode: formatPeriodLabel(annuals[2].fiscal_year),
          p1: annuals[1],
          p2: annuals[2]
        });
      }
    }

    const finHeaderRow = [t('itemCol'), ...res.history.map((h: any) => formatPeriodLabel(h.fiscal_year))];
    if (hasYoY) {
      finHeaderRow.push(''); // Spacer column
      yoyMap.forEach(cmp => {
        finHeaderRow.push(`${cmp.yearCode} ${t('varVs')} ${cmp.prevYearCode}`);
        finHeaderRow.push(t('varPct'));
      });
    }
    addRowWithFormat(ws, finHeaderRow);

    const baseColMap: Record<string, string> = {};
    res.history.forEach((h: any, i: number) => {
      baseColMap[h.fiscal_year] = getColName(i + 1);
    });

    Array.from(allKeys).forEach(k => {
      const rowData: (any)[] = [prettifyKey(k, lang)];
      const rLabel = ws.rowCount + 1;

      res.history.forEach((h: any) => {
        let val: any = '--';
        if (h.statements) {
          for (const tab of ['income', 'balance', 'cash']) {
            if (h.statements[tab] && h.statements[tab][k] !== undefined) {
              val = h.statements[tab][k];
              break;
            }
          }
        }
        rowData.push(val);
      });

      if (hasYoY) {
        rowData.push('');
        yoyMap.forEach(cmp => {
          let v1: number | null = null;
          let v2: number | null = null;

          if (cmp.p1.statements) {
            for (const tab of ['income', 'balance', 'cash']) {
              if (cmp.p1.statements[tab] && cmp.p1.statements[tab][k] !== undefined) {
                v1 = cmp.p1.statements[tab][k];
                break;
              }
            }
          }
          if (cmp.p2.statements) {
            for (const tab of ['income', 'balance', 'cash']) {
              if (cmp.p2.statements[tab] && cmp.p2.statements[tab][k] !== undefined) {
                v2 = cmp.p2.statements[tab][k];
                break;
              }
            }
          }

          if (v1 !== null && v2 !== null && v1 !== undefined && v2 !== undefined) {
            const col1 = baseColMap[cmp.p1.fiscal_year];
            const col2 = baseColMap[cmp.p2.fiscal_year];
            rowData.push({ t: 'n', z: '#,##0.00', f: `${col1}${rLabel}-${col2}${rLabel}` });
            rowData.push({ t: 'n', z: '0.00%', f: `IFERROR((${col1}${rLabel}-${col2}${rLabel})/ABS(${col2}${rLabel}), "-")` });
          } else {
            rowData.push('--');
            rowData.push('--');
          }
        });
      }
      addRowWithFormat(ws, rowData);
    });
  });

  const buffer = await wb.xlsx.writeBuffer();
  saveAs(new Blob([buffer]), `RiskLens_MultiCompany_Comparison.xlsx`);
};

import { translateAssessmentText, prettifyKey, getTooltip, translateRatingStatus } from './translations';


function MetricTooltip({ metricKey, label, lang }: { metricKey: string; label: string; lang: Language }) {
  const tip = getTooltip(metricKey, lang);
  if (!tip) return <span className="min-w-0 break-words">{label}</span>;
  return (
    <Tooltip
      content={
        <div className="space-y-1">
          <p>{tip.def}</p>
          {tip.formula && (
            <p className="text-brand-300 font-medium text-[11px] border-t border-white/10 pt-1 mt-1">
              = {tip.formula}
            </p>
          )}
        </div>
      }
    >
      <span className="group inline-flex max-w-full items-start gap-1.5 cursor-help leading-snug">
        <span className="min-w-0 break-words">{label}</span>
        <Info className="mt-0.5 w-3.5 h-3.5 text-brand-500/70 group-hover:text-brand-400 transition-colors flex-shrink-0" />
      </span>
    </Tooltip>
  );
}

function StatementDialog({
  open,
  onClose,
  period,
  companyName,
  ticker,
  currency,
  lang,
  numFormat,
}: {
  open: boolean;
  onClose: () => void;
  period: Period | null;
  companyName: string;
  ticker: string;
  currency: string;
  lang: Language;
  numFormat: 'compact' | 'full';
}) {
  const [tab, setTab] = useState<'income' | 'balance' | 'cash'>('income');
  const yahooUrl = getYahooUrl(ticker);
  const t = getT(lang);
  const STATEMENT_TABS = getStatementTabs(t);
  const isAShare = /^\d{6}(?:\.[A-Z]{2})?$/.test(ticker);
  const statementUiText = {
    lineItem: lang === 'ja' ? '勘定科目' : lang === 'zh-TW' ? '會計科目' : lang === 'zh-CN' ? '会计科目' : 'Line Item',
    period: lang === 'ja' ? '期間' : lang === 'zh-TW' ? '期間' : lang === 'zh-CN' ? '期间' : 'Period',
    currency: lang === 'ja' ? '通貨' : lang === 'zh-TW' ? '幣別' : lang === 'zh-CN' ? '币种' : 'Currency',
    foldHintTitle: lang === 'ja' ? '同義項目の折りたたみ' : lang === 'zh-TW' ? '同義項折疊' : lang === 'zh-CN' ? '同义项折叠' : 'Grouped Folding',
    foldHintBody:
      lang === 'ja'
        ? '同義の会計項目は主項目に統合表示されます。行頭の ▸ をクリックすると内訳を展開できます。'
        : lang === 'zh-TW'
          ? '同義會計項目會聚合到主項目顯示。點擊行首 ▸ 可展開明細。'
          : lang === 'zh-CN'
            ? '同义会计科目会聚合到主项显示。点击行首 ▸ 可展开明细。'
            : 'Synonymous accounting terms are grouped under a primary term. Click ▸ to expand details.',
  };

  // Use full statements data from the API
  const displayData = useMemo<Record<string, number>>(
    () => period?.statements?.[tab] ?? {},
    [period, tab]
  );

  const [expandedAliases, setExpandedAliases] = useState<Record<string, boolean>>({});
  const aliasStateKey = (metricKey: string) => `${tab}:${period?.fiscal_year ?? 'na'}:${metricKey}`;

  const { foldedDisplayData, foldedAliases } = useMemo(() => {
    const entries = Object.entries(displayData) as [string, number][];
    if (entries.length === 0) {
      return {
        foldedDisplayData: {} as Record<string, number>,
        foldedAliases: {} as Record<string, Array<{ key: string; label: string; value: number }>>,
      };
    }

    type Row = {
      key: string;
      value: number;
      normalized: string;
      order: number;
    };

    const normalize = (text: string) =>
      text
        .toLowerCase()
        .replace(/[_/&(),.-]+/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();

    const rows: Row[] = entries.map(([key, value], order) => {
      const englishLabel = prettifyKey(key, 'en');
      return {
        key,
        value,
        normalized: normalize(`${key} ${englishLabel}`),
        order,
      };
    });

    type FamilyRule = {
      id: string;
      patterns: RegExp[];
      priorities: RegExp[];
    };

    const rules: FamilyRule[] = [
      {
        id: 'net_income',
        patterns: [/net income/, /normalized income/, /income available to common/, /continuing ops/, /non controlling/],
        priorities: [/^net income$/i, /net income/, /income available to common/, /normalized income/, /continuing/],
      },
      {
        id: 'ebit_equivalent',
        patterns: [/operating income as reported/, /\bebit\b/, /operating income/],
        priorities: [/^ebit$/i, /operating income as reported/, /operating income/],
      },
      {
        id: 'ebitda',
        patterns: [/\bebitda\b/, /normalized ebitda/],
        priorities: [/^ebitda$/i, /normalized ebitda/],
      },
      {
        id: 'revenue',
        patterns: [/total revenue/, /operating revenue/, /\brevenue\b/],
        priorities: [/^revenue$/i, /total revenue/, /operating revenue/],
      },
      {
        id: 'other_income_expense',
        patterns: [/other income expense/, /other non operating income expenses/],
        priorities: [/^other income expense$/i, /other non operating income expenses/],
      },
      {
        id: 'operating_cash_flow',
        patterns: [/operating cash flow/, /cash flow from continuing operating activities/, /cf from continuing operating activities/, /net cash provided by operating activities/],
        priorities: [/^operating cash flow$/i, /cash flow from continuing operating activities/, /net cash provided by operating activities/],
      },
      {
        id: 'investing_cash_flow',
        patterns: [/investing cash flow/, /cash flow from continuing investing activities/, /cf from continuing investing activities/, /net cash used for investing activities/],
        priorities: [/^investing cash flow$/i, /cash flow from continuing investing activities/, /net cash used for investing activities/],
      },
      {
        id: 'financing_cash_flow',
        patterns: [/financing cash flow/, /cash flow from continuing financing activities/, /cf from continuing financing activities/, /net cash .* financing activities/],
        priorities: [/^financing cash flow$/i, /cash flow from continuing financing activities/, /net cash .* financing activities/],
      },
      {
        id: 'change_payables',
        patterns: [/change in payables accrued expense/, /change in payables/, /change in account payable/, /accrued expense/],
        priorities: [/change in payables accrued expense/, /^change in payables$/i, /change in account payable/],
      },
      {
        id: 'change_receivables',
        patterns: [/changes in account receivables/, /change in receivables/, /change in account receivable/],
        priorities: [/changes in account receivables/, /^change in receivables$/i, /change in account receivable/],
      },
      {
        id: 'depreciation_amortization',
        patterns: [/depreciation amortization depletion/, /depreciation amortization/, /depreciation and amortization/],
        priorities: [/depreciation amortization depletion/, /^depreciation amortization$/i, /depreciation and amortization/],
      },
      {
        id: 'dividends_paid',
        patterns: [/cash dividends paid/, /common stock dividend paid/, /dividend paid/],
        priorities: [/^cash dividends paid$/i, /common stock dividend paid/, /dividend paid/],
      },
      {
        id: 'common_stock_outflow',
        patterns: [/repurchase of capital stock/, /common stock payments/, /purchase of common stock/, /buyback/],
        priorities: [/repurchase of capital stock/, /common stock payments/, /purchase of common stock/],
      },
      {
        id: 'debt_issuance',
        patterns: [/issuance of debt/, /lt debt issuance/, /long term debt issuance/, /short term debt issuance/],
        priorities: [/issuance of debt/, /lt debt issuance/, /long term debt issuance/, /short term debt issuance/],
      },
      {
        id: 'debt_repayment',
        patterns: [/repayment of debt/, /debt repayment/],
        priorities: [/^repayment of debt$/i, /debt repayment/],
      },
      {
        id: 'cash_end_position',
        patterns: [/end cash position/, /cash and cash equivalents end of period/, /cash at end of period/],
        priorities: [/^end cash position$/i, /cash and cash equivalents end of period/, /cash at end of period/],
      },
      {
        id: 'cash_beginning_position',
        patterns: [/beginning cash position/, /cash and cash equivalents beginning of period/, /cash at beginning of period/],
        priorities: [/^beginning cash position$/i, /cash and cash equivalents beginning of period/, /cash at beginning of period/],
      },
      {
        id: 'cash_change',
        patterns: [/changes in cash/, /change in cash and cash equivalents/, /net change in cash/],
        priorities: [/^changes in cash$/i, /change in cash and cash equivalents/, /net change in cash/],
      },
      {
        id: 'capital_expenditure',
        patterns: [/capital expenditure/, /\bcapex\b/, /purchase of ppe/, /purchase of property plant and equipment/],
        priorities: [/^capital expenditure$/i, /\bcapex\b/, /purchase of ppe/, /purchase of property plant and equipment/],
      },
      {
        id: 'total_equity',
        patterns: [/stockholders equity/, /shareholders equity/, /total equity/, /common stock equity/],
        priorities: [/^total equity$/i, /stockholders equity/, /shareholders equity/, /common stock equity/],
      },
      {
        id: 'total_assets',
        patterns: [/total assets/, /assets total/],
        priorities: [/^total assets$/i, /assets total/],
      },
      {
        id: 'total_liabilities',
        patterns: [/total liabilities net minority interest/, /^total liabilities$/],
        priorities: [/^total liabilities$/i, /total liabilities net minority interest/],
      },
      {
        id: 'total_liabilities_equity',
        patterns: [/total liabilities and stockholders equity/, /total liabilities and equity/, /total liabilities equity/],
        priorities: [/total liabilities and stockholders equity/, /total liabilities and equity/, /total liabilities equity/],
      },
      {
        id: 'non_current_deferred_assets',
        patterns: [/non current deferred tax assets/, /non current deferred assets/],
        priorities: [/non current deferred tax assets/, /^non current deferred assets$/i],
      },
      {
        id: 'non_current_deferred_liabilities',
        patterns: [/non current deferred tax liabilities/, /non current deferred liabilities/],
        priorities: [/non current deferred tax liabilities/, /^non current deferred liabilities$/i],
      },
      {
        id: 'current_deferred_liabilities',
        patterns: [/current deferred tax liabilities/, /current deferred liabilities/],
        priorities: [/current deferred tax liabilities/, /^current deferred liabilities$/i],
      },
      {
        id: 'long_term_debt_lease',
        patterns: [
          /long term debt and capital lease obligation/,
          /long term debt & capital lease/,
          /^long term debt$/,
          /long term capital lease obligation/,
        ],
        priorities: [
          /^long term debt$/i,
          /long term debt and capital lease obligation/,
          /long term debt & capital lease/,
          /long term capital lease obligation/,
        ],
      },
      {
        id: 'current_debt_lease',
        patterns: [
          /current debt and capital lease obligation/,
          /current debt & capital lease/,
          /^current debt$/,
          /current portion of long term debt/,
          /current capital lease obligation/,
        ],
        priorities: [
          /^current debt$/i,
          /current debt and capital lease obligation/,
          /current debt & capital lease/,
          /current portion of long term debt/,
          /current capital lease obligation/,
        ],
      },
      {
        id: 'cash_equivalents',
        patterns: [/cash and cash equivalents/, /cash equivalents and short term investments/, /cash cash equivalents and short term investments/],
        priorities: [/^cash and cash equivalents$/i, /cash equivalents and short term investments/, /cash cash equivalents and short term investments/],
      },
    ];

    const getFamilyId = (row: Row): string | null => {
      if (row.normalized.includes('cost of revenue') || row.normalized.includes('reconciled cost of revenue')) return null;
      for (const rule of rules) {
        if (rule.patterns.some((pattern) => pattern.test(row.normalized))) return rule.id;
      }
      return null;
    };

    const scoreRow = (family: string, row: Row): number => {
      const rule = rules.find((item) => item.id === family);
      if (!rule) return 99;
      for (let i = 0; i < rule.priorities.length; i += 1) {
        if (rule.priorities[i].test(row.normalized)) return i;
      }
      return 99;
    };

    const groups = new Map<string, Row[]>();
    const singletons: Row[] = [];
    rows.forEach((row) => {
      const family = getFamilyId(row);
      if (!family) {
        singletons.push(row);
        return;
      }
      // Fold all semantic synonyms in a family; details are preserved in expandable aliases.
      const foldKey = family;
      const bucket = groups.get(foldKey);
      if (bucket) bucket.push(row);
      else groups.set(foldKey, [row]);
    });

    const merged: Array<{
      key: string;
      value: number;
      order: number;
      aliases: Array<{ key: string; label: string; value: number }>;
    }> = [];

    groups.forEach((bucket, foldKey) => {
      const family = foldKey;
      const primary = [...bucket].sort((a, b) => {
        const scoreDiff = scoreRow(family, a) - scoreRow(family, b);
        if (scoreDiff !== 0) return scoreDiff;
        return a.order - b.order;
      })[0];
      const aliases = bucket
        .filter((row) => row.key !== primary.key)
        .sort((a, b) => a.order - b.order)
        .map((row) => ({
          key: row.key,
          label: prettifyKey(row.key, lang),
          value: row.value,
        }));
      merged.push({
        key: primary.key,
        value: primary.value,
        order: Math.min(...bucket.map((row) => row.order)),
        aliases,
      });
    });

    singletons.forEach((row) => {
      merged.push({ key: row.key, value: row.value, order: row.order, aliases: [] });
    });

    merged.sort((a, b) => a.order - b.order);

    const foldedDisplayData: Record<string, number> = {};
    const foldedAliases: Record<string, Array<{ key: string; label: string; value: number }>> = {};
    merged.forEach((row) => {
      foldedDisplayData[row.key] = row.value;
      if (row.aliases.length > 0) foldedAliases[row.key] = row.aliases;
    });

    return { foldedDisplayData, foldedAliases };
  }, [displayData, lang]);

  const tableGroups = useMemo(() => {
    if (Object.entries(foldedDisplayData).length === 0) return null;

    const usedKeys = new Set<string>();
    const groups: { title: string, items: [string, number][] }[] = [];

    const addGroup = (title: string, matchFn: (k: string) => boolean) => {
      const items = Object.entries(foldedDisplayData).filter(([k]) => !usedKeys.has(k) && matchFn(k));
      if (items.length > 0) {
        items.forEach(([k]) => usedKeys.add(k));
        groups.push({ title, items });
      }
    };

    if (tab === 'balance') {
      addGroup(lang === 'en' ? 'Assets' : lang === 'ja' ? '資産' : '资产', k => k.includes('asset') || k.includes('receivable') || k.includes('inventory') || k.includes('property') || k.includes('cash') || k.includes('ppe'));
      addGroup(lang === 'en' ? 'Liabilities' : lang === 'ja' ? '負債' : '负债', k => k.includes('liabilit') || k.includes('debt') || k.includes('payable') || k.includes('lease_obligation'));
      addGroup(lang === 'en' ? 'Equity' : lang === 'ja' ? '資本' : '权益', k => k.includes('equity') || k.includes('stock') || k.includes('retained_earnings'));
    } else if (tab === 'income') {
      addGroup(lang === 'en' ? 'Revenue & Cost' : lang === 'ja' ? '売上と原価' : '收入与成本', k => k.includes('revenue') || k.includes('cost_of') || k.includes('gross_profit') || k.includes('sales'));
      addGroup(lang === 'en' ? 'Operating Expenses' : lang === 'ja' ? '営業費用' : '营业费用', k => k.includes('expense') && !k.includes('interest_expense') && !k.includes('tax'));
      addGroup(lang === 'en' ? 'Profitability' : lang === 'ja' ? '利益' : '利润与收益', k => k.includes('income') || k.includes('ebit') || k.includes('profit') || k.includes('earnings'));
    } else if (tab === 'cash') {
      addGroup(lang === 'en' ? 'Operating Activities' : lang === 'ja' ? '営業活動' : '经营活动', k => k.includes('operating') || k.includes('depreciation') || k.includes('working_capital') || k.includes('receivable') || k.includes('payable') || k.includes('inventory'));
      addGroup(lang === 'en' ? 'Investing Activities' : lang === 'ja' ? '投資活動' : '投资活动', k => k.includes('invest') || k.includes('capital_expenditure'));
      addGroup(lang === 'en' ? 'Financing Activities' : lang === 'ja' ? '財務活動' : '筹资活动', k => k.includes('financing') || k.includes('dividend') || k.includes('debt_issuance') || k.includes('stock_issuance'));
    }

    const otherItems = Object.entries(foldedDisplayData).filter(([k]) => !usedKeys.has(k));
    if (otherItems.length > 0) {
      groups.push({ title: lang === 'en' ? 'Other' : lang === 'ja' ? 'その他' : '其他', items: otherItems });
    }

    return groups;
  }, [foldedDisplayData, tab, lang]);

  if (!period) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="w-[min(1120px,96vw)] max-w-[min(1120px,96vw)] max-h-[92vh] overflow-y-auto glass-panel border border-white/10 shadow-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 flex-wrap">
            <span className="text-2xl font-semibold tracking-tight text-foreground">{companyName}</span>
            <span className="inline-flex items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-1.5">
              <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-semibold">{statementUiText.period}</span>
              <span className="text-sm font-semibold text-foreground">{formatPeriodLabel(period.fiscal_year)}</span>
            </span>
            <span className="inline-flex items-center gap-2 rounded-md border border-border bg-muted/40 px-3 py-1.5">
              <span className="text-[10px] uppercase tracking-[0.12em] text-muted-foreground font-semibold">{statementUiText.currency}</span>
              <span className="text-sm font-semibold text-foreground">{currency}</span>
            </span>
            {isAShare ? (
              <Tooltip content={t('akshareDisclaimer')}>
                <span className="ml-auto flex items-center gap-1 text-xs text-brand-400 font-normal cursor-help">
                  <ExternalLink className="w-3 h-3 opacity-50" />
                  {t('sourceAKShare')}
                </span>
              </Tooltip>
            ) : (
              <a
                href={yahooUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors font-normal"
              >
                <ExternalLink className="w-3 h-3" />
                {t('source')}
              </a>
            )}
          </DialogTitle>
          <DialogDescription className="sr-only">Financial statements for {companyName} {period.fiscal_year}</DialogDescription>
        </DialogHeader>

        {/* Tab bar */}
        <div className="flex gap-1 p-1 rounded-lg bg-muted/30 border border-white/10">
          {STATEMENT_TABS.map(tOption => (
            <button
              key={tOption.key}
              onClick={() => setTab(tOption.key as 'income' | 'balance' | 'cash')}
              className={`flex-1 py-1.5 text-xs font-medium rounded-md transition-colors ${tab === tOption.key
                ? 'bg-brand-600 text-white shadow'
                : 'text-muted-foreground hover:text-foreground'
                }`}
            >
              {tOption.label}
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="mt-2 rounded-md border border-brand-500/20 bg-brand-500/10 px-3 py-2 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground/90 mr-1">{statementUiText.foldHintTitle}:</span>
          <span>{statementUiText.foldHintBody}</span>
        </div>
        <div className="mt-2 rounded-lg border border-white/10 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/20 border-b border-white/10">
                <th className="py-2 px-4 text-left font-medium text-muted-foreground w-[65%]">
                  {statementUiText.lineItem}
                </th>
                <th className="py-2 px-4 text-right font-medium text-muted-foreground">{t('value')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {!tableGroups ? (
                <tr><td colSpan={2} className="py-4 px-4 text-center text-muted-foreground text-xs">{t('noData')}</td></tr>
              ) : (
                tableGroups.map(g => (
                  <Fragment key={g.title}>
                    <tr className="bg-muted/10">
                      <td colSpan={2} className="py-2 px-4 font-bold text-brand-600 dark:text-brand-300 text-xs tracking-wider uppercase">
                        {g.title}
                      </td>
                    </tr>
                    {g.items.map(([k, v]) => {
                      const aliases = foldedAliases[k] ?? [];
                      const expandKey = aliasStateKey(k);
                      const isExpanded = !!expandedAliases[expandKey];

                      return (
                        <Fragment key={k}>
                          <tr className="hover:bg-muted/10 transition-colors">
                            <td className="py-2 pl-6 pr-4 text-muted-foreground align-top">
                              <div className="grid grid-cols-[14px_minmax(0,1fr)] items-start gap-x-2">
                                {aliases.length > 0 ? (
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setExpandedAliases((prev) => ({ ...prev, [expandKey]: !prev[expandKey] }))
                                    }
                                    className="inline-flex h-4 w-[14px] items-center justify-center rounded text-xs text-muted-foreground hover:text-foreground hover:bg-muted/60 mt-0.5"
                                    aria-label={isExpanded ? 'Collapse folded details' : 'Expand folded details'}
                                    title={isExpanded ? 'Collapse folded details' : 'Expand folded details'}
                                  >
                                    {isExpanded ? '▾' : '▸'}
                                  </button>
                                ) : (
                                  <span className="inline-flex h-4 w-[14px] mt-0.5" />
                                )}
                                <div className="min-w-0 flex flex-wrap items-start gap-x-2 gap-y-1">
                                  <MetricTooltip metricKey={k} label={prettifyKey(k, lang)} lang={lang} />
                                  {aliases.length > 0 && (
                                    <span className="inline-flex h-5 items-center rounded-full border border-brand-500/30 bg-brand-500/10 px-2 text-[10px] font-semibold tracking-wide text-brand-300 tabular-nums whitespace-nowrap">
                                      +{aliases.length}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </td>
                            <td className={`py-2 px-4 text-right tabular-nums ${typeof v === 'number' && v < 0 ? 'text-rose-600 dark:text-rose-400 font-medium' : ''}`}>
                              {formatCurrency(typeof v === 'number' ? v : null, numFormat, lang)}
                            </td>
                          </tr>
                          {isExpanded &&
                            aliases.map((alias) => (
                              <tr key={`${k}-${alias.key}`} className="bg-muted/5">
                                <td className="py-1.5 pl-6 pr-4 text-muted-foreground/85 text-xs align-top">
                                  <div className="grid grid-cols-[14px_minmax(0,1fr)] items-start gap-x-2">
                                    <span className="inline-flex h-4 w-[14px]" />
                                    <span className="min-w-0 break-words">↳ {alias.label}</span>
                                  </div>
                                </td>
                                <td className={`py-1.5 px-4 text-right tabular-nums text-xs ${alias.value < 0 ? 'text-rose-600 dark:text-rose-400' : 'text-muted-foreground/90'}`}>
                                  {formatCurrency(alias.value, numFormat, lang)}
                                </td>
                              </tr>
                            ))}
                        </Fragment>
                      );
                    })}
                  </Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function App() {
  const [tickerInput, setTickerInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [data, setData] = useState<AssessmentResponse | null>(null)
  const [lang, setLang] = useState<Language>('en')
  const [colorMode, setColorMode] = useState<ColorMode>(getInitialColorMode)
  const [numFormat, setNumFormat] = useState<'compact' | 'full'>('compact')
  const [activeTheme, setActiveTheme] = useState('monochrome')
  const [themeMenuOpen, setThemeMenuOpen] = useState(false)

  const t = getT(lang)

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedPeriod, setSelectedPeriod] = useState<Period | null>(null)
  const [selectedCompany, setSelectedCompany] = useState('')
  const [selectedTicker, setSelectedTicker] = useState('')
  const [selectedCurrency, setSelectedCurrency] = useState('USD')

  // Keep selected color theme and follow system light/dark mode.
  useEffect(() => {
    const html = document.documentElement;
    if (!THEMES.some((theme) => html.classList.contains(`theme-${theme.id}`))) {
      html.classList.add('theme-monochrome');
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const applyColorMode = (mode: ColorMode) => {
      const shouldUseDark = mode === 'dark' || (mode === 'system' && mediaQuery.matches);
      html.classList.toggle('dark', shouldUseDark);
    };

    applyColorMode(colorMode);
    const handleChange = (event: MediaQueryListEvent) => {
      if (colorMode === 'system') {
        html.classList.toggle('dark', event.matches);
      }
    };
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [colorMode]);

  useEffect(() => {
    window.localStorage.setItem(COLOR_MODE_STORAGE_KEY, colorMode);
  }, [colorMode]);

  const changeTheme = (themeId: string) => {
    const html = document.documentElement;
    THEMES.forEach(t => html.classList.remove(`theme-${t.id}`));
    html.classList.add(`theme-${themeId}`);
    setActiveTheme(themeId);
    setThemeMenuOpen(false);
  }

  const openStatements = (period: Period, companyName: string, ticker: string, currency: string) => {
    setSelectedPeriod(period);
    setSelectedCompany(companyName);
    setSelectedTicker(ticker);
    setSelectedCurrency(currency);
    setDialogOpen(true);
  }

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!tickerInput.trim()) return

    setIsLoading(true)
    setData(null)

    const tickers = tickerInput.split(',').map(t => t.trim()).filter(Boolean)

    try {
      const res = await fetch('/api/v1/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tickers })
      })

      const contentType = res.headers.get('content-type') ?? ''
      let json: any = null

      if (contentType.includes('application/json')) {
        try {
          json = await res.json()
        } catch {
          json = null
        }
      } else {
        const text = await res.text()
        json = text ? { message: text } : null
      }

      if (!res.ok) {
        const detail = json?.detail
        const errors = Array.isArray(detail?.errors)
          ? detail.errors
          : Array.isArray(json?.errors)
            ? json.errors
            : typeof detail === 'string'
              ? [detail]
              : typeof json?.message === 'string'
                ? [json.message]
                : typeof json?.error === 'string'
                  ? [json.error]
                  : [`Request failed (${res.status})`]

        setData({
          errors,
          suggestions: json?.suggestions || detail?.suggestions
        })
      } else {
        if (json && typeof json === 'object') {
          setData(json)
        } else {
          setData({ errors: ['Received empty response from server'] })
        }
      }
    } catch (err) {
      setData({ errors: [err instanceof Error ? err.message : 'Network error'] })
    } finally {
      setIsLoading(false)
    }
  }

  const metricRows = [
    { key: 'operating_income', label: t('ebit'), src: 'raw_metrics', isCurrency: true },
    { key: 'ebitda', label: t('ebitda'), src: 'ratios', isCurrency: true },
    { key: 'total_debt', label: t('totalDebt'), src: 'raw_metrics', isCurrency: true },
    { key: 'debt_to_ebitda', label: t('debtToEbitda'), src: 'ratios', format: 'x' },
    { key: 'interest_coverage', label: t('interestCoverage'), src: 'ratios', format: 'x' },
    { key: 'free_cf', label: t('freeCf'), src: 'raw_metrics', isCurrency: true },
    { key: 'fcf_to_debt', label: t('fcfToDebt'), src: 'ratios', format: '%' },
    { key: 'current_ratio', label: t('currentRatio'), src: 'ratios', format: 'x' },
  ]

  return (
    <TooltipProvider>
      <div className="min-h-screen text-foreground font-sans">
        <header className="dashboard-header">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold text-lg tracking-tight">
              <span><strong className="font-bold text-brand-600 dark:text-brand-400">RiskLens</strong></span>
            </div>
            <div className="flex items-center gap-2 sm:gap-3">
              <div className="flex bg-muted p-1 rounded-md border border-border hidden sm:flex">
                <button
                  onClick={() => setNumFormat('compact')}
                  className={`px-2 py-1 text-[11px] font-semibold rounded-sm transition-all ${numFormat === 'compact' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  B/M
                </button>
                <button
                  onClick={() => setNumFormat('full')}
                  className={`px-2 py-1 text-[11px] font-semibold rounded-sm transition-all ${numFormat === 'full' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  1,000
                </button>
              </div>
              <select
                className="bg-transparent border border-input rounded-md px-2 py-1 text-xs outline-none cursor-pointer h-8 text-muted-foreground focus:text-foreground hover:text-foreground transition-colors"
                value={lang}
                onChange={(e) => setLang(e.target.value as Language)}
              >
                <option value="en" className="bg-background">EN</option>
                <option value="zh-CN" className="bg-background">简中</option>
                <option value="zh-TW" className="bg-background">繁中</option>
                <option value="ja" className="bg-background">日本語</option>
              </select>
              <div className="flex items-center rounded-md border border-input bg-muted/40 p-0.5">
                <button
                  type="button"
                  aria-label="Auto theme"
                  title="Auto"
                  onClick={() => setColorMode('system')}
                  className={`h-7 w-7 rounded flex items-center justify-center transition-colors ${colorMode === 'system'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  <Monitor className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  aria-label="Light theme"
                  title="Light"
                  onClick={() => setColorMode('light')}
                  className={`h-7 w-7 rounded flex items-center justify-center transition-colors ${colorMode === 'light'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  <Sun className="w-3.5 h-3.5" />
                </button>
                <button
                  type="button"
                  aria-label="Dark theme"
                  title="Dark"
                  onClick={() => setColorMode('dark')}
                  className={`h-7 w-7 rounded flex items-center justify-center transition-colors ${colorMode === 'dark'
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  <Moon className="w-3.5 h-3.5" />
                </button>
              </div>
              <div className="relative">
                <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setThemeMenuOpen(!themeMenuOpen)}>
                  <Palette className="w-4 h-4 text-muted-foreground hover:text-brand-500" />
                </Button>
                {themeMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 p-2 bg-popover text-popover-foreground border border-border rounded-md shadow-xl z-50">
                    <p className="px-2 py-1 text-xs font-semibold text-muted-foreground mb-1">{t('themeSelect')}</p>
                    {THEMES.map(tOption => (
                      <button
                        key={tOption.id}
                        onClick={() => changeTheme(tOption.id)}
                        className={`flex items-center w-full gap-3 px-2 py-1.5 rounded-md text-sm hover:bg-muted ${activeTheme === tOption.id ? 'bg-muted font-medium' : ''}`}
                      >
                        <span className={`w-3 h-3 rounded-full ${tOption.color} border border-border`} />
                        {tOption.name[lang] || tOption.name['en']}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="w-full max-w-6xl mx-auto px-4 sm:px-6 py-10 flex flex-col items-center">
          <div className="w-full mb-10 animate-in fade-in duration-500">
            <div className="w-full max-w-3xl mx-auto text-center space-y-3 mb-6">
              <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight text-foreground">{t('title')}</h1>
              <p className="text-muted-foreground text-base md:text-lg">
                {t('subtitle')}
              </p>
            </div>

            <Card className="w-full dashboard-panel bg-white/95 dark:bg-card border-border">
              <CardContent className="p-4">
                <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
                  <div className="relative flex-1">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      value={tickerInput}
                      onChange={(e) => setTickerInput(e.target.value)}
                      placeholder={t('placeholder')}
                      className="pl-9 h-10 text-sm bg-white dark:bg-background border-input placeholder:text-muted-foreground/70 transition-colors focus-visible:ring-brand-500 shadow-sm"
                    />
                  </div>
                  <Button type="submit" disabled={isLoading} className="h-10 px-6 font-medium shadow-sm">
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t('synthesizing')}
                      </>
                    ) : (
                      <>
                        {t('synthesize')}
                        <ArrowRight className="ml-2 w-4 h-4" />
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>

          <div className="w-full space-y-6">
            {data?.results && data.results.length > 1 && (
              <div className="flex justify-end animate-in fade-in slide-in-from-bottom-6">
                <Button onClick={() => exportToExcel(data.results!, t, lang)} className="shadow-md bg-brand-600 hover:bg-brand-500 text-white font-bold tracking-wide">
                  <Download className="mr-2 h-4 w-4" />
                  {t('exportAll')} ({data.results.length})
                </Button>
              </div>
            )}
            {data?.errors && (
              <Card className="dashboard-panel border-rose-500/50 shadow-sm bg-rose-500/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-rose-500">
                    <AlertTriangle className="w-5 h-5" />
                    {t('failed')}
                  </CardTitle>
                  <CardDescription>
                    {data.errors.map((err, i) => <div key={i}>{err}</div>)}
                  </CardDescription>
                </CardHeader>
                {data.suggestions && Object.keys(data.suggestions).length > 0 && (
                  <CardContent>
                    <Separator className="mb-4" />
                    <p className="text-sm font-medium mb-3">{t('didYouMean')}</p>
                    <div className="flex flex-wrap gap-2">
                      {Object.values(data.suggestions).flat().map((s) => (
                        <Button
                          key={s.symbol}
                          variant="secondary"
                          size="sm"
                          onClick={() => setTickerInput(s.symbol)}
                        >
                          <span className="font-bold mr-1">{s.symbol}</span>
                          <span className="text-muted-foreground">{s.name}</span>
                        </Button>
                      ))}
                    </div>
                  </CardContent>
                )}
              </Card>
            )}

            {data?.results?.map((res) => {
              const validHistory = res.history.filter((p: Period) => p.assessment != null);
              const latest = validHistory[0]
              if (!latest) return null;
              const riskScore = typeof latest.assessment.risk_score === 'number' ? latest.assessment.risk_score : null

              const zZone = latest.assessment.overall_rating || 'N/A'
              const isSafe = zZone.includes('(S)')
              const isGrey = zZone.includes('(G)')
              const nameMap = res.company_name_localized || {};
              const localizedName = nameMap[lang] || nameMap['en'] || nameMap['ja'] || res.company_name;

              const uniqueNames = Array.from(new Set([res.company_name, ...Object.values(nameMap)].filter(Boolean)));
              const otherNames = uniqueNames.filter(n => n !== localizedName);
              const hasMultipleNames = otherNames.length > 0;

              return (
                <Card key={res.ticker} className="dashboard-panel overflow-hidden animate-in fade-in duration-500">
                  <CardHeader className="bg-muted/10 border-b py-4">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-3">
                          <div className="flex items-center gap-2">
                            <CardTitle className="text-2xl">{localizedName}</CardTitle>
                            {hasMultipleNames && (
                              <Tooltip content={
                                <div className="text-xs">
                                  <div className="text-muted-foreground mb-1">{t('otherNames')}</div>
                                  {otherNames.map((name, idx) => (
                                    <div key={idx} className="font-medium">{name}</div>
                                  ))}
                                </div>
                              }>
                                <div className="flex items-center justify-center cursor-help">
                                  <Info className="w-4 h-4 text-muted-foreground hover:text-brand-500 transition-colors" />
                                </div>
                              </Tooltip>
                            )}
                          </div>
                          <span className="text-muted-foreground text-sm font-medium bg-muted/30 px-2 py-1 rounded">
                            {res.ticker}
                          </span>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 ml-2 text-muted-foreground hover:text-brand-500 hover:bg-brand-500/10"
                            onClick={() => exportToExcel([res], t, lang)}
                            title="Export to Excel"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      <div className="flex gap-4 p-3 bg-white dark:bg-background/50 rounded-lg shadow-inner border">
                        <div className="flex flex-col items-center px-4 border-r">
                          <div className="text-xs text-muted-foreground font-semibold tracking-wider uppercase">
                            <MetricTooltip metricKey="zscore" label={t('zScore')} lang={lang} />
                          </div>
                          <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold">{riskScore !== null ? riskScore.toFixed(2) : '--'}</span>
                            <span className={`text-sm font-bold ${isSafe ? 'text-emerald-500' : isGrey ? 'text-amber-500' : 'text-rose-500'}`}>
                              [{translateRatingStatus(zZone, lang)}]
                            </span>
                          </div>
                        </div>
                        <div className="flex flex-col items-center px-4">
                          <div className="text-xs text-muted-foreground font-semibold tracking-wider uppercase">
                            <MetricTooltip metricKey="implied_rating" label={t('impliedRating')} lang={lang} />
                          </div>
                          <span className="text-2xl font-bold mt-1">{translateRatingStatus(latest.assessment.implied_rating || zZone.replace(/\s*\(.*\)/, ''), lang)}</span>
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="p-0">
                    <div className="mx-4 mt-4 mb-2 rounded-lg border border-brand-500/30 bg-brand-500/10 px-4 py-3">
                      <div className="flex items-start gap-2">
                        <Info className="mt-0.5 h-4 w-4 text-brand-400 flex-shrink-0" />
                        <div className="space-y-0.5 text-xs sm:text-sm">
                          <p className="font-semibold text-foreground">{t('periodGuideTitle')}</p>
                          <p className="text-muted-foreground">{t('periodGuideBody')}</p>
                        </div>
                      </div>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/40 border-b">
                          <tr>
                            {/* ① Empty header — removed "Metric" label */}
                            <th className="py-2.5 pl-6 pr-4 text-left font-medium text-muted-foreground text-xs uppercase tracking-wider min-w-[12rem]" />
                            {/* column headers — only show valid periods */}
                            {validHistory.map((period, idx) => (
                              <th key={period.fiscal_year} className="py-2.5 px-4 text-right font-medium min-w-[7rem]">
                                <button
                                  onClick={() => openStatements(period, localizedName, res.ticker, res.currency ?? 'USD')}
                                  className={`inline-flex items-center justify-center rounded-full border px-3 py-1.5 text-[11px] font-semibold tracking-wide transition-colors ${idx === 0
                                    ? 'border-brand-500/60 bg-brand-500/15 text-brand-300'
                                    : 'border-border bg-background/80 text-foreground/85 hover:border-brand-500/50 hover:bg-brand-500/10 hover:text-brand-300'
                                    }`}
                                  title={t('periodButtonTitle')}
                                >
                                  {formatPeriodLabel(period.fiscal_year)}
                                </button>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y border-white/5">
                          {metricRows.map((row) => (
                            <tr key={row.key} className="hover:bg-muted/20 even:bg-muted/5 transition-colors text-sm">
                              <td className="py-2.5 pl-6 pr-4 font-medium text-foreground/80">
                                <MetricTooltip metricKey={row.key} label={row.label} lang={lang} />
                              </td>
                              {validHistory.map((period, j) => {
                                const sourceObj = row.src === 'ratios' ? period.ratios : period.raw_metrics;
                                const rawVal = sourceObj ? sourceObj[row.key] : null;
                                const numericVal = typeof rawVal === 'number' ? rawVal : null;

                                let displayVal = '--';
                                if (numericVal !== null) {
                                  if (row.isCurrency) displayVal = formatCurrency(numericVal, numFormat, lang);
                                  else if (row.format === '%') displayVal = (numericVal * 100).toFixed(1) + '%';
                                  else displayVal = numericVal.toFixed(2) + 'x';
                                }

                                return (
                                  <td key={`${row.key}-${j}`} className={`py-2.5 px-4 text-right tabular-nums font-medium ${numericVal !== null && numericVal < 0 ? 'text-rose-600 dark:text-rose-400' : 'text-muted-foreground'}`}>
                                    {displayVal}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x border-t bg-muted/10">
                      <div className="p-4 sm:p-6 space-y-3">
                        <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold text-sm uppercase tracking-wide">
                          <CheckCircle2 className="w-4 h-4" />
                          <h4>{t('strengths')}</h4>
                        </div>
                        <ul className="space-y-2 text-sm">
                          {latest.assessment.strengths.slice(0, 3).map((s, i) => (
                            <li key={i} className="flex items-start gap-2 text-muted-foreground">
                              <span className="min-w-1.5 h-1.5 rounded-full bg-emerald-500/50 mt-1.5" />
                              <span className="leading-relaxed">{translateAssessmentText(s, lang)}</span>
                            </li>
                          ))}
                          {latest.assessment.strengths.length === 0 && (
                            <li className="text-muted-foreground italic">{t('noStrengths')}</li>
                          )}
                        </ul>
                      </div>
                      <div className="p-4 sm:p-6 space-y-3">
                        <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-semibold text-sm uppercase tracking-wide">
                          <AlertTriangle className="w-4 h-4" />
                          <h4>{t('watchItems')}</h4>
                        </div>
                        <ul className="space-y-2 text-sm">
                          {latest.assessment.weaknesses.slice(0, 3).map((w, i) => (
                            <li key={i} className="flex items-start gap-2 text-muted-foreground">
                              <span className="min-w-1.5 h-1.5 rounded-full bg-rose-500/50 mt-1.5" />
                              <span className="leading-relaxed">{translateAssessmentText(w, lang)}</span>
                            </li>
                          ))}
                          {latest.assessment.weaknesses.length === 0 && (
                            <li className="text-muted-foreground italic">{t('noWatchItems')}</li>
                          )}
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </main>

        {/* Financial Statement Dialog */}
        <StatementDialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          period={selectedPeriod}
          companyName={selectedCompany}
          ticker={selectedTicker}
          currency={selectedCurrency}
          lang={lang}
          numFormat={numFormat}
        />
      </div>
    </TooltipProvider>
  )
}
