import { test, expect } from 'playwright/test';

const synthesizeButton = /Synthesize|综合分析|綜合分析|分析する/i;

function createPeriod(label, riskScore = 2.5) {
  return {
    fiscal_year: label,
    is_quarterly: false,
    assessment: {
      overall_rating: 'Grey (G)',
      risk_score: riskScore,
      implied_rating: 'BBB',
      strengths: [],
      weaknesses: [],
    },
    ratios: {
      ebitda: 123,
      debt_to_ebitda: 1.23,
      interest_coverage: 3.2,
      fcf_to_debt: 0.12,
      current_ratio: 1.4,
    },
    raw_metrics: {
      operating_income: 100,
      total_debt: 200,
      free_cf: 50,
    },
    statements: {
      income: { revenue: 1000, net_income: 100 },
      balance: { total_assets: 5000, total_liabilities: 2800 },
      cash: { operating_cf: 130, investing_cf: -50 },
    },
  };
}

test('500 text response does not leave UI in loading state', async ({ page }) => {
  await page.route('**/api/v1/assess', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'text/plain',
      body: 'Internal Server Error',
    });
  });

  await page.goto('/');
  await page.locator('input').first().fill('AAPL');
  await page.getByRole('button', { name: synthesizeButton }).click();

  await expect(page.getByText(/Internal Server Error|Request failed \(500\)/)).toBeVisible();
  await expect(page.getByRole('button', { name: synthesizeButton })).toBeEnabled();
});

test('export all is safe when every result has empty history', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', (err) => pageErrors.push(err));

  await page.route('**/api/v1/assess', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 2,
        errors: null,
        suggestions: null,
        results: [
          { ticker: 'AAPL', company_name: 'Apple', history: [] },
          { ticker: 'MSFT', company_name: 'Microsoft', history: [] },
        ],
      }),
    });
  });

  await page.goto('/');
  await page.locator('input').first().fill('AAPL,MSFT');
  await page.getByRole('button', { name: synthesizeButton }).click();

  const exportAll = page.getByRole('button', { name: /Export All/i });
  await expect(exportAll).toBeVisible();
  await exportAll.click();

  await page.waitForTimeout(500);
  expect(pageErrors, 'page should not throw runtime errors').toEqual([]);
  await expect(page.locator('body')).toBeVisible();
});

test('mobile table keeps horizontal overflow with many periods', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });

  await page.route('**/api/v1/assess', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 1,
        errors: null,
        suggestions: null,
        results: [
          {
            ticker: 'AAPL',
            company_name: 'Apple Inc.',
            currency: 'USD',
            history: [
              createPeriod("FY25", 2.6),
              createPeriod("FY24", 2.4),
              createPeriod("FY23", 2.2),
              createPeriod("FY22", 2.1),
              createPeriod("Q3 '25", 2.3),
              createPeriod("Q2 '25", 2.5),
              createPeriod("Q1 '25", 2.7),
            ],
          },
        ],
      }),
    });
  });

  await page.goto('/');
  await page.locator('input').first().fill('AAPL');
  await page.getByRole('button', { name: synthesizeButton }).click();

  const headers = page.locator('table thead tr').first().locator('th');
  await expect(headers.first()).toHaveCSS('min-width', '192px');
  await expect(headers.nth(1)).toHaveCSS('min-width', '112px');

  const scrollContainer = page.locator('.overflow-x-auto').first();
  const dimensions = await scrollContainer.evaluate((el) => ({
    clientWidth: el.clientWidth,
    scrollWidth: el.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeGreaterThan(dimensions.clientWidth);
});
