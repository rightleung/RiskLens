export type Language = 'en' | 'zh-CN' | 'zh-TW' | 'ja';
export const translateAssessmentText = (text: string, lang: Language): string => {
    if (lang === 'en') return text;
    const translations: Record<string, Record<Language, string>> = {
        // Strengths
        'Low leverage': {
            'en': 'Low leverage', 'zh-CN': '低杠杆', 'zh-TW': '低槓桿', 'ja': '低レバレッジ'
        },
        'Strong interest coverage': {
            'en': 'Strong interest coverage', 'zh-CN': '强劲的利息保障倍数', 'zh-TW': '強勁的利息保障倍數', 'ja': '強固なインタレストカバレッジ'
        },
        'Healthy liquidity position': {
            'en': 'Healthy liquidity position', 'zh-CN': '健康的流动性状况', 'zh-TW': '健康的流動性狀況', 'ja': '健全な流動性ポジション'
        },
        'Healthy liquidity': {
            'en': 'Healthy liquidity', 'zh-CN': '健康的流动性', 'zh-TW': '健康的流動性', 'ja': '健全な流動性'
        },
        'Good liquidity': {
            'en': 'Good liquidity', 'zh-CN': '良好的流动性', 'zh-TW': '良好的流動性', 'ja': '良好な流動性'
        },
        'Strong profitability margins': {
            'en': 'Strong profitability margins', 'zh-CN': '强劲的利润率', 'zh-TW': '強勁的利潤率', 'ja': '強固な利益率'
        },
        'Strong profitability': {
            'en': 'Strong profitability', 'zh-CN': '强劲的盈利能力', 'zh-TW': '強勁的盈利能力', 'ja': '強い収益性'
        },
        'Strong free cash flow generation': {
            'en': 'Strong free cash flow generation', 'zh-CN': '强劲的自由现金流生成', 'zh-TW': '強勁的自由現金流生成', 'ja': '強力なフリーキャッシュフロー創出'
        },
        'Strong free cash flow': {
            'en': 'Strong free cash flow', 'zh-CN': '强劲的自由现金流', 'zh-TW': '強勁的自由現金流', 'ja': '強力なフリーキャッシュフロー'
        },
        'Conservative debt level': {
            'en': 'Conservative debt level', 'zh-CN': '保守的债务水平', 'zh-TW': '保守的債務水平', 'ja': '保守的な負債水準'
        },
        // Weaknesses
        'High financial leverage': {
            'en': 'High financial leverage', 'zh-CN': '高财务杠杆', 'zh-TW': '高財務槓桿', 'ja': '高い財務レバレッジ'
        },
        'High leverage': {
            'en': 'High leverage', 'zh-CN': '高杠杆', 'zh-TW': '高槓桿', 'ja': '高レバレッジ'
        },
        'Weak interest coverage': {
            'en': 'Weak interest coverage', 'zh-CN': '利息保障倍数较弱', 'zh-TW': '利息保障倍數較弱', 'ja': '弱いインタレストカバレッジ'
        },
        'Tight liquidity': {
            'en': 'Tight liquidity', 'zh-CN': '流动性紧张', 'zh-TW': '流動性緊張', 'ja': 'ひっ迫した流動性'
        },
        'Weak liquidity': {
            'en': 'Weak liquidity', 'zh-CN': '流动性较弱', 'zh-TW': '流動性較弱', 'ja': '流動性が弱い'
        },
        'Negative or weak profitability': {
            'en': 'Negative or weak profitability', 'zh-CN': '盈利能力弱或为负', 'zh-TW': '盈利能力弱或為負', 'ja': '収益性がマイナスまたは弱い'
        },
        'Weak profitability': {
            'en': 'Weak profitability', 'zh-CN': '盈利能力较弱', 'zh-TW': '盈利能力較弱', 'ja': '弱い収益性'
        },
        'Negative free cash flow': {
            'en': 'Negative free cash flow', 'zh-CN': '负自由现金流', 'zh-TW': '負自由現金流', 'ja': 'マイナスのフリーキャッシュフロー'
        },
        'Excessive debt burden': {
            'en': 'Excessive debt burden', 'zh-CN': '过度的债务负担', 'zh-TW': '過度的債務負擔', 'ja': '過剰な負債負担'
        },
        'Moderate leverage': {
            'en': 'Moderate leverage', 'zh-CN': '适度杠杆', 'zh-TW': '適度槓桿', 'ja': '適度なレバレッジ'
        },

    };
    // Try exact match first
    if (translations[text] && translations[text][lang]) {
        return translations[text][lang];
    }
    // Try partial match: the assessment text may be like "Low leverage (Debt/EBITDA: 0.7)"
    // We match on the known prefix and keep the parenthetical data portion
    for (const [key, value] of Object.entries(translations)) {
        if (text.toLowerCase().startsWith(key.toLowerCase())) {
            let remainder = text.substring(key.length);
            // Translate embedded metric labels in parenthesis specifically for Chinese/Japanese
            if (lang === 'zh-CN') {
                remainder = remainder.replace('Debt/EBITDA', '债务/EBITDA').replace('Current Ratio', '流动比率').replace('of debt', '占总债务');
            } else if (lang === 'zh-TW') {
                remainder = remainder.replace('Debt/EBITDA', '債務/EBITDA').replace('Current Ratio', '流動比率').replace('of debt', '占總債務');
            } else if (lang === 'ja') {
                remainder = remainder.replace('Debt/EBITDA', '有利子負債/EBITDA').replace('Current Ratio', '流動比率').replace('of debt', '対負債');
            }
            return value[lang] + remainder;
        }
    }
    // Also try substring match for embedded phrases
    for (const [key, value] of Object.entries(translations)) {
        if (text.toLowerCase().includes(key.toLowerCase())) {
            return text.replace(new RegExp(key, 'ig'), value[lang]);
        }
    }
    return text;
};
export const prettifyKey = (key: string, lang: Language): string => {
    const normalizedKey = key.trim().toLowerCase().replace(/[\s_]+/g, '_');
    const dictionary: Record<string, Record<Language, string>> = {
        // ═══ Income Statement ═══
        'total_revenue': {
            'en': 'Total Revenue', 'zh-CN': '总营业收入', 'zh-TW': '總營業收入', 'ja': '総売上高'
        },
        'operating_revenue': {
            'en': 'Operating Revenue', 'zh-CN': '营业收入', 'zh-TW': '營業收入', 'ja': '営業収益'
        },
        'cost_of_revenue': {
            'en': 'Cost of Revenue', 'zh-CN': '营业成本', 'zh-TW': '營業成本', 'ja': '売上原価'
        },
        'gross_profit': {
            'en': 'Gross Profit', 'zh-CN': '毛利润', 'zh-TW': '毛利潤', 'ja': '売上総利益'
        },
        'operating_expense': {
            'en': 'Operating Expense', 'zh-CN': '营业费用', 'zh-TW': '營業費用', 'ja': '営業費用'
        },
        'operating_income': {
            'en': 'Operating Income', 'zh-CN': '营业利润 (EBIT)', 'zh-TW': '營業利潤 (EBIT)', 'ja': '営業利益 (EBIT)'
        },
        'ebit': {
            'en': 'EBIT', 'zh-CN': '息税前利润 (EBIT)', 'zh-TW': '息稅前利潤 (EBIT)', 'ja': 'EBIT (利払前税引前利益)'
        },
        'net_income': {
            'en': 'Net Income', 'zh-CN': '净利润', 'zh-TW': '淨利潤', 'ja': '当期純利益'
        },
        'net_income_continuous_operations': {
            'en': 'Net Income (Continuing Operations)', 'zh-CN': '持续经营净利润', 'zh-TW': '持續經營淨利潤', 'ja': '継続事業純利益'
        },
        'ebitda': {
            'en': 'EBITDA', 'zh-CN': 'EBITDA (息税折旧摊销前利润)', 'zh-TW': 'EBITDA (息稅折舊攤銷前利潤)', 'ja': 'EBITDA'
        },
        'pretax_income': {
            'en': 'Pretax Income', 'zh-CN': '税前利润', 'zh-TW': '稅前利潤', 'ja': '税引前利益'
        },
        'tax_provision': {
            'en': 'Tax Provision', 'zh-CN': '所得税', 'zh-TW': '所得稅', 'ja': '法人税等'
        },
        'net_income_discontinuous_operations': {
            'en': 'Net Income (Discontinued)', 'zh-CN': '终止经营净利润', 'zh-TW': '終止經營淨利潤', 'ja': '非継続事業純利益'
        },
        'net_income_common_stockholders': {
            'en': 'Net Income available to Common', 'zh-CN': '归属普通股股东净利润', 'zh-TW': '歸屬普通股股東淨利潤', 'ja': '普通株主帰属純利益'
        },
        'minority_interests': {
            'en': 'Minority Interests', 'zh-CN': '少数股东损益', 'zh-TW': '少數股東損益', 'ja': '少数株主利益'
        },
        'total_other_income_expense_net': {
            'en': 'Total Other Income/Expense', 'zh-CN': '其他收支净额', 'zh-TW': '其他收支淨額', 'ja': 'その他の収支純額'
        },
        'normalized_ebitda': {
            'en': 'Normalized EBITDA', 'zh-CN': '标准化EBITDA', 'zh-TW': '標準化EBITDA', 'ja': '正規化EBITDA'
        },
        'normalized_income': {
            'en': 'Normalized Income', 'zh-CN': '标准化净利润', 'zh-TW': '標準化淨利潤', 'ja': '正規化純利益'
        },
        'tax_effect_of_unusual_items': {
            'en': 'Tax Effect of Unusual Items', 'zh-CN': '非经常性项目的税收影响', 'zh-TW': '非經常性項目的稅收影響', 'ja': '特別項目の税効果'
        },
        'tax_rate_for_calcs': {
            'en': 'Tax Rate for Calcs', 'zh-CN': '计算用税率', 'zh-TW': '計算用稅率', 'ja': '計算用税率'
        },
        'net_income_from_continuing_operation_net_minority_interest': {
            'en': 'Net Income (Continuing Ops, excl. Minority)', 'zh-CN': '持续经营净利润（不含少数股东权益）', 'zh-TW': '持續經營淨利潤（不含少數股東權益）', 'ja': '継続事業純利益（少数株主利益控除後）'
        },
        'reconciled_depreciation': {
            'en': 'Depreciation & Amortization', 'zh-CN': '折旧与摊销', 'zh-TW': '折舊與攤銷', 'ja': '減価償却費及び償却費'
        },
        'reconciled_cost_of_revenue': {
            'en': 'Reconciled Cost of Revenue', 'zh-CN': '调整后营业成本', 'zh-TW': '調整後營業成本', 'ja': '調整済み売上原価'
        },
        'total_expenses': {
            'en': 'Total Expenses', 'zh-CN': '总费用', 'zh-TW': '總費用', 'ja': '総費用'
        },
        'research_and_development': {
            'en': 'R&D', 'zh-CN': '研发费用', 'zh-TW': '研發費用', 'ja': '研究開発費'
        },
        'total_operating_income_as_reported': {
            'en': 'Operating Income (As Reported)', 'zh-CN': '报告营业利润', 'zh-TW': '報告營業利潤', 'ja': '報告済み営業利益'
        },
        'diluted_average_shares': {
            'en': 'Diluted Average Shares', 'zh-CN': '稀释后平均股数', 'zh-TW': '稀釋後平均股數', 'ja': '希薄化後平均株式数'
        },
        'basic_average_shares': {
            'en': 'Basic Average Shares', 'zh-CN': '基本平均股数', 'zh-TW': '基本平均股數', 'ja': '基本的平均株式数'
        },
        'diluted_eps': {
            'en': 'Diluted EPS', 'zh-CN': '稀释每股收益', 'zh-TW': '稀釋每股收益', 'ja': '希薄化EPS'
        },
        'basic_eps': {
            'en': 'Basic EPS', 'zh-CN': '基本每股收益', 'zh-TW': '基本每股收益', 'ja': '基本EPS'
        },
        'diluted_ni_availto_com_stockholders': {
            'en': 'Diluted NI Avail. to Common Stockholders', 'zh-CN': '归属于普通股东的稀释净利润', 'zh-TW': '歸屬於普通股東的稀釋淨利潤', 'ja': '普通株主帰属希薄化純利益'
        },
        'net_income_including_noncontrolling_interests': {
            'en': 'Net Income (incl. Non-controlling)', 'zh-CN': '净利润（含少数股东损益）', 'zh-TW': '淨利潤（含少數股東損益）', 'ja': '純利益（非支配持分含む）'
        },
        'net_income_from_continuing_and_discontinued_operation': {
            'en': 'Net Income (Continuing & Discontinued)', 'zh-CN': '持续与终止经营净利润', 'zh-TW': '持續與終止經營淨利潤', 'ja': '継続・廃止事業純利益'
        },
        'income_tax_expense': {
            'en': 'Income Tax Expense', 'zh-CN': '所得税费用', 'zh-TW': '所得稅費用', 'ja': '法人税等(所得税費用)'
        },
        'income_before_tax': {
            'en': 'Income Before Tax', 'zh-CN': '税前利润', 'zh-TW': '稅前利潤', 'ja': '税引前利益'
        },
        'other_income_expense': {
            'en': 'Other Income/Expense', 'zh-CN': '其他收入/支出', 'zh-TW': '其他收入/支出', 'ja': 'その他の収益/費用'
        },
        'other_non_operating_income_expenses': {
            'en': 'Other Non-operating Income/Expenses', 'zh-CN': '其他营业外收支', 'zh-TW': '其他營業外收支', 'ja': 'その他の営業外収益/費用'
        },
        'interest_income': {
            'en': 'Interest Income', 'zh-CN': '利息收入', 'zh-TW': '利息收入', 'ja': '受取利息'
        },
        'interest_income_non_operating': {
            'en': 'Interest Income (Non-operating)', 'zh-CN': '营业外利息收入', 'zh-TW': '營業外利息收入', 'ja': '営業外受取利息'
        },
        'interest_expense': {
            'en': 'Interest Expense', 'zh-CN': '利息费用', 'zh-TW': '利息費用', 'ja': '支払利息'
        },
        'interest_expense_non_operating': {
            'en': 'Interest Expense (Non-operating)', 'zh-CN': '营业外利息费用', 'zh-TW': '營業外利息費用', 'ja': '営業外支払利息'
        },
        'net_interest_income': {
            'en': 'Net Interest Income', 'zh-CN': '净利息收入', 'zh-TW': '淨利息收入', 'ja': '純受取利息'
        },
        'net_non_operating_interest_income_expense': {
            'en': 'Net Non-operating Interest Income/Expense', 'zh-CN': '营业外净利息收支', 'zh-TW': '營業外淨利息收支', 'ja': '営業外純利息収支'
        },
        'depreciation_and_amortization_in_income_statement': {
            'en': 'Depreciation & Amortization', 'zh-CN': '折旧与摊销', 'zh-TW': '折舊與攤銷', 'ja': '減価償却費及び償却費'
        },
        'special_income_charges': {
            'en': 'Special Income/Charges', 'zh-CN': '特殊收益/费用', 'zh-TW': '特殊收益/費用', 'ja': '特別利益/損失'
        },
        'restructuring_and_mergern_acquisition': {
            'en': 'Restructuring & M&A', 'zh-CN': '重组及并购费用', 'zh-TW': '重組及併購費用', 'ja': 'リストラ・M&A費用'
        },
        'other_operating_expenses': {
            'en': 'Other Operating Expenses', 'zh-CN': '其他营业费用', 'zh-TW': '其他營業費用', 'ja': 'その他の営業費用'
        },
        // ═══ Balance Sheet ═══
        'cash_and_equivalents': {
            'en': 'Cash & Equivalents', 'zh-CN': '现金及等价物', 'zh-TW': '現金及等價物', 'ja': '現金及び現金同等物'
        },
        'cash_financial': {
            'en': 'Cash', 'zh-CN': '现金', 'zh-TW': '現金', 'ja': '現金'
        },
        'cash_and_cash_equivalents': {
            'en': 'Cash & Cash Equivalents', 'zh-CN': '现金及现金等价物', 'zh-TW': '現金及現金等價物', 'ja': '現金及び現金同等物'
        },
        'cash_cash_equivalents_and_short_term_investments': {
            'en': 'Cash, Equivalents & Short Term Investments', 'zh-CN': '现金、等价物及短期投资', 'zh-TW': '現金、等價物及短期投資', 'ja': '現金同等物及び短期投資'
        },
        'other_short_term_investments': {
            'en': 'Other Short Term Investments', 'zh-CN': '其他短期投资', 'zh-TW': '其他短期投資', 'ja': 'その他の短期投資'
        },
        'accounts_receivable': {
            'en': 'Accounts Receivable', 'zh-CN': '应收账款', 'zh-TW': '應收帳款', 'ja': '売掛金'
        },
        'receivables': {
            'en': 'Receivables', 'zh-CN': '应收款项', 'zh-TW': '應收款項', 'ja': '受取手形及び売掛金'
        },
        'inventory': {
            'en': 'Inventory', 'zh-CN': '存货', 'zh-TW': '存貨', 'ja': '棚卸資産'
        },
        'other_current_assets': {
            'en': 'Other Current Assets', 'zh-CN': '其他流动资产', 'zh-TW': '其他流動資產', 'ja': 'その他の流動資産'
        },
        'total_current_assets': {
            'en': 'Total Current Assets', 'zh-CN': '流动资产合计', 'zh-TW': '流動資產合計', 'ja': '流動資産合計'
        },
        'net_ppe': {
            'en': 'Net PP&E', 'zh-CN': '固定资产净额', 'zh-TW': '固定資產淨額', 'ja': '有形固定資産（純額）'
        },
        'gross_ppe': {
            'en': 'Gross PP&E', 'zh-CN': '固定资产总额', 'zh-TW': '固定資產總額', 'ja': '有形固定資産（総額）'
        },
        'accumulated_depreciation': {
            'en': 'Accumulated Depreciation', 'zh-CN': '累计折旧', 'zh-TW': '累計折舊', 'ja': '減価償却累計額'
        },
        'goodwill': {
            'en': 'Goodwill', 'zh-CN': '商誉', 'zh-TW': '商譽', 'ja': 'のれん'
        },
        'goodwill_and_other_intangible_assets': {
            'en': 'Goodwill & Intangible Assets', 'zh-CN': '商誉及无形资产', 'zh-TW': '商譽及無形資產', 'ja': 'のれん及び無形資産'
        },
        'other_intangible_assets': {
            'en': 'Other Intangible Assets', 'zh-CN': '其他无形资产', 'zh-TW': '其他無形資產', 'ja': 'その他の無形資産'
        },
        'investments_and_advances': {
            'en': 'Investments & Advances', 'zh-CN': '投资及垫款', 'zh-TW': '投資及墊款', 'ja': '投資及び貸付金'
        },
        'long_term_equity_investment': {
            'en': 'Long Term Equity Investment', 'zh-CN': '长期股权投资', 'zh-TW': '長期股權投資', 'ja': '長期株式投資'
        },
        'other_non_current_assets': {
            'en': 'Other Non-current Assets', 'zh-CN': '其他非流动资产', 'zh-TW': '其他非流動資產', 'ja': 'その他の固定資産'
        },
        'total_non_current_assets': {
            'en': 'Total Non-current Assets', 'zh-CN': '非流动资产合计', 'zh-TW': '非流動資產合計', 'ja': '固定資産合計'
        },
        'total_assets': {
            'en': 'Total Assets', 'zh-CN': '总资产', 'zh-TW': '總資產', 'ja': '総資産'
        },
        'accounts_payable': {
            'en': 'Accounts Payable', 'zh-CN': '应付账款', 'zh-TW': '應付帳款', 'ja': '買掛金'
        },
        'payables': {
            'en': 'Payables', 'zh-CN': '应付款项', 'zh-TW': '應付款項', 'ja': '支払手形及び買掛金'
        },
        'payables_and_accrued_expenses': {
            'en': 'Payables & Accrued Expenses', 'zh-CN': '应付账款及应计费用', 'zh-TW': '應付帳款及應計費用', 'ja': '買掛金及び未払費用'
        },
        'current_debt': {
            'en': 'Current Debt', 'zh-CN': '短期借款', 'zh-TW': '短期借款', 'ja': '短期借入金'
        },
        'current_debt_and_capital_lease_obligation': {
            'en': 'Current Debt & Capital Lease', 'zh-CN': '短期债务及资本租赁', 'zh-TW': '短期債務及資本租賃', 'ja': '短期借入金及びリース債務'
        },
        'other_current_liabilities': {
            'en': 'Other Current Liabilities', 'zh-CN': '其他流动负债', 'zh-TW': '其他流動負債', 'ja': 'その他の流動負債'
        },
        'current_liabilities': {
            'en': 'Current Liabilities', 'zh-CN': '流动负债合计', 'zh-TW': '流動負債合計', 'ja': '流動負債合計'
        },
        'total_current_liabilities': {
            'en': 'Total Current Liabilities', 'zh-CN': '流动负债合计', 'zh-TW': '流動負債合計', 'ja': '流動負債合計'
        },
        'long_term_debt': {
            'en': 'Long Term Debt', 'zh-CN': '长期借款', 'zh-TW': '長期借款', 'ja': '長期借入金'
        },
        'long_term_debt_and_capital_lease_obligation': {
            'en': 'Long Term Debt & Capital Lease', 'zh-CN': '长期债务及资本租赁', 'zh-TW': '長期債務及資本租賃', 'ja': '長期借入金及びリース債務'
        },
        'long_term_capital_lease_obligation': {
            'en': 'Long Term Capital Lease', 'zh-CN': '长期资本租赁', 'zh-TW': '長期資本租賃', 'ja': '長期リース債務'
        },
        'other_non_current_liabilities': {
            'en': 'Other Non-current Liabilities', 'zh-CN': '其他非流动负债', 'zh-TW': '其他非流動負債', 'ja': 'その他の固定負債'
        },
        'total_non_current_liabilities_net_minority_interest': {
            'en': 'Total Non-current Liabilities', 'zh-CN': '非流动负债合计', 'zh-TW': '非流動負債合計', 'ja': '固定負債合計'
        },
        'total_liabilities_net_minority_interest': {
            'en': 'Total Liabilities', 'zh-CN': '总负债', 'zh-TW': '總負債', 'ja': '総負債'
        },
        'total_liabilities': {
            'en': 'Total Liabilities', 'zh-CN': '总负债', 'zh-TW': '總負債', 'ja': '総負債'
        },
        'total_debt': {
            'en': 'Total Debt', 'zh-CN': '总债务', 'zh-TW': '總債務', 'ja': '総有利子負債'
        },
        'net_debt': {
            'en': 'Net Debt', 'zh-CN': '净债务', 'zh-TW': '淨債務', 'ja': '純有利子負債'
        },
        'stockholders_equity': {
            'en': "Stockholders' Equity", 'zh-CN': '股东权益', 'zh-TW': '股東權益', 'ja': '株主資本'
        },
        'total_equity_gross_minority_interest': {
            'en': 'Total Equity (incl. Minority)', 'zh-CN': '所有者权益合计（含少数股东）', 'zh-TW': '所有者權益合計（含少數股東）', 'ja': '資本合計（少数株主含む）'
        },
        'minority_interest': {
            'en': 'Minority Interest', 'zh-CN': '少数股东权益', 'zh-TW': '少數股東權益', 'ja': '少数株主持分'
        },
        'retained_earnings': {
            'en': 'Retained Earnings', 'zh-CN': '留存收益', 'zh-TW': '保留盈餘', 'ja': '利益剰余金'
        },
        'common_stock': {
            'en': 'Common Stock', 'zh-CN': '普通股', 'zh-TW': '普通股', 'ja': '普通株式'
        },
        'common_stock_equity': {
            'en': 'Common Stock Equity', 'zh-CN': '普通股权益', 'zh-TW': '普通股權益', 'ja': '普通株主持分'
        },
        'capital_stock': {
            'en': 'Capital Stock', 'zh-CN': '股本', 'zh-TW': '股本', 'ja': '資本金'
        },
        'share_issued': {
            'en': 'Shares Issued', 'zh-CN': '已发行股数', 'zh-TW': '已發行股數', 'ja': '発行済株式数'
        },
        'ordinary_shares_number': {
            'en': 'Ordinary Shares Number', 'zh-CN': '普通股数', 'zh-TW': '普通股數', 'ja': '普通株式数'
        },
        'treasury_shares_number': {
            'en': 'Treasury Shares', 'zh-CN': '库存股数', 'zh-TW': '庫存股數', 'ja': '自己株式数'
        },
        'treasury_stock': {
            'en': 'Treasury Stock', 'zh-CN': '库存股', 'zh-TW': '庫存股', 'ja': '自己株式'
        },
        'additional_paid_in_capital': {
            'en': 'Additional Paid-in Capital', 'zh-CN': '资本公积', 'zh-TW': '資本公積', 'ja': '資本剰余金'
        },
        'other_equity_adjustments': {
            'en': 'Other Equity Adjustments', 'zh-CN': '其他权益调整', 'zh-TW': '其他權益調整', 'ja': 'その他の資本調整'
        },
        'gains_losses_not_affecting_retained_earnings': {
            'en': 'Gains/Losses Not Affecting Retained Earnings', 'zh-CN': '不影响留存收益的利得/损失', 'zh-TW': '不影響保留盈餘的利得/損失', 'ja': '利益剰余金に影響しない損益'
        },
        'tangible_book_value': {
            'en': 'Tangible Book Value', 'zh-CN': '有形净资产', 'zh-TW': '有形淨資產', 'ja': '有形純資産'
        },
        'total_capitalization': {
            'en': 'Total Capitalization', 'zh-CN': '总资本', 'zh-TW': '總資本', 'ja': '総資本'
        },
        'invested_capital': {
            'en': 'Invested Capital', 'zh-CN': '投入资本', 'zh-TW': '投入資本', 'ja': '投下資本'
        },
        'working_capital': {
            'en': 'Working Capital', 'zh-CN': '营运资本', 'zh-TW': '營運資本', 'ja': '運転資本'
        },
        'net_tangible_assets': {
            'en': 'Net Tangible Assets', 'zh-CN': '有形资产净额', 'zh-TW': '有形資產淨額', 'ja': '有形資産（純額）'
        },
        // ═══ Cash Flow Statement ═══
        'operating_cash_flow': {
            'en': 'Operating Cash Flow', 'zh-CN': '经营活动现金流', 'zh-TW': '經營活動現金流', 'ja': '営業活動によるキャッシュフロー'
        },
        'investing_cash_flow': {
            'en': 'Investing Cash Flow', 'zh-CN': '投资活动现金流', 'zh-TW': '投資活動現金流', 'ja': '投資活動によるキャッシュフロー'
        },
        'financing_cash_flow': {
            'en': 'Financing Cash Flow', 'zh-CN': '筹资活动现金流', 'zh-TW': '籌資活動現金流', 'ja': '財務活動によるキャッシュフロー'
        },
        'capital_expenditure': {
            'en': 'Capital Expenditure', 'zh-CN': '资本支出 (CapEx)', 'zh-TW': '資本支出 (CapEx)', 'ja': '資本的支出 (CapEx)'
        },
        'free_cash_flow': {
            'en': 'Free Cash Flow', 'zh-CN': '自由现金流', 'zh-TW': '自由現金流', 'ja': 'フリーキャッシュフロー'
        },
        'depreciation_and_amortization': {
            'en': 'Depreciation & Amortization', 'zh-CN': '折旧与摊销', 'zh-TW': '折舊與攤銷', 'ja': '減価償却費及び償却費'
        },
        'depreciation_amortization_depletion': {
            'en': 'Depreciation, Amortization & Depletion', 'zh-CN': '折旧、摊销及资源耗减', 'zh-TW': '折舊、攤銷及資源耗減', 'ja': '減価償却費・償却費・減耗'
        },
        'stock_based_compensation': {
            'en': 'Stock Based Compensation', 'zh-CN': '股份支付费用', 'zh-TW': '股份支付費用', 'ja': '株式報酬費用'
        },
        'change_in_working_capital': {
            'en': 'Change in Working Capital', 'zh-CN': '营运资本变动', 'zh-TW': '營運資本變動', 'ja': '運転資本の変動'
        },
        'change_in_receivables': {
            'en': 'Change in Receivables', 'zh-CN': '应收账款变动', 'zh-TW': '應收帳款變動', 'ja': '売掛金の変動'
        },
        'change_in_inventory': {
            'en': 'Change in Inventory', 'zh-CN': '存货变动', 'zh-TW': '存貨變動', 'ja': '棚卸資産の変動'
        },
        'change_in_payable': {
            'en': 'Change in Payables', 'zh-CN': '应付账款变动', 'zh-TW': '應付帳款變動', 'ja': '買掛金の変動'
        },
        'change_in_payables_and_accrued_expense': {
            'en': 'Change in Payables & Accrued Expense', 'zh-CN': '应付及应计费用变动', 'zh-TW': '應付及應計費用變動', 'ja': '買掛金・未払費用の変動'
        },
        'change_in_other_current_assets': {
            'en': 'Change in Other Current Assets', 'zh-CN': '其他流动资产变动', 'zh-TW': '其他流動資產變動', 'ja': 'その他流動資産の変動'
        },
        'change_in_other_current_liabilities': {
            'en': 'Change in Other Current Liabilities', 'zh-CN': '其他流动负债变动', 'zh-TW': '其他流動負債變動', 'ja': 'その他流動負債の変動'
        },
        'deferred_income_tax': {
            'en': 'Deferred Income Tax', 'zh-CN': '递延所得税', 'zh-TW': '遞延所得稅', 'ja': '繰延税金'
        },
        'deferred_tax': {
            'en': 'Deferred Tax', 'zh-CN': '递延税款', 'zh-TW': '遞延稅款', 'ja': '繰延税金'
        },
        'other_non_cash_items': {
            'en': 'Other Non-cash Items', 'zh-CN': '其他非现金项目', 'zh-TW': '其他非現金項目', 'ja': 'その他の非資金項目'
        },
        'purchase_of_investment': {
            'en': 'Purchase of Investment', 'zh-CN': '投资购买', 'zh-TW': '投資購買', 'ja': '投資の取得'
        },
        'sale_of_investment': {
            'en': 'Sale of Investment', 'zh-CN': '投资出售', 'zh-TW': '投資出售', 'ja': '投資の売却'
        },
        'purchase_of_business': {
            'en': 'Purchase of Business', 'zh-CN': '企业并购', 'zh-TW': '企業併購', 'ja': '事業の取得'
        },
        'net_ppe_purchase_and_sale': {
            'en': 'Net PP&E Purchase & Sale', 'zh-CN': '固定资产净购销', 'zh-TW': '固定資產淨購銷', 'ja': '有形固定資産の取得・売却（純額）'
        },
        'purchase_of_ppe': {
            'en': 'Purchase of PP&E', 'zh-CN': '购置固定资产', 'zh-TW': '購置固定資產', 'ja': '有形固定資産の取得'
        },
        'net_investment_purchase_and_sale': {
            'en': 'Net Investment Purchase & Sale', 'zh-CN': '净投资购销', 'zh-TW': '淨投資購銷', 'ja': '投資の取得・売却（純額）'
        },
        'net_issuance_payments_of_debt': {
            'en': 'Net Issuance/Payments of Debt', 'zh-CN': '债务发行/偿还净额', 'zh-TW': '債務發行/償還淨額', 'ja': '有利子負債の発行・返済（純額）'
        },
        'issuance_of_debt': {
            'en': 'Issuance of Debt', 'zh-CN': '债务发行', 'zh-TW': '債務發行', 'ja': '有利子負債の発行'
        },
        'repayment_of_debt': {
            'en': 'Repayment of Debt', 'zh-CN': '债务偿还', 'zh-TW': '債務償還', 'ja': '有利子負債の返済'
        },
        'long_term_debt_issuance': {
            'en': 'LT Debt Issuance', 'zh-CN': '长期债务发行', 'zh-TW': '長期債務發行', 'ja': '長期借入金の調達'
        },
        'long_term_debt_payments': {
            'en': 'LT Debt Payments', 'zh-CN': '长期债务偿还', 'zh-TW': '長期債務償還', 'ja': '長期借入金の返済'
        },
        'short_term_debt_issuance': {
            'en': 'ST Debt Issuance', 'zh-CN': '短期债务发行', 'zh-TW': '短期債務發行', 'ja': '短期借入金の調達'
        },
        'short_term_debt_payments': {
            'en': 'ST Debt Payments', 'zh-CN': '短期债务偿还', 'zh-TW': '短期債務償還', 'ja': '短期借入金の返済'
        },
        'common_stock_issuance': {
            'en': 'Common Stock Issuance', 'zh-CN': '普通股发行', 'zh-TW': '普通股發行', 'ja': '普通株式の発行'
        },
        'common_stock_payments': {
            'en': 'Common Stock Payments', 'zh-CN': '普通股回购', 'zh-TW': '普通股回購', 'ja': '自己株式の取得'
        },
        'net_common_stock_issuance': {
            'en': 'Net Common Stock Issuance', 'zh-CN': '普通股净发行', 'zh-TW': '普通股淨發行', 'ja': '普通株式の発行（純額）'
        },
        'common_stock_dividend_paid': {
            'en': 'Common Stock Dividend Paid', 'zh-CN': '普通股股利支付', 'zh-TW': '普通股股利支付', 'ja': '普通株式配当金の支払'
        },
        'cash_dividends_paid': {
            'en': 'Cash Dividends Paid', 'zh-CN': '现金股利支付', 'zh-TW': '現金股利支付', 'ja': '配当金の支払'
        },
        'repurchase_of_capital_stock': {
            'en': 'Repurchase of Capital Stock', 'zh-CN': '股票回购', 'zh-TW': '股票回購', 'ja': '自己株式の取得'
        },
        'end_cash_position': {
            'en': 'End Cash Position', 'zh-CN': '期末现金余额', 'zh-TW': '期末現金餘額', 'ja': '期末現金残高'
        },
        'beginning_cash_position': {
            'en': 'Beginning Cash Position', 'zh-CN': '期初现金余额', 'zh-TW': '期初現金餘額', 'ja': '期首現金残高'
        },
        'changes_in_cash': {
            'en': 'Changes in Cash', 'zh-CN': '现金变动', 'zh-TW': '現金變動', 'ja': '現金の増減'
        },
        'effect_of_exchange_rate_changes': {
            'en': 'Effect of Exchange Rate Changes', 'zh-CN': '汇率变动影响', 'zh-TW': '匯率變動影響', 'ja': '為替変動の影響'
        },
        // ═══ Missing Balance Sheet Items ═══
        'available_for_sale_securities': {
            'en': 'Available for Sale Securities', 'zh-CN': '可供出售金融资产', 'zh-TW': '可供出售金融資產', 'ja': '売却可能有価証券'
        },
        'capital_lease_obligations': {
            'en': 'Capital Lease Obligations', 'zh-CN': '融资租赁负债', 'zh-TW': '融資租賃負債', 'ja': 'ファイナンスリース債務'
        },
        'cash_equivalents': {
            'en': 'Cash Equivalents', 'zh-CN': '现金等价物', 'zh-TW': '現金等價物', 'ja': '現金同等物'
        },
        'current_accrued_expenses': {
            'en': 'Current Accrued Expenses', 'zh-CN': '应计费用', 'zh-TW': '應計費用', 'ja': '未払費用'
        },
        'current_capital_lease_obligation': {
            'en': 'Current Capital Lease Obligation', 'zh-CN': '一年内到期融资租赁负债', 'zh-TW': '一年內到期融資租賃負債', 'ja': '短期リース債務'
        },
        'current_deferred_liabilities': {
            'en': 'Current Deferred Liabilities', 'zh-CN': '流动递延负债', 'zh-TW': '流動遞延負債', 'ja': '流動繰延負債'
        },
        'current_deferred_revenue': {
            'en': 'Current Deferred Revenue', 'zh-CN': '流动递延收入', 'zh-TW': '流動遞延收入', 'ja': '流動繰延収益'
        },
        'income_tax_payable': {
            'en': 'Income Tax Payable', 'zh-CN': '应交所得税', 'zh-TW': '應交所得稅', 'ja': '未払法人税等'
        },
        'total_tax_payable': {
            'en': 'Total Tax Payable', 'zh-CN': '应交税费合计', 'zh-TW': '應交稅費合計', 'ja': '未払税金合計'
        },
        'investmentin_financial_assets': {
            'en': 'Investment in Financial Assets', 'zh-CN': '金融资产投资', 'zh-TW': '金融資產投資', 'ja': '金融資産投資'
        },
        'land_and_improvements': {
            'en': 'Land & Improvements', 'zh-CN': '土地及改良', 'zh-TW': '土地及改良', 'ja': '土地及び土地改良'
        },
        'leases': {
            'en': 'Leases', 'zh-CN': '租赁', 'zh-TW': '租賃', 'ja': 'リース'
        },
        'machinery_furniture_equipment': {
            'en': 'Machinery, Furniture & Equipment', 'zh-CN': '机器设备及家具', 'zh-TW': '機器設備及傢具', 'ja': '機械装置・器具備品'
        },
        'non_current_deferred_assets': {
            'en': 'Non-current Deferred Assets', 'zh-CN': '非流动递延资产', 'zh-TW': '非流動遞延資產', 'ja': '固定繰延資産'
        },
        'non_current_deferred_taxes_assets': {
            'en': 'Non-current Deferred Tax Assets', 'zh-CN': '非流动递延所得税资产', 'zh-TW': '非流動遞延所得稅資產', 'ja': '固定繰延税金資産'
        },
        'other_current_borrowings': {
            'en': 'Other Current Borrowings', 'zh-CN': '其他短期借款', 'zh-TW': '其他短期借款', 'ja': 'その他の短期借入金'
        },
        'other_investments': {
            'en': 'Other Investments', 'zh-CN': '其他投资', 'zh-TW': '其他投資', 'ja': 'その他の投資'
        },
        'other_properties': {
            'en': 'Other Properties', 'zh-CN': '其他物业', 'zh-TW': '其他物業', 'ja': 'その他の不動産'
        },
        'other_receivables': {
            'en': 'Other Receivables', 'zh-CN': '其他应收款', 'zh-TW': '其他應收款', 'ja': 'その他の債権'
        },
        'properties': {
            'en': 'Properties', 'zh-CN': '物业', 'zh-TW': '物業', 'ja': '不動産'
        },
        'tradeand_other_payables_non_current': {
            'en': 'Trade & Other Payables (Non-current)', 'zh-CN': '长期应付款及其他', 'zh-TW': '長期應付款及其他', 'ja': '長期買掛金・その他'
        },
        'commercial_paper': {
            'en': 'Commercial Paper', 'zh-CN': '商业票据', 'zh-TW': '商業票據', 'ja': 'コマーシャルペーパー'
        },
        // ═══ Missing Cash Flow Items ═══
        'cash_flow_from_continuing_financing_activities': {
            'en': 'CF from Continuing Financing Activities', 'zh-CN': '持续经营筹资活动现金流', 'zh-TW': '持續經營籌資活動現金流', 'ja': '継続事業の財務活動によるCF'
        },
        'cash_flow_from_continuing_investing_activities': {
            'en': 'CF from Continuing Investing Activities', 'zh-CN': '持续经营投资活动现金流', 'zh-TW': '持續經營投資活動現金流', 'ja': '継続事業の投資活動によるCF'
        },
        'cash_flow_from_continuing_operating_activities': {
            'en': 'CF from Continuing Operating Activities', 'zh-CN': '持续经营活动现金流', 'zh-TW': '持續經營活動現金流', 'ja': '継続事業の営業活動によるCF'
        },
        'change_in_account_payable': {
            'en': 'Change in Account Payable', 'zh-CN': '应付账款变动', 'zh-TW': '應付帳款變動', 'ja': '買掛金の変動'
        },
        'change_in_other_working_capital': {
            'en': 'Change in Other Working Capital', 'zh-CN': '其他营运资本变动', 'zh-TW': '其他營運資本變動', 'ja': 'その他運転資本の変動'
        },
        'changes_in_account_receivables': {
            'en': 'Changes in Account Receivables', 'zh-CN': '应收账款变动', 'zh-TW': '應收帳款變動', 'ja': '売掛金の変動'
        },
        'income_tax_paid_supplemental_data': {
            'en': 'Income Tax Paid (Supplemental)', 'zh-CN': '已付所得税（补充数据）', 'zh-TW': '已付所得稅（補充數據）', 'ja': '法人税等支払額（補足）'
        },
        'interest_paid_supplemental_data': {
            'en': 'Interest Paid (Supplemental)', 'zh-CN': '已付利息（补充数据）', 'zh-TW': '已付利息（補充數據）', 'ja': '支払利息（補足）'
        },
        'issuance_of_capital_stock': {
            'en': 'Issuance of Capital Stock', 'zh-CN': '股本发行', 'zh-TW': '股本發行', 'ja': '株式の発行'
        },
        'net_business_purchase_and_sale': {
            'en': 'Net Business Purchase & Sale', 'zh-CN': '企业并购净额', 'zh-TW': '企業併購淨額', 'ja': '事業の取得・売却（純額）'
        },
        'net_income_from_continuing_operations': {
            'en': 'Net Income from Continuing Operations', 'zh-CN': '持续经营净利润', 'zh-TW': '持續經營淨利潤', 'ja': '継続事業からの純利益'
        },
        'net_long_term_debt_issuance': {
            'en': 'Net Long Term Debt Issuance', 'zh-CN': '长期债务净发行', 'zh-TW': '長期債務淨發行', 'ja': '長期借入金の純発行'
        },
        'net_short_term_debt_issuance': {
            'en': 'Net Short Term Debt Issuance', 'zh-CN': '短期债务净发行', 'zh-TW': '短期債務淨發行', 'ja': '短期借入金の純発行'
        },
        'net_other_financing_charges': {
            'en': 'Net Other Financing Charges', 'zh-CN': '其他筹资费用净额', 'zh-TW': '其他籌資費用淨額', 'ja': 'その他の財務活動（純額）'
        },
        'net_other_investing_changes': {
            'en': 'Net Other Investing Changes', 'zh-CN': '其他投资变动净额', 'zh-TW': '其他投資變動淨額', 'ja': 'その他の投資活動（純額）'
        },
        // ═══ Specifically Requested Missing Translations ═══
        'total_equity': {
            'en': 'Total Equity', 'zh-CN': '所有者权益合计', 'zh-TW': '所有者權益合計', 'ja': '自己資本合計'
        },
        'short_term_debt': {
            'en': 'Short Term Debt', 'zh-CN': '短期债务', 'zh-TW': '短期債務', 'ja': '短期借入金'
        },
        'property_plant_equipment': {
            'en': 'Property, Plant & Equipment', 'zh-CN': '固定资产', 'zh-TW': '固定資產', 'ja': '有形固定資産'
        },
        'property_plant_and_equipment': {
            'en': 'Property, Plant & Equipment', 'zh-CN': '固定资产', 'zh-TW': '固定資產', 'ja': '有形固定資産'
        },
        'net_property_plant_and_equipment': {
            'en': 'Net Property, Plant & Equipment', 'zh-CN': '固定资产净额', 'zh-TW': '固定資產淨額', 'ja': '有形固定資産（純額）'
        },
        'gross_property_plant_and_equipment': {
            'en': 'Gross Property, Plant & Equipment', 'zh-CN': '固定资产原值', 'zh-TW': '固定資產原值', 'ja': '有形固定資産（総額）'
        },
        'short_term_investments': {
            'en': 'Short Term Investments', 'zh-CN': '短期投资', 'zh-TW': '短期投資', 'ja': '短期投資'
        },
        'capital_expenditures': {
            'en': 'Capital Expenditures', 'zh-CN': '资本支出', 'zh-TW': '資本支出', 'ja': '資本的支出'
        },
        'net_capital_expenditures': {
            'en': 'Net Capital Expenditures', 'zh-CN': '净资本支出', 'zh-TW': '淨資本支出', 'ja': '純資本的支出'
        },
        // ═══ AKShare & Additional Missing Translations ═══
        'revenue': { 'en': 'Revenue', 'zh-CN': '营业收入', 'zh-TW': '營業收入', 'ja': '売上高' },
        'selling_expense': { 'en': 'Selling Expense', 'zh-CN': '销售费用', 'zh-TW': '銷售費用', 'ja': '販売費' },
        'admin_expense': { 'en': 'Admin Expense', 'zh-CN': '管理费用', 'zh-TW': '管理費用', 'ja': '一般管理費' },
        'research_development': { 'en': 'Research & Development', 'zh-CN': '研发费用', 'zh-TW': '研發費用', 'ja': '研究開発費' },
        'taxes_and_surcharges': { 'en': 'Taxes And Surcharges', 'zh-CN': '税金及附加', 'zh-TW': '稅金及附加', 'ja': '税金および付加金' },
        'asset_impairment_loss': { 'en': 'Asset Impairment Loss', 'zh-CN': '资产减值损失', 'zh-TW': '資產減值損失', 'ja': '資産減損損失' },
        'credit_impairment_loss': { 'en': 'Credit Impairment Loss', 'zh-CN': '信用减值损失', 'zh-TW': '信用減值損失', 'ja': '信用減損損失' },
        'investment_income': { 'en': 'Investment Income', 'zh-CN': '投资收益', 'zh-TW': '投資收益', 'ja': '投資収益' },
        'fair_value_change': { 'en': 'Fair Value Change', 'zh-CN': '公允价值变动收益', 'zh-TW': '公允價值變動收益', 'ja': '公正価値変動損益' },
        'total_operating_cost': { 'en': 'Total Operating Cost', 'zh-CN': '营业总成本', 'zh-TW': '營業總成本', 'ja': '営業総費用' },
        'cash': { 'en': 'Cash', 'zh-CN': '货币资金', 'zh-TW': '貨幣資金', 'ja': '現金' },
        'operating_cf': { 'en': 'Operating Cash Flow', 'zh-CN': '经营活动产生的现金流量净额', 'zh-TW': '經營活動產生的現金流量淨額', 'ja': '営業活動によるキャッシュフロー' },
        'free_cf': { 'en': 'Free Cash Flow', 'zh-CN': '自由现金流', 'zh-TW': '自由現金流', 'ja': 'フリーキャッシュフロー' },
        'investing_cf': { 'en': 'Investing Cash Flow', 'zh-CN': '投资活动产生的现金流量净额', 'zh-TW': '投資活動產生的現金流量淨額', 'ja': '投資活動によるキャッシュフロー' },
        'financing_cf': { 'en': 'Financing Cash Flow', 'zh-CN': '筹资活动产生的现金流量净额', 'zh-TW': '籌資活動產生的現金流量淨額', 'ja': '財務活動によるキャッシュフロー' },
        'net_change_in_cash': { 'en': 'Net Change In Cash', 'zh-CN': '现金及现金等价物净增加额', 'zh-TW': '現金及現金等價物淨增加額', 'ja': '現金及び現金同等物の増減額' },
        'depreciation': { 'en': 'Depreciation', 'zh-CN': '折旧', 'zh-TW': '折舊', 'ja': '減価償却費' },
        'amortization': { 'en': 'Amortization', 'zh-CN': '摊销', 'zh-TW': '攤銷', 'ja': '償却費' },
        'cash_end': { 'en': 'Cash at End of Period', 'zh-CN': '期末现金及现金等价物余额', 'zh-TW': '期末現金及現金等價物餘額', 'ja': '期末現金残高' },
        'intangible_assets': { 'en': 'Intangible Assets', 'zh-CN': '无形资产', 'zh-TW': '無形資產', 'ja': '無形固定資産' },
        'bonds_payable': { 'en': 'Bonds Payable', 'zh-CN': '应付债券', 'zh-TW': '應付債券', 'ja': '社債' },
        'current_portion_lt_debt': { 'en': 'Current Portion of LT Debt', 'zh-CN': '一年内到期的非流动负债', 'zh-TW': '一年內到期的非流動負債', 'ja': '1年以内返済予定の長期借入金' },
        'non_current_liabilities': { 'en': 'Non-Current Liabilities', 'zh-CN': '非流动负债', 'zh-TW': '非流動負債', 'ja': '固定負債' },
        'accrued_interest_receivable': { 'en': 'Accrued Interest Receivable', 'zh-CN': '应收利息', 'zh-TW': '應收利息', 'ja': '未収利息' },
        'allowance_for_doubtful_accounts_receivable': { 'en': 'Allowance For Doubtful Accounts Receivable', 'zh-CN': '坏账准备', 'zh-TW': '壞帳準備', 'ja': '貸倒引当金' },
        'amortization_cash_flow': { 'en': 'Amortization Cash Flow', 'zh-CN': '摊销（现金流）', 'zh-TW': '攤銷（現金流）', 'ja': '償却費（キャッシュフロー）' },
        'amortization_of_intangibles': { 'en': 'Amortization Of Intangibles', 'zh-CN': '无形资产摊销', 'zh-TW': '無形資產攤銷', 'ja': '無形資産償却' },
        'amortization_of_intangibles_income_statement': { 'en': 'Amortization Of Intangibles Income Statement', 'zh-CN': '无形资产摊销（利润表）', 'zh-TW': '無形資產攤銷（利潤表）', 'ja': '無形資産償却（損益計算書）' },
        'asset_impairment_charge': { 'en': 'Asset Impairment Charge', 'zh-CN': '资产减值费用', 'zh-TW': '資產減值費用', 'ja': '資産減損損失' },
        'assets_held_for_sale_current': { 'en': 'Assets Held For Sale Current', 'zh-CN': '持有待售流动资产', 'zh-TW': '持有待售流動資產', 'ja': '売却目的保有流動資産' },
        'average_dilution_earnings': { 'en': 'Average Dilution Earnings', 'zh-CN': '平均摊薄收益', 'zh-TW': '平均攤薄收益', 'ja': '平均希薄化後利益' },
        'buildings_and_improvements': { 'en': 'Buildings And Improvements', 'zh-CN': '房屋及建筑物', 'zh-TW': '房屋及建築物', 'ja': '建物および構築物' },
        'capital_expenditure_reported': { 'en': 'Capital Expenditure Reported', 'zh-CN': '报告资本支出', 'zh-TW': '報告資本支出', 'ja': '報告資本的支出' },
        'cash_cash_equivalents_and_federal_funds_sold': { 'en': 'Cash Cash Equivalents', 'zh-CN': '现金及现金等价物', 'zh-TW': '現金及現金等價物', 'ja': '現金及び現金同等物等' },
        'cash_flowsfromusedin_operating_activities_direct': { 'en': 'Operating Cash Flows Direct', 'zh-CN': '经营活动现金流（直接法）', 'zh-TW': '經營活動現金流（直接法）', 'ja': '営業活動によるキャッシュフロー（直接法）' },
        'cash_from_discontinued_financing_activities': { 'en': 'Cash From Discontinued Financing', 'zh-CN': '终止经营筹资活动现金流', 'zh-TW': '終止經營籌資活動現金流', 'ja': '廃止事業財務活動キャッシュフロー' },
        'cash_from_discontinued_investing_activities': { 'en': 'Cash From Discontinued Investing', 'zh-CN': '终止经营投资活动现金流', 'zh-TW': '終止經營投資活動現金流', 'ja': '廃止事業投資活動キャッシュフロー' },
        'cash_from_discontinued_operating_activities': { 'en': 'Cash From Discontinued Operating', 'zh-CN': '终止经营经营活动现金流', 'zh-TW': '終止經營經營活動現金流', 'ja': '廃止事業営業活動キャッシュフロー' },
        'change_in_accrued_expense': { 'en': 'Change In Accrued Expense', 'zh-CN': '应计费用变动', 'zh-TW': '應計費用變動', 'ja': '未払費用増減額' },
        'change_in_income_tax_payable': { 'en': 'Change In Income Tax Payable', 'zh-CN': '应交所得税变动', 'zh-TW': '應交所得稅變動', 'ja': '未払法人税等増減額' },
        'change_in_prepaid_assets': { 'en': 'Change In Prepaid Assets', 'zh-CN': '预付资产变动', 'zh-TW': '預付資產變動', 'ja': '前払費用増減額' },
        'change_in_tax_payable': { 'en': 'Change In Tax Payable', 'zh-CN': '应交税费变动', 'zh-TW': '應交稅費變動', 'ja': '未払税金増減額' },
        'classesof_cash_payments': { 'en': 'Classes of Cash Payments', 'zh-CN': '各项现金支付', 'zh-TW': '各項現金支付', 'ja': '支払現金内訳' },
        'classesof_cash_receiptsfrom_operating_activities': { 'en': 'Classes of Cash Receipts from Operating', 'zh-CN': '经营活动各项现金收入', 'zh-TW': '經營活動各項現金收入', 'ja': '営業活動収入現金内訳' },
        'construction_in_progress': { 'en': 'Construction In Progress', 'zh-CN': '在建工程', 'zh-TW': '在建工程', 'ja': '建設仮勘定' },
        'current_assets': { 'en': 'Current Assets', 'zh-CN': '流动资产', 'zh-TW': '流動資產', 'ja': '流動資産' },
        'current_deferred_assets': { 'en': 'Current Deferred Assets', 'zh-CN': '流动递延资产', 'zh-TW': '流動遞延資產', 'ja': '流動繰延資産' },
        'current_notes_payable': { 'en': 'Current Notes Payable', 'zh-CN': '短期应付票据', 'zh-TW': '短期應付票據', 'ja': '短期支払手形' },
        'current_provisions': { 'en': 'Current Provisions', 'zh-CN': '流动预计负债', 'zh-TW': '流動預計負債', 'ja': '流動引当金' },
        'defined_pension_benefit': { 'en': 'Defined Pension Benefit', 'zh-CN': '设定受益计划', 'zh-TW': '設定受益計劃', 'ja': '確定給付年金' },
        'depreciation_amortization_depletion_income_statement': { 'en': 'Depreciation Amortization Depletion', 'zh-CN': '折旧、摊销及折耗', 'zh-TW': '折舊、攤銷及折耗', 'ja': '減価償却費および枯渇償却費' },
        'depreciation_income_statement': { 'en': 'Depreciation Income Statement', 'zh-CN': '折旧（利润表）', 'zh-TW': '折舊（利潤表）', 'ja': '減価償却費（損益計算書）' },
        'derivative_product_liabilities': { 'en': 'Derivative Product Liabilities', 'zh-CN': '衍生品负债', 'zh-TW': '衍生品負債', 'ja': '派生商品負債' },
        'dividend_paid_cfo': { 'en': 'Dividend Paid CFO', 'zh-CN': '支付的股利（经营）', 'zh-TW': '支付的股利（經營）', 'ja': '支払配当金（営業）' },
        'dividend_received_cfo': { 'en': 'Dividend Received CFO', 'zh-CN': '收到的股利（经营）', 'zh-TW': '收到的股利（經營）', 'ja': '受取配当金（営業）' },
        'dividends_payable': { 'en': 'Dividends Payable', 'zh-CN': '应付股利', 'zh-TW': '應付股利', 'ja': '未払配当金' },
        'dividends_received_cfi': { 'en': 'Dividends Received CFI', 'zh-CN': '收到的股利（投资）', 'zh-TW': '收到的股利（投資）', 'ja': '受取配当金（投資）' },
        'duefrom_related_parties_current': { 'en': 'Due From Related Parties Current', 'zh-CN': '应收关联方款项（流动）', 'zh-TW': '應收關聯方款項（流動）', 'ja': '流動関係会社預け金' },
        'duefrom_related_parties_non_current': { 'en': 'Due From Related Parties Non Current', 'zh-CN': '应收关联方款项（非流动）', 'zh-TW': '應收關聯方款項（非流動）', 'ja': '固定関係会社預け金' },
        'dueto_related_parties_current': { 'en': 'Due To Related Parties Current', 'zh-CN': '应付关联方款项（流动）', 'zh-TW': '應付關聯方款項（流動）', 'ja': '流動関係会社借入金' },
        'dueto_related_parties_non_current': { 'en': 'Due To Related Parties Non Current', 'zh-CN': '应付关联方款项（非流动）', 'zh-TW': '應付關聯方款項（非流動）', 'ja': '固定関係会社借入金' },
        'earnings_from_equity_interest': { 'en': 'Earnings From Equity Interest', 'zh-CN': '权益投资收益', 'zh-TW': '權益投資收益', 'ja': '持分法による投資損益' },
        'earnings_from_equity_interest_net_of_tax': { 'en': 'Earnings From Equity Net Of Tax', 'zh-CN': '权益投资收益（税后）', 'zh-TW': '權益投資收益（稅後）', 'ja': '持分法投資損益（税引後）' },
        'earnings_losses_from_equity_investments': { 'en': 'Earnings Losses From Equity Inv', 'zh-CN': '权益投资盈亏', 'zh-TW': '權益投資盈虧', 'ja': '持分法投資に関する損益' },
        'employee_benefits': { 'en': 'Employee Benefits', 'zh-CN': '员工福利', 'zh-TW': '員工福利', 'ja': '従業員給付' },
        'financial_assets': { 'en': 'Financial Assets', 'zh-CN': '金融资产', 'zh-TW': '金融資產', 'ja': '金融資産' },
        'financial_assets_designatedas_fair_value_through_profitor_loss_total': { 'en': 'Financial Assets FVTPL Total', 'zh-CN': '以公允价值计量且其变动计入当期损益的金融资产', 'zh-TW': '以公允價值計量且其變動計入當期損益的金融資產', 'ja': 'FVTPL指定金融資産合計' },
        'finished_goods': { 'en': 'Finished Goods', 'zh-CN': '产成品', 'zh-TW': '產成品', 'ja': '製品' },
        'fixed_assets_revaluation_reserve': { 'en': 'Fixed Assets Revaluation Reserve', 'zh-CN': '固定资产重估储备', 'zh-TW': '固定資產重估儲備', 'ja': '固定資産再評価積立金' },
        'foreign_currency_translation_adjustments': { 'en': 'Foreign Currency Translation Adj.', 'zh-CN': '外币报表折算差额', 'zh-TW': '外幣報表折算差額', 'ja': '為替換算調整勘定' },
        'gain_loss_on_investment_securities': { 'en': 'Gain Loss On Investment Sec.', 'zh-CN': '投资证券投资损益', 'zh-TW': '投資證券投資損益', 'ja': '投資有価証券売却損益' },
        'gain_loss_on_sale_of_business': { 'en': 'Gain Loss On Sale Of Business', 'zh-CN': '出售业务的损益', 'zh-TW': '出售業務的損益', 'ja': '事業売却損益' },
        'gain_loss_on_sale_of_ppe': { 'en': 'Gain Loss On Sale Of PPE', 'zh-CN': '处置固定资产损益', 'zh-TW': '處置固定資產損益', 'ja': '有形固定資産売却損益' },
        'gain_on_sale_of_business': { 'en': 'Gain On Sale Of Business', 'zh-CN': '出售业务收益', 'zh-TW': '出售業務收益', 'ja': '事業売却益' },
        'gain_on_sale_of_ppe': { 'en': 'Gain On Sale Of PPE', 'zh-CN': '出售固定资产收益', 'zh-TW': '出售固定資產收益', 'ja': '有形固定資産売却益' },
        'gain_on_sale_of_security': { 'en': 'Gain On Sale Of Security', 'zh-CN': '出售证券收益', 'zh-TW': '出售證券收益', 'ja': '有価証券売却益' },
        'general_and_administrative_expense': { 'en': 'General And Administrative Exp', 'zh-CN': '管理费用', 'zh-TW': '管理費用', 'ja': '一般管理費' },
        'gross_accounts_receivable': { 'en': 'Gross Accounts Receivable', 'zh-CN': '应收账款原值', 'zh-TW': '應收帳款原值', 'ja': '売掛金総額' },
        'hedging_assets_current': { 'en': 'Hedging Assets Current', 'zh-CN': '套期保值资产（流动）', 'zh-TW': '套期保值資產（流動）', 'ja': '流動ヘッジ資産' },
        'held_to_maturity_securities': { 'en': 'Held To Maturity Securities', 'zh-CN': '持有至到期投资', 'zh-TW': '持有至到期投資', 'ja': '満期保有目的債券' },
        'impairment_of_capital_assets': { 'en': 'Impairment Of Capital Assets', 'zh-CN': '资本资产减值', 'zh-TW': '資本資產減值', 'ja': '資本資産減損' },
        'insurance_and_claims': { 'en': 'Insurance And Claims', 'zh-CN': '保险与理赔', 'zh-TW': '保險與理賠', 'ja': '保険および請求' },
        'interest_paid_cff': { 'en': 'Interest Paid CFF', 'zh-CN': '支付的利息（筹资）', 'zh-TW': '支付的利息（籌資）', 'ja': '財務活動の支払利息' },
        'interest_paid_cfo': { 'en': 'Interest Paid CFO', 'zh-CN': '支付的利息（经营）', 'zh-TW': '支付的利息（經營）', 'ja': '営業活動の支払利息' },
        'interest_paid_direct': { 'en': 'Interest Paid Direct', 'zh-CN': '支付的利息（直接法）', 'zh-TW': '支付的利息（直接法）', 'ja': '支払利息（直接法）' },
        'interest_payable': { 'en': 'Interest Payable', 'zh-CN': '应付利息', 'zh-TW': '應付利息', 'ja': '未払利息' },
        'interest_received_cfi': { 'en': 'Interest Received CFI', 'zh-CN': '收到的利息（投资）', 'zh-TW': '收到的利息（投資）', 'ja': '投資活動の受取利息' },
        'interest_received_cfo': { 'en': 'Interest Received CFO', 'zh-CN': '收到的利息（经营）', 'zh-TW': '收到的利息（經營）', 'ja': '営業活動の受取利息' },
        'interest_received_direct': { 'en': 'Interest Received Direct', 'zh-CN': '收到的利息（直接法）', 'zh-TW': '收到的利息（直接法）', 'ja': '受取利息（直接法）' },
        'inventories_adjustments_allowances': { 'en': 'Inventories Adjustments', 'zh-CN': '存货跌价准备', 'zh-TW': '存貨跌價準備', 'ja': '棚卸資産評価引当金' },
        'investment_properties': { 'en': 'Investment Properties', 'zh-CN': '投资性房地产', 'zh-TW': '投資性房地產', 'ja': '投資不動産' },
        'investments_in_other_ventures_under_equity_method': { 'en': 'Equity Method Investments', 'zh-CN': '权益法下其他企业投资', 'zh-TW': '權益法下其他企業投資', 'ja': '持分法適用会社への投資' },
        'investmentsin_associatesat_cost': { 'en': 'Investments in Associates at Cost', 'zh-CN': '联营企业投资（成本法）', 'zh-TW': '聯營企業投資（成本法）', 'ja': '関連会社への投資（原価）' },
        'investmentsin_joint_venturesat_cost': { 'en': 'Investments in Joint Ventures at Cost', 'zh-CN': '合营企业投资（成本法）', 'zh-TW': '合營企業投資（成本法）', 'ja': '共同支配企業への投資（原価）' },
        'liabilities_heldfor_sale_non_current': { 'en': 'Liabilities Held For Sale Non Current', 'zh-CN': '持有待售非流动负债', 'zh-TW': '持有待售非流動負債', 'ja': '売却目的保有固定負債' },
        'line_of_credit': { 'en': 'Line Of Credit', 'zh-CN': '信用额度', 'zh-TW': '信用額度', 'ja': 'クレジットライン' },
        'long_term_provisions': { 'en': 'Long Term Provisions', 'zh-CN': '长期预计负债', 'zh-TW': '長期預計負債', 'ja': '長期引当金' },
        'minimum_pension_liabilities': { 'en': 'Minimum Pension Liabilities', 'zh-CN': '最低养老金负债', 'zh-TW': '最低養老金負債', 'ja': '最低年金負債' },
        'net_foreign_currency_exchange_gain_loss': { 'en': 'Net FX Gain Loss', 'zh-CN': '净汇兑损益', 'zh-TW': '淨匯兌損益', 'ja': '為替差損益純額' },
        'net_intangibles_purchase_and_sale': { 'en': 'Net Intangibles Purchase And Sale', 'zh-CN': '净买卖无形资产', 'zh-TW': '淨買賣無形資產', 'ja': '無形資産純売買額' },
        'net_investment_properties_purchase_and_sale': { 'en': 'Net Investment Prop Purchase/Sale', 'zh-CN': '净买卖投资性房地产', 'zh-TW': '淨買賣投資性房地產', 'ja': '投資不動産純売買額' },
        'net_policyholder_benefits_and_claims': { 'en': 'Net Policyholder Benefits Claims', 'zh-CN': '净保单持有人利益与赔款', 'zh-TW': '淨保單持有人利益與賠款', 'ja': '純保険契約者給付金及び請求' },
        'net_preferred_stock_issuance': { 'en': 'Net Preferred Stock Issuance', 'zh-CN': '优先股净发行', 'zh-TW': '優先股淨發行', 'ja': '優先株純発行額' },
        'non_current_accounts_receivable': { 'en': 'Non Current Accounts Receivable', 'zh-CN': '非流动应收账款', 'zh-TW': '非流動應收帳款', 'ja': '固定売掛金' },
        'non_current_accrued_expenses': { 'en': 'Non Current Accrued Expenses', 'zh-CN': '非流动应计费用', 'zh-TW': '非流動應計費用', 'ja': '固定未払費用' },
        'non_current_deferred_liabilities': { 'en': 'Non Current Deferred Liabilities', 'zh-CN': '非流动递延负债', 'zh-TW': '非流動遞延負債', 'ja': '固定繰延負債' },
        'non_current_deferred_revenue': { 'en': 'Non Current Deferred Revenue', 'zh-CN': '非流动递延收入', 'zh-TW': '非流動遞延收入', 'ja': '固定繰延収益' },
        'non_current_deferred_taxes_liabilities': { 'en': 'Non Current Deferred Taxes Liab.', 'zh-CN': '非流动递延所得税负债', 'zh-TW': '非流動遞延所得稅負債', 'ja': '固定繰延税金負債' },
        'non_current_pension_and_other_postretirement_benefit_plans': { 'en': 'Non Current Pension Benefit Plans', 'zh-CN': '非流动养老金及离职后福利', 'zh-TW': '非流動養老金及離職後福利', 'ja': '固定年金及び退職後給付制度' },
        'non_current_prepaid_assets': { 'en': 'Non Current Prepaid Assets', 'zh-CN': '非流动预付资产', 'zh-TW': '非流動預付資產', 'ja': '固定前払資産' },
        'occupancy_and_equipment': { 'en': 'Occupancy And Equipment', 'zh-CN': '办公设备及租金', 'zh-TW': '辦公設備及租金', 'ja': '施設および設備費' },
        'operating_gains_losses': { 'en': 'Operating Gains Losses', 'zh-CN': '经营损益', 'zh-TW': '經營損益', 'ja': '営業損益' },
        'other_cash_adjustment_inside_changein_cash': { 'en': 'Other Cash Adj Inside Change in Cash', 'zh-CN': '其他现金变动内部调整', 'zh-TW': '其他現金變動內部調整', 'ja': 'その他のキャッシュ内部調整' },
        'other_cash_adjustment_outside_changein_cash': { 'en': 'Other Cash Adj Outside Change in Cash', 'zh-CN': '其他现金变动外部调整', 'zh-TW': '其他現金變動外部調整', 'ja': 'その他のキャッシュ外部調整' },
        'other_cash_paymentsfrom_operating_activities': { 'en': 'Other Cash Payments from Operating', 'zh-CN': '其他经营现金支付', 'zh-TW': '其他經營現金支付', 'ja': 'その他の営業現金支出' },
        'other_cash_receiptsfrom_operating_activities': { 'en': 'Other Cash Receipts from Operating', 'zh-CN': '其他经营现金收入', 'zh-TW': '其他經營現金收入', 'ja': 'その他の営業現金収入' },
        'other_equity_interest': { 'en': 'Other Equity Interest', 'zh-CN': '其他权益影响', 'zh-TW': '其他權益影響', 'ja': 'その他の持分' },
        'other_gand_a': { 'en': 'Other G&A', 'zh-CN': '其他管理费用', 'zh-TW': '其他管理費用', 'ja': 'その他の一般管理費' },
        'other_inventories': { 'en': 'Other Inventories', 'zh-CN': '其他存货', 'zh-TW': '其他存貨', 'ja': 'その他の棚卸資産' },
        'other_non_interest_expense': { 'en': 'Other Non Interest Expense', 'zh-CN': '其他非利息支出', 'zh-TW': '其他非利息支出', 'ja': 'その他の非利息費用' },
        'other_payable': { 'en': 'Other Payable', 'zh-CN': '其他应付款', 'zh-TW': '其他應付款', 'ja': 'その他未払金' },
        'other_special_charges': { 'en': 'Other Special Charges', 'zh-CN': '其他特殊费用', 'zh-TW': '其他特殊費用', 'ja': 'その他の特別損失' },
        'other_taxes': { 'en': 'Other Taxes', 'zh-CN': '其他税费', 'zh-TW': '其他稅費', 'ja': 'その他の税金' },
        'otherunder_preferred_stock_dividend': { 'en': 'Other Under Preferred Stock Div', 'zh-CN': '优先股股息下方其他项目', 'zh-TW': '優先股股息下方其他項目', 'ja': '優先配当金控除後のその他項目' },
        'paymentson_behalfof_employees': { 'en': 'Payments on Behalf of Employees', 'zh-CN': '代员工支付款项', 'zh-TW': '代員工支付款項', 'ja': '従業員代行支払' },
        'paymentsto_suppliersfor_goodsand_services': { 'en': 'Payments to Suppliers', 'zh-CN': '向供应商支付的商品及服务款项', 'zh-TW': '向供應商支付的商品及服務款項', 'ja': '商品及びサービスの仕入先への支払' },
        'pension_and_employee_benefit_expense': { 'en': 'Pension And Employee Benefit Exp', 'zh-CN': '养老金及员工福利支出', 'zh-TW': '養老金及員工福利支出', 'ja': '年金および従業員給付費用' },
        'pensionand_other_post_retirement_benefit_plans_current': { 'en': 'Pension and Other Plans Current', 'zh-CN': '流动养老及离职后福利', 'zh-TW': '流動養老及離職後福利', 'ja': '流動年金及び退職後給付制度' },
        'preferred_securities_outside_stock_equity': { 'en': 'Pref Securities Outside Equity', 'zh-CN': '普通权益外的优先证券', 'zh-TW': '普通權益外的優先證券', 'ja': '株主資本外の優先証券' },
        'preferred_shares_number': { 'en': 'Preferred Shares Number', 'zh-CN': '优先股数量', 'zh-TW': '優先股數量', 'ja': '優先株式数' },
        'preferred_stock': { 'en': 'Preferred Stock', 'zh-CN': '优先股', 'zh-TW': '優先股', 'ja': '優先株' },
        'preferred_stock_dividends': { 'en': 'Preferred Stock Dividends', 'zh-CN': '优先股股息', 'zh-TW': '優先股股息', 'ja': '優先株配当金' },
        'preferred_stock_equity': { 'en': 'Preferred Stock Equity', 'zh-CN': '优先股权益', 'zh-TW': '優先股權益', 'ja': '優先株主持分' },
        'preferred_stock_issuance': { 'en': 'Preferred Stock Issuance', 'zh-CN': '发行优先股', 'zh-TW': '發行優先股', 'ja': '優先株発行' },
        'preferred_stock_payments': { 'en': 'Preferred Stock Payments', 'zh-CN': '优先股支付额', 'zh-TW': '優先股支付額', 'ja': '優先株支払額' },
        'prepaid_assets': { 'en': 'Prepaid Assets', 'zh-CN': '预付资产', 'zh-TW': '預付資產', 'ja': '前払資産' },
        'proceeds_from_stock_option_exercised': { 'en': 'Proceeds From Stock Option', 'zh-CN': '股票期权行权收入', 'zh-TW': '股票期權行權收入', 'ja': 'ストックオプション行使による収入' },
        'professional_expense_and_contract_services_expense': { 'en': 'Professional and Contract Services', 'zh-CN': '专业服务及合同支出', 'zh-TW': '專業服務及合同支出', 'ja': '専門および契約サービス費用' },
        'provisionand_write_offof_assets': { 'en': 'Provision and Write Off of Assets', 'zh-CN': '资产减值准备与核销', 'zh-TW': '資產減值準備與核銷', 'ja': '資産引当金および償却' },
        'purchase_of_intangibles': { 'en': 'Purchase Of Intangibles', 'zh-CN': '购买无形资产', 'zh-TW': '購買無形資產', 'ja': '無形資産の購入' },
        'purchase_of_investment_properties': { 'en': 'Purchase Of Investment Prop', 'zh-CN': '购买投资性房地产', 'zh-TW': '購買投資性房地產', 'ja': '投資不動産の購入' },
        'raw_materials': { 'en': 'Raw Materials', 'zh-CN': '原材料', 'zh-TW': '原材料', 'ja': '原材料' },
        'receiptsfrom_customers': { 'en': 'Receipts from Customers', 'zh-CN': '来自客户的收入', 'zh-TW': '來自客戶的收入', 'ja': '顧客からの収入' },
        'receivables_adjustments_allowances': { 'en': 'Receivables Adjustments Allowances', 'zh-CN': '应收账款调整及准备金', 'zh-TW': '應收帳款調整及準備金', 'ja': '売掛金調整および引当金' },
        'rent_and_landing_fees': { 'en': 'Rent And Landing Fees', 'zh-CN': '租金及着陆费', 'zh-TW': '租金及著陸費', 'ja': '賃借料および着陸料' },
        'rent_expense_supplemental': { 'en': 'Rent Expense Supplemental', 'zh-CN': '补充租金支出', 'zh-TW': '補充租金支出', 'ja': '追加賃借料' },
        'restricted_cash': { 'en': 'Restricted Cash', 'zh-CN': '受限资金', 'zh-TW': '受限資金', 'ja': '拘束性預金' },
        'salaries_and_wages': { 'en': 'Salaries And Wages', 'zh-CN': '工资与薪金', 'zh-TW': '工資與薪金', 'ja': '給与および賃金' },
        'sale_of_business': { 'en': 'Sale Of Business', 'zh-CN': '出售业务', 'zh-TW': '出售業務', 'ja': '事業売却' },
        'sale_of_intangibles': { 'en': 'Sale Of Intangibles', 'zh-CN': '出售无形资产', 'zh-TW': '出售無形資產', 'ja': '無形資産売却' },
        'sale_of_investment_properties': { 'en': 'Sale Of Investment Properties', 'zh-CN': '出售投资性房地产', 'zh-TW': '出售投資性房地產', 'ja': '投資不動産売却' },
        'sale_of_ppe': { 'en': 'Sale Of PPE', 'zh-CN': '出售固定资产', 'zh-TW': '出售固定資產', 'ja': '有形固定資産売却' },
        'selling_and_marketing_expense': { 'en': 'Selling And Marketing Exp', 'zh-CN': '销售与营销费用', 'zh-TW': '銷售與營銷費用', 'ja': '販売・マーケティング費用' },
        'selling_general_and_administration': { 'en': 'Selling General & Admin', 'zh-CN': '销售及管理费用', 'zh-TW': '銷售及管理費用', 'ja': '販売費及び一般管理費' },
        'taxes_receivable': { 'en': 'Taxes Receivable', 'zh-CN': '应收税金', 'zh-TW': '應收稅金', 'ja': '未収税金' },
        'taxes_refund_paid': { 'en': 'Taxes Refund Paid', 'zh-CN': '支付与退回的税费', 'zh-TW': '支付與退回的稅費', 'ja': '支払および還付税金' },
        'taxes_refund_paid_direct': { 'en': 'Taxes Refund Paid Direct', 'zh-CN': '税费退回（直接法）', 'zh-TW': '稅費退回（直接法）', 'ja': '税金還付（直接法）' },
        'total_other_finance_cost': { 'en': 'Total Other Finance Cost', 'zh-CN': '其他财务总成本', 'zh-TW': '其他財務總成本', 'ja': 'その他財務費用合計' },
        'total_unusual_items': { 'en': 'Total Unusual Items', 'zh-CN': '非经常性项目合计', 'zh-TW': '非經常性項目合計', 'ja': '非経常項目合計' },
        'total_unusual_items_excluding_goodwill': { 'en': 'Total Unusual Items Excl Goodwill', 'zh-CN': '除商誉外非经常性项目合计', 'zh-TW': '除商譽外非經常性項目合計', 'ja': 'のれんを除く非経常項目合計' },
        'trading_securities': { 'en': 'Trading Securities', 'zh-CN': '交易性金融资产', 'zh-TW': '交易性金融資產', 'ja': '売買目的有価証券' },
        'unrealized_gain_loss': { 'en': 'Unrealized Gain Loss', 'zh-CN': '未实现持仓损益', 'zh-TW': '未實現持倉損益', 'ja': '未実現評価損益' },
        'unrealized_gain_loss_on_investment_securities': { 'en': 'Unrealized Gain Loss On Inv. Sec.', 'zh-CN': '未实现投资证券损益', 'zh-TW': '未實現投資證券損益', 'ja': '未実現投資有価証券評価損益' },
        'work_in_process': { 'en': 'Work In Process', 'zh-CN': '在产品', 'zh-TW': '在產品', 'ja': '仕掛品' },
        'write_off': { 'en': 'Write Off', 'zh-CN': '核销', 'zh-TW': '核銷', 'ja': '償却/帳簿への減額' },
    };
    return dictionary[normalizedKey]?.[lang] || key.split(/_|\s+/).map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
};
export type TooltipDef = { def: string; formula?: string };
export const getTooltip = (metricKey: string, lang: Language): TooltipDef | null => {
    const normalizedKey = metricKey.toLowerCase().replace(/\s+/g, '_');
    const tooltips: Record<string, Record<Language, TooltipDef>> = {
        'operating_income': {
            'en': { def: 'Earnings Before Interest and Taxes (EBIT). Measures profitability from core operations.', formula: 'Revenue - COGS - Operating Expenses' },
            'zh-CN': { def: '息税前利润（EBIT）。衡量核心业务的盈利能力。', formula: '营业收入 - 营业成本 - 营业费用' },
            'zh-TW': { def: '息稅前利潤（EBIT）。衡量核心業務的盈利能力。', formula: '營業收入 - 營業成本 - 營業費用' },
            'ja': { def: '利払前税引前利益 (EBIT)。中核事業からの収益性を測定します。', formula: '売上高 - 売上原価 - 営業費用' }
        },
        'ebitda': {
            'en': { def: 'Earnings Before Interest, Taxes, Depreciation, and Amortization. A proxy for operating cash flow.', formula: 'Operating Income + Depreciation + Amortization' },
            'zh-CN': { def: '息税折旧摊销前利润。通常作为经营现金流的代理指标。', formula: '营业利润 + 折旧 + 摊销' },
            'zh-TW': { def: '息稅折舊攤銷前利潤。通常作為經營現金流的代理指標。', formula: '營業利潤 + 折舊 + 攤銷' },
            'ja': { def: '利払前・税引前・減価償却前利益。営業キャッシュフローの代替指標。', formula: '営業利益 + 減価償却費 + のれん償却額' }
        },
        'total_debt': {
            'en': { def: 'Sum of all short-term and long-term interest-bearing liabilities.', formula: 'Short Term Debt + Long Term Debt' },
            'zh-CN': { def: '所有短期和长期计息负债的总和。', formula: '短期债务 + 长期债务' },
            'zh-TW': { def: '所有短期和長期計息負債的總和。', formula: '短期債務 + 長期債務' },
            'ja': { def: '短期および長期の有利子負債の合計。', formula: '短期借入金 + 長期借入金' }
        },
        'debt_to_ebitda': {
            'en': { def: 'Measures how many years it would take to pay back debt using current EBITDA. >3.0x suggests higher risk.', formula: 'Total Debt / EBITDA' },
            'zh-CN': { def: '衡量目前的EBITDA需要多少年才能偿还全部债务。大于3倍表明风险较高。', formula: '总债务 / EBITDA' },
            'zh-TW': { def: '衡量目前的EBITDA需要多少年才能償還全部債務。大於3倍表明風險較高。', formula: '總債務 / EBITDA' },
            'ja': { def: '現在のEBITDAを用いて負債を返済するのに何年かかるかを測定します。3倍以上は高リスクとされます。', formula: '総有利子負債 / EBITDA' }
        },
        'interest_coverage': {
            'en': { def: 'Measures a company\'s ability to pay interest expenses. <2.0x is concerning.', formula: 'EBIT / Interest Expense' },
            'zh-CN': { def: '衡量公司支付利息费用的能力。小于2倍通常具有较高风险。', formula: '息税前利润 / 利息费用' },
            'zh-TW': { def: '衡量公司支付利息費用的能力。小於2倍通常具有較高風險。', formula: '息稅前利潤 / 利息費用' },
            'ja': { def: '企業の支払利息への対応能力を測定します。2倍未満は懸念されます。', formula: 'EBIT / 支払利息' }
        },
        'free_cf': {
            'en': { def: 'Cash left over after paying for operating expenses and capital expenditures.', formula: 'Operating Cash Flow - Capital Expenditures' },
            'zh-CN': { def: '支付经营费用和资本支出后剩余的现金。', formula: '经营现金流 - 资本支出' },
            'zh-TW': { def: '支付經營費用和資本支出後剩餘的現金。', formula: '經營現金流 - 資本支出' },
            'ja': { def: '営業費用と資本的支出を支払った後に残る現金。', formula: '営業キャッシュフロー - 資本的支出' }
        },
        'fcf_to_debt': {
            'en': { def: 'Percentage of total debt that could be paid off with a year\'s free cash flow. <10% is weak.', formula: '(Free Cash Flow / Total Debt) * 100' },
            'zh-CN': { def: '一年自由现金流可以偿还的总债务百分比。小于10%通常视为较弱。', formula: '(自由现金流 / 总债务) * 100' },
            'zh-TW': { def: '一年自由現金流可以償還的總債務百分比。小於10%通常視為較弱。', formula: '(自由現金流 / 總債務) * 100' },
            'ja': { def: '1年間のフリーキャッシュフローで返済できる総有利子負債の割合。10%未満は弱いとされます。', formula: '(FCF / 総有利子負債) * 100' }
        },
        'current_ratio': {
            'en': { def: 'Measures ability to pay short-term obligations using short-term assets. <1.0x indicates potential liquidity issues.', formula: 'Current Assets / Current Liabilities' },
            'zh-CN': { def: '衡量使用短期资产偿还短期债务的能力。小于1倍可能表明流动性存在问题。', formula: '流动资产 / 流动负债' },
            'zh-TW': { def: '衡量使用短期資產償還短期債務的能力。小於1倍可能表明流動性存在問題。', formula: '流動資產 / 流動負債' },
            'ja': { def: '短期資産を用いて短期負債を支払う能力を測定します。1未満は潜在的な流動性の問題を示します。', formula: '流動資産 / 流動負債' }
        },
        'zscore': {
            'en': { def: 'Altman Z-Score. Predicts the probability of a company going bankrupt within 2 years. >2.99 is safe, 1.81-2.99 is grey, <1.81 is distress.', formula: '1.2(Working Capital/Total Assets) + 1.4(Retained Earnings/Total Assets) + 3.3(EBIT/Total Assets) + 0.6(Market Value of Equity/Total Liabilities) + 1.0(Sales/Total Assets)' },
            'zh-CN': { def: '奥特曼 Z-score。预测公司两年内破产的概率。>2.99 为安全，1.81-2.99 为灰色地带，<1.81 为财务困境。', formula: '1.2(营运资本/总资产) + 1.4(留存收益/总资产) + 3.3(EBIT/总资产) + 0.6(股权市值/总负债) + 1.0(销售额/总资产)' },
            'zh-TW': { def: '奧特曼 Z-score。預測公司兩年內破產的概率。>2.99 為安全，1.81-2.99 為灰色地帶，<1.81 為財務困境。', formula: '1.2(營運資本/總資產) + 1.4(保留盈餘/總資產) + 3.3(EBIT/總資產) + 0.6(股權市值/總負債) + 1.0(銷售額/總資產)' },
            'ja': { def: 'アルトマン Z-Score。2年以内に企業が倒産する確率を予測します。>2.99は安全、1.81-2.99はグレー、<1.81は苦境。', formula: '1.2(運転資本/総資産) + 1.4(利益剰余金/総資産) + 3.3(EBIT/総資産) + 0.6(株式時価総額/総負債) + 1.0(売上高/総資産)' }
        },
        'implied_rating': {
            'en': { def: 'Experimental credit rating derived from Z-Score thresholds. Maps Z-Score probability of default into S&P global rating scale equivalents.' },
            'zh-CN': { def: '基于 Z-Score 阈值推导的实验性信用评级。将 Z-Score 的违约概率映射为标普全球评级标准的等效评级。' },
            'zh-TW': { def: '基於 Z-Score 閾值推導的實驗性信用評級。將 Z-Score 的違約概率映射為標普全球評級標準的等效評級。' },
            'ja': { def: 'Z-Scoreの閾値から導出された実験的な信用格付け。Z-Scoreのデフォルト確率は、S&Pグローバル格付け尺度の相当格付けにマッピングされます。' }
        }
    };
    return tooltips[normalizedKey]?.[lang] || null;
};
export const translateRatingStatus = (status: string, lang: Language): string => {
    if (lang === 'en') return status;
    const map: Record<string, Record<Language, string>> = {
        'Safe (S)': { 'en': 'Safe (S)', 'zh-CN': '安全 (S)', 'zh-TW': '安全 (S)', 'ja': '安全 (S)' },
        'Grey (G)': { 'en': 'Grey (G)', 'zh-CN': '灰色 (G)', 'zh-TW': '灰色 (G)', 'ja': 'グレー (G)' },
        'Distress (D)': { 'en': 'Distress (D)', 'zh-CN': '困境 (D)', 'zh-TW': '困境 (D)', 'ja': '苦境 (D)' },
        'Safe': { 'en': 'Safe', 'zh-CN': '安全', 'zh-TW': '安全', 'ja': '安全' },
        'Grey': { 'en': 'Grey', 'zh-CN': '灰色', 'zh-TW': '灰色', 'ja': 'グレー' },
        'Distress': { 'en': 'Distress', 'zh-CN': '困境', 'zh-TW': '困境', 'ja': '苦境' },
    };
    return map[status]?.[lang] || status;
};
