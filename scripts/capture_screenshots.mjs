// Captures the screenshots used by the defence deck straight from a running
// development server, so the slides always show the real interface.
//
//   npm i puppeteer-core
//   python manage.py runserver
//   node scripts/capture_screenshots.mjs <sessionid> [name ...]
//
// Naming one or more shots re-takes only those; with no names it takes all of
// them. SMS_BASE overrides the server URL when the port is not 8000.
//
// The session key comes from an authenticated Django session; CHROME points at
// the browser downloaded by Puppeteer.
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { mkdirSync } from 'node:fs';

import puppeteer from 'puppeteer-core';

const CHROME = `${process.env.HOME}/.cache/puppeteer/chrome/mac_arm-131.0.6778.204/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing`;
const BASE = process.env.SMS_BASE || 'http://127.0.0.1:8000';
const SESSION = process.argv[2];
const ONLY = new Set(process.argv.slice(3));
const wanted = (name) => ONLY.size === 0 || ONLY.has(name);
const HOST = new URL(BASE).hostname;
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
  if (!wanted(file)) return;
  await page.setCookie(
    { name: 'sessionid', value: SESSION, domain: HOST, path: '/' },
    { name: 'django_language', value: lang, domain: HOST, path: '/' },
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
await shot(page, '/attendance/', 'attendance-list');
// A loaded roster, so the slide shows the bulk marking screen doing its job.
await shot(page, '/attendance/mark/?course=5&date=2026-05-25', 'attendance-mark-class');
await shot(page, '/teachers/', 'teachers-list');
await shot(page, '/students/1/', 'student-detail');
await shot(page, '/', 'dashboard-pl', { lang: 'pl' });

if (wanted('login')) {
const anon = await browser.createBrowserContext();
const loginPage = await anon.newPage();
await loginPage.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 2 });
await loginPage.goto(BASE + '/login/', { waitUntil: 'networkidle0' });
await new Promise((r) => setTimeout(r, 800));
await loginPage.screenshot({ path: `${OUT}/login.png` });
console.log('saved login');
await anon.close();
}

if (wanted('dashboard-mobile')) {
const anon2 = await browser.createBrowserContext();
const mobile = await anon2.newPage();
await mobile.setViewport({ width: 430, height: 932, deviceScaleFactor: 3 });
await mobile.setCookie({ name: 'sessionid', value: SESSION, domain: HOST, path: '/' });
await mobile.goto(BASE + '/', { waitUntil: 'networkidle0' });
await new Promise((r) => setTimeout(r, 1400));
await mobile.screenshot({ path: `${OUT}/dashboard-mobile.png` });
console.log('saved mobile');
await anon2.close();
}

await browser.close();
