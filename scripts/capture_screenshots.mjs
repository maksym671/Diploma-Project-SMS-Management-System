// Captures the screenshots used by the defence deck straight from a running
// development server, so the slides always show the real interface.
//
//   npm i puppeteer-core
//   python manage.py runserver
//   node scripts/capture_screenshots.mjs <sessionid>
//
// The session key comes from an authenticated Django session; CHROME points at
// the browser downloaded by Puppeteer.
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { mkdirSync } from 'node:fs';

import puppeteer from 'puppeteer-core';

const CHROME = `${process.env.HOME}/.cache/puppeteer/chrome/mac_arm-131.0.6778.204/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const BASE = 'http://127.0.0.1:8000';
const SESSION = process.argv[2];
const OUT = resolve(dirname(fileURLToPath(import.meta.url)), '../docs/screenshots');

mkdirSync(OUT, { recursive: true });

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  userDataDir: resolve(OUT, '../.chrome-profile'),
  args: [
    '--force-color-profile=srgb',
    '--font-render-hinting=none',
    '--disable-crashpad',
    '--no-sandbox',
  ],
});

async function shot(page, path, file, { dark = false, lang = 'en' } = {}) {
  await page.setCookie(
    { name: 'sessionid', value: SESSION, domain: '127.0.0.1', path: '/' },
    { name: 'django_language', value: lang, domain: '127.0.0.1', path: '/' },
  );
  await page.goto(BASE + path, { waitUntil: 'networkidle0' });
  await page.evaluate((d) => {
    localStorage.setItem('sms-theme', d ? 'dark' : 'light');
  }, dark);
  await page.goto(BASE + path, { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, 1400));
  await page.screenshot({ path: `${OUT}/${file}.png` });
  console.log('saved', file);
}

const page = await browser.newPage();
await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 2 });

await shot(page, '/', 'dashboard-light');
await shot(page, '/', 'dashboard-dark', { dark: true });
await shot(page, '/students/', 'students-list');
await shot(page, '/grades/', 'grades-list');
await shot(page, '/courses/', 'courses-list');
await shot(page, '/students/1/', 'student-detail');
await shot(page, '/', 'dashboard-pl', { lang: 'pl' });

const anon = await browser.createBrowserContext();
const loginPage = await anon.newPage();
await loginPage.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 2 });
await loginPage.goto(BASE + '/login/', { waitUntil: 'networkidle0' });
await new Promise((r) => setTimeout(r, 800));
await loginPage.screenshot({ path: `${OUT}/login.png` });
console.log('saved login');

const mobile = await anon.newPage();
await mobile.setViewport({ width: 430, height: 932, deviceScaleFactor: 3 });
await mobile.setCookie({ name: 'sessionid', value: SESSION, domain: '127.0.0.1', path: '/' });
await mobile.goto(BASE + '/', { waitUntil: 'networkidle0' });
await new Promise((r) => setTimeout(r, 1400));
await mobile.screenshot({ path: `${OUT}/dashboard-mobile.png` });
console.log('saved mobile');

await browser.close();
