import { useState, useEffect, Fragment, useMemo } from 'react'
import { Search, Loader2, Moon, Sun, ArrowRight, CheckCircle2, AlertTriangle, ExternalLink, Info, Palette, Download } from 'lucide-react'
import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
    varVs: 'vs',
    varPct: 'Var (%)',
    exportAll: 'Export All',
    finComparisonTab: 'Fin Comparison'
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
    varVs: '对比',
    varPct: '变动比例(%)',
    exportAll: '全部导出',
    finComparisonTab: '财报横向对比'
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
    varVs: '對比',
    varPct: '變動比例(%)',
    exportAll: '全部匯出',
    finComparisonTab: '財報橫向對比'
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
    varVs: '比較',
    varPct: '増減率(%)',
    exportAll: 'すべてエクスポート',
    finComparisonTab: '財務諸表比較'
  }
};

const THEMES = [
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
    let ordA = 'A'.charCodeAt(0);
    let ordZ = 'Z'.charCodeAt(0);
    let len = ordZ - ordA + 1;
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

  if (results.length === 1) {
    // === SINGLE COMPANY LOGIC ===
    const res = results[0];
    const latest = res.history[0];

    const ws1 = wb.addWorksheet(t('mainInfoTab'), { properties: { tabColor: { argb: 'FF4F81BD' } } });

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
    let yoyMap: { yearCode: string, prevYearCode: string, p1: any, p2: any }[] = [];

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

    const ws2 = wb.addWorksheet(t('financialsTab'), { properties: { tabColor: { argb: 'FF9BBB59' } } });

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

  const wsMain = wb.addWorksheet(t('mainInfoTab'), { properties: { tabColor: { argb: 'FF4F81BD' } } });
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
  const wsFinComp = wb.addWorksheet("Financial Comparison", { properties: { tabColor: { argb: 'FF8064A2' } } });

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
    const shortName = (res.company_name_localized?.[lang] || res.company_name).substring(0, 25);
    const ws = wb.addWorksheet(`${shortName} Fin`, { properties: { tabColor: { argb: 'FF9BBB59' } } });

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
    let yoyMap: { yearCode: string, prevYearCode: string, p1: any, p2: any }[] = [];

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
  if (!tip) return <span>{label}</span>;
  return (
    <Tooltip
      content={
        <div className="space-y-1">
          <p>{tip.def}</p>
          {tip.formula && (
            <p className="text-brand-300 font-mono text-[11px] border-t border-white/10 pt-1 mt-1">
              = {tip.formula}
            </p>
          )}
        </div>
      }
    >
      <span className="flex items-center gap-1.5 cursor-help group">
        {label}
        <Info className="w-3.5 h-3.5 text-brand-500/70 group-hover:text-brand-400 transition-colors flex-shrink-0" />
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

  // Use full statements data from the API
  const displayData: Record<string, number> = period?.statements?.[tab] ?? {};

  const tableGroups = useMemo(() => {
    if (Object.entries(displayData).length === 0) return null;

    const usedKeys = new Set<string>();
    const groups: { title: string, items: [string, number][] }[] = [];

    const addGroup = (title: string, matchFn: (k: string) => boolean) => {
      const items = Object.entries(displayData).filter(([k]) => !usedKeys.has(k) && matchFn(k));
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

    const otherItems = Object.entries(displayData).filter(([k]) => !usedKeys.has(k));
    if (otherItems.length > 0) {
      groups.push({ title: lang === 'en' ? 'Other' : lang === 'ja' ? 'その他' : '其他', items: otherItems });
    }

    return groups;
  }, [displayData, tab, lang]);

  if (!period) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto glass-panel border border-white/10 shadow-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3 flex-wrap">
            <span>{companyName}</span>
            <Badge variant="outline" className="font-mono">{formatPeriodLabel(period.fiscal_year)}</Badge>
            {/* Currency badge in header */}
            <Badge className="bg-zinc-700/60 text-zinc-300 border-0 text-[11px] font-mono">
              in {currency}
            </Badge>
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
        <div className="mt-2 rounded-lg border border-white/10 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/20 border-b border-white/10">
                <th className="py-2 px-4 text-left font-medium text-muted-foreground w-1/2" />
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
                    {g.items.map(([k, v]) => (
                      <tr key={k} className="hover:bg-muted/10 transition-colors">
                        <td className="py-2 pl-8 pr-4 text-muted-foreground">
                          <MetricTooltip metricKey={k} label={prettifyKey(k, lang)} lang={lang} />
                        </td>
                        <td className={`py-2 px-4 text-right font-mono tabular-nums ${(v as number) < 0 ? 'text-rose-600 dark:text-rose-400 font-medium' : ''}`}>
                          {formatCurrency(v as number, numFormat, lang)}
                        </td>
                      </tr>
                    ))}
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
  const [isDark, setIsDark] = useState(true)
  const [lang, setLang] = useState<Language>('en')
  const [numFormat, setNumFormat] = useState<'compact' | 'full'>('compact')
  const [activeTheme, setActiveTheme] = useState('celadon')
  const [themeMenuOpen, setThemeMenuOpen] = useState(false)

  const t = getT(lang)

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false)
  const [selectedPeriod, setSelectedPeriod] = useState<Period | null>(null)
  const [selectedCompany, setSelectedCompany] = useState('')
  const [selectedTicker, setSelectedTicker] = useState('')
  const [selectedCurrency, setSelectedCurrency] = useState('USD')

  // Apply default theme on mount
  useEffect(() => {
    document.documentElement.classList.add('theme-celadon');
  }, []);

  const toggleTheme = () => {
    const html = document.documentElement;
    if (isDark) { html.classList.remove('dark'); setIsDark(false); }
    else { html.classList.add('dark'); setIsDark(true); }
  }

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

      const json = await res.json()
      if (!res.ok) {
        setData({
          errors: json.detail?.errors || [json.detail || 'Unknown error'],
          suggestions: json.detail?.suggestions
        })
      } else {
        setData(json)
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
        <header className="glass-header">
          <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold text-lg">
              <span><strong className="font-bold">RiskLens</strong></span>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex bg-muted/40 p-1 rounded-md border border-white/5 backdrop-blur-sm mr-2 hidden sm:flex">
                <button
                  onClick={() => setNumFormat('compact')}
                  className={`px-3 py-1 text-xs font-medium rounded-sm transition-all ${numFormat === 'compact' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  B/M
                </button>
                <button
                  onClick={() => setNumFormat('full')}
                  className={`px-3 py-1 text-xs font-medium rounded-sm transition-all ${numFormat === 'full' ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  1,000
                </button>
              </div>
              <select
                className="bg-transparent border border-white/20 rounded-md px-2 py-1 text-sm outline-none cursor-pointer h-9 text-muted-foreground focus:text-foreground hover:text-foreground transition-colors"
                value={lang}
                onChange={(e) => setLang(e.target.value as Language)}
              >
                <option value="en" className="bg-background">English</option>
                <option value="zh-CN" className="bg-background">简体中文</option>
                <option value="zh-TW" className="bg-background">繁體中文</option>
                <option value="ja" className="bg-background">日本語</option>
              </select>
              <div className="relative">
                <Button variant="ghost" size="icon" onClick={() => setThemeMenuOpen(!themeMenuOpen)}>
                  <Palette className="w-5 h-5 text-brand-400" />
                </Button>
                {themeMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 p-2 bg-popover text-popover-foreground border border-white/20 rounded-md shadow-xl z-50">
                    <p className="px-2 py-1 text-xs font-semibold text-muted-foreground mb-1">{t('themeSelect')}</p>
                    {THEMES.map(tOption => (
                      <button
                        key={tOption.id}
                        onClick={() => changeTheme(tOption.id)}
                        className={`flex items-center w-full gap-3 px-2 py-1.5 rounded-md text-sm hover:bg-muted ${activeTheme === tOption.id ? 'bg-muted font-medium' : ''}`}
                      >
                        <span className={`w-4 h-4 rounded-full ${tOption.color} border border-white/20`} />
                        {tOption.name[lang] || tOption.name['en']}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <Button variant="ghost" size="icon" onClick={toggleTheme}>
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </Button>
            </div>
          </div>
        </header>

        <main className="w-full max-w-7xl mx-auto px-6 py-12 flex flex-col items-center">
          <div className="w-full max-w-xl text-center space-y-4 mb-10">
            <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight">{t('title')}</h1>
            <p className="text-muted-foreground text-lg md:text-xl">
              {t('subtitle')}
            </p>
          </div>

          <Card className="w-full max-w-6xl glass-panel border-white/10 shadow-xl overflow-hidden mb-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <CardContent className="p-6">
              <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <Input
                    value={tickerInput}
                    onChange={(e) => setTickerInput(e.target.value)}
                    placeholder={t('placeholder')}
                    className="pl-10 h-12 text-lg bg-background/50 border-input shadow-inner transition-colors focus-visible:ring-brand-500"
                  />
                </div>
                <Button type="submit" disabled={isLoading} className="h-12 px-8 shadow-md">
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

          <div className="w-full space-y-8">
            {data?.results && data.results.length > 1 && (
              <div className="flex justify-end animate-in fade-in slide-in-from-bottom-6">
                <Button onClick={() => exportToExcel(data.results!, t, lang)} className="shadow-md bg-brand-600 hover:bg-brand-500 text-white font-bold tracking-wide">
                  <Download className="mr-2 h-4 w-4" />
                  {t('exportAll')} ({data.results.length})
                </Button>
              </div>
            )}
            {data?.errors && (
              <Card className="glass-panel border-rose-500/20 shadow-rose-500/10">
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

              const zZone = latest.assessment.overall_rating || 'N/A'
              const isSafe = zZone.includes('(S)')
              const isGrey = zZone.includes('(G)')
              const nameMap = res.company_name_localized || {};
              const localizedName = nameMap[lang] || nameMap['en'] || nameMap['ja'] || res.company_name;

              const uniqueNames = Array.from(new Set([res.company_name, ...Object.values(nameMap)].filter(Boolean)));
              const otherNames = uniqueNames.filter(n => n !== localizedName);
              const hasMultipleNames = otherNames.length > 0;

              return (
                <Card key={res.ticker} className="glass-panel overflow-hidden animate-in fade-in slide-in-from-bottom-8 duration-700 fill-mode-both">
                  <CardHeader className="bg-muted/30 border-b">
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
                          <span className="text-muted-foreground text-sm font-mono tracking-tight font-medium bg-muted/30 px-2 py-1 rounded">
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
                      <div className="flex gap-4 p-3 bg-background/50 rounded-lg shadow-inner border">
                        <div className="flex flex-col items-center px-4 border-r">
                          <div className="text-xs text-muted-foreground font-semibold tracking-wider uppercase">
                            <MetricTooltip metricKey="zscore" label={t('zScore')} lang={lang} />
                          </div>
                          <div className="flex items-baseline gap-2 mt-1">
                            <span className="text-2xl font-bold">{latest.assessment.risk_score.toFixed(2)}</span>
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
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-muted/10 border-b">
                          <tr>
                            {/* ① Empty header — removed "Metric" label */}
                            <th className="py-4 pl-6 pr-4 text-left font-medium text-muted-foreground" />
                            {/* column headers — only show valid periods */}
                            {validHistory.map(period => (
                              <th key={period.fiscal_year} className="py-4 px-4 text-right font-medium">
                                {/* ② Clickable year button redesigned as a highly prominent action pill */}
                                <button
                                  onClick={() => openStatements(period, localizedName, res.ticker, res.currency ?? 'USD')}
                                  className="px-4 py-1.5 rounded-md bg-brand-600 hover:bg-brand-500 text-white shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5 text-sm font-extrabold tracking-wide cursor-pointer ring-1 ring-brand-400/50"
                                  title="Click to view financial statements"
                                >
                                  {/* ③ Reformatted period label */}
                                  {formatPeriodLabel(period.fiscal_year)}
                                </button>
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {metricRows.map((row) => (
                            <tr key={row.key} className="hover:bg-muted/5 transition-colors">
                              <td className="py-3 pl-6 pr-4 font-medium">
                                <MetricTooltip metricKey={row.key} label={row.label} lang={lang} />
                              </td>
                              {validHistory.map((period, j) => {
                                const sourceObj = row.src === 'ratios' ? period.ratios : period.raw_metrics;
                                const rawVal = sourceObj ? sourceObj[row.key] : null;

                                let displayVal = '--';
                                if (rawVal !== null && rawVal !== undefined) {
                                  if (row.isCurrency) displayVal = formatCurrency(rawVal as number, numFormat, lang);
                                  else if (row.format === '%') displayVal = ((rawVal as number) * 100).toFixed(1) + '%';
                                  else displayVal = (rawVal as number).toFixed(2) + 'x';
                                }

                                return (
                                  <td key={`${row.key}-${j}`} className={`py-3 px-4 text-right tabular-nums ${(rawVal as number) < 0 ? 'text-rose-600 dark:text-rose-400 font-medium' : 'text-muted-foreground'}`}>
                                    {displayVal}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x border-t bg-muted/5">
                      <div className="p-6 space-y-4">
                        <div className="flex items-center gap-2 text-emerald-500 font-semibold">
                          <CheckCircle2 className="w-5 h-5" />
                          <h4>{t('strengths')}</h4>
                        </div>
                        <ul className="space-y-2 text-sm">
                          {latest.assessment.strengths.slice(0, 3).map((s, i) => (
                            <li key={i} className="flex gap-2 text-muted-foreground">
                              <span className="min-w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5" />
                              {translateAssessmentText(s, lang)}
                            </li>
                          ))}
                          {latest.assessment.strengths.length === 0 && (
                            <li className="text-muted-foreground italic">{t('noStrengths')}</li>
                          )}
                        </ul>
                      </div>
                      <div className="p-6 space-y-4">
                        <div className="flex items-center gap-2 text-rose-500 font-semibold">
                          <AlertTriangle className="w-5 h-5" />
                          <h4>{t('watchItems')}</h4>
                        </div>
                        <ul className="space-y-2 text-sm">
                          {latest.assessment.weaknesses.slice(0, 3).map((w, i) => (
                            <li key={i} className="flex gap-2 text-muted-foreground">
                              <span className="min-w-1.5 h-1.5 rounded-full bg-rose-500 mt-1.5" />
                              {translateAssessmentText(w, lang)}
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
