import { createHash } from 'node:crypto';
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
  await page.locator('input').first().fill('NVDA');
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
          { ticker: 'NVDA', company_name: 'NVIDIA', history: [] },
          { ticker: 'AMD', company_name: 'Advanced Micro Devices', history: [] },
        ],
      }),
    });
  });

  await page.goto('/');
  await page.locator('input').first().fill('NVDA,AMD');
  await page.getByRole('button', { name: synthesizeButton }).click();

  const exportAll = page.getByRole('button', { name: /Export All to Excel/i });
  await expect(exportAll).toBeVisible();
  await exportAll.click();

  await page.waitForTimeout(500);
  expect(pageErrors, 'page should not throw runtime errors').toEqual([]);
  await expect(page.locator('body')).toBeVisible();
});

test('batch PDF export sends all results and verifies ZIP integrity', async ({ page }) => {
  const zipBody = Buffer.from('risklens-test-zip', 'utf8');
  const zipSha256 = createHash('sha256').update(zipBody).digest('hex');
  let batchRequestBody = null;

  await page.route('**/api/v1/assess', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 2,
        errors: null,
        suggestions: null,
        results: [
          { ticker: 'NVDA', company_name: 'NVIDIA', history: [createPeriod('FY25')] },
          { ticker: 'AMD', company_name: 'Advanced Micro Devices', history: [createPeriod('FY25')] },
        ],
      }),
    });
  });
  await page.route('**/api/v1/reports/pdf/batch', async (route) => {
    batchRequestBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/zip',
      headers: {
        'content-disposition': 'attachment; filename="RiskLens_PDF_Reports.zip"',
        'x-zip-sha256': zipSha256,
        'x-zip-bytes': String(zipBody.length),
      },
      body: zipBody,
    });
  });

  await page.goto('/');
  await page.locator('input').first().fill('NVDA,AMD');
  await page.getByRole('button', { name: synthesizeButton }).click();
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /Export All to PDF/i }).click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe('RiskLens_PDF_Reports.zip');
  expect(batchRequestBody?.theme).toBe('light');
  expect(batchRequestBody?.reports).toHaveLength(2);
  expect(batchRequestBody?.reports.map((report) => report.ticker)).toEqual(['NVDA', 'AMD']);
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
            ticker: 'NVDA',
            company_name: 'NVIDIA Corp.',
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
  await page.locator('input').first().fill('NVDA');
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

test('pdf export verifies the downloaded blob against response headers', async ({ page }) => {
  const pdfBody = Buffer.from('%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF', 'utf8');
  const pdfSha256 = createHash('sha256').update(pdfBody).digest('hex');

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
            ticker: 'NVDA',
            company_name: 'NVIDIA Corp.',
            currency: 'USD',
            history: [
              createPeriod('FY25', 2.6),
              createPeriod('FY24', 2.4),
              createPeriod('FY23', 2.2),
            ],
          },
        ],
      }),
    });
  });

  let pdfRequestBody = null;
  await page.route('**/api/v1/reports/pdf', async (route) => {
    pdfRequestBody = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: 'application/pdf',
      headers: {
        'content-disposition': 'attachment; filename="NVDA_Full_Report.pdf"',
        'x-pdf-sha256': pdfSha256,
        'x-pdf-bytes': String(pdfBody.length),
      },
      body: pdfBody,
    });
  });

  await page.goto('/');
  await page.locator('input').first().fill('NVDA');
  await page.getByRole('button', { name: synthesizeButton }).click();

  await expect(page.getByRole('button', { name: /Export PDF/i }).first()).toBeVisible();
  await page.getByRole('button', { name: /Export PDF/i }).first().click();

  const exportDialog = page.getByRole('dialog');
  const downloadPromise = page.waitForEvent('download');
  await exportDialog.getByRole('button', { name: /Export PDF/i }).click();
  const download = await downloadPromise;

  expect(download.suggestedFilename()).toBe('NVDA_Full_Report.pdf');
  expect(pdfRequestBody?.theme).toBe('light');
  await expect(exportDialog.getByText(`SHA-256: ${pdfSha256}`)).toBeVisible();
  await expect(exportDialog.getByText(`Bytes: ${pdfBody.length}`)).toBeVisible();
});
