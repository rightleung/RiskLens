const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage();

    page.on('console', msg => console.log('BROWSER CONSOLE:', msg.type(), msg.text()));
    page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));

    console.log("Navigating to app...");
    await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });

    console.log("Typing 000002.SZ...");
    await page.fill('input[placeholder]', '000002.SZ');
    await page.click('button[type="submit"]');

    console.log("Waiting for results...");
    await page.waitForSelector('text=China Vanke', { timeout: 15000 });

    console.log("Clicking FY23...");
    await page.click('button:has-text("FY23")');

    // Wait a brief moment to see if error triggers
    await page.waitForTimeout(2000);

    console.log("Script completed.");
    await browser.close();
})();
