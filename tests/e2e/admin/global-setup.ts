import fs from 'fs';
import path from 'path';
import { chromium, type FullConfig } from '@playwright/test';
import { BASE_URL, STORAGE_STATE } from './playwright.config';
import { LEDGER_PATH } from './src/health';
import { loadInventory } from './src/inventory';
import { newRunId, writeRunMeta } from './src/run-scope';

const USERNAME = process.env.ADMIN_USERNAME ?? 'admin';
const PASSWORD = process.env.ADMIN_PASSWORD ?? 'admin';

export default async function globalSetup(_config: FullConfig): Promise<void> {
  // Fail loudly and early if the inventory was never generated.
  const inventory = loadInventory();

  fs.mkdirSync(path.dirname(LEDGER_PATH), { recursive: true });
  fs.writeFileSync(LEDGER_PATH, '');

  const runId = process.env.RUN_ID ?? newRunId();
  writeRunMeta(runId);

  const browser = await chromium.launch({ channel: 'chromium' });
  const page = await browser.newPage({ baseURL: BASE_URL });

  await page.goto(inventory.login);
  // db.User extends AbstractUser, so USERNAME_FIELD is `username`.
  await page.fill('input[name="username"]', USERNAME);
  await page.fill('input[name="password"]', PASSWORD);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.includes('/login/'), { timeout: 30_000 }),
    page.click('input[type="submit"], button[type="submit"]'),
  ]);

  const stillOnLogin = page.url().includes('/login/');
  if (stillOnLogin) {
    const error = await page.locator('.errornote, .errorlist').allTextContents();
    await browser.close();
    throw new Error(`Admin login failed for "${USERNAME}": ${error.join(' ') || 'no error shown'}`);
  }

  fs.mkdirSync(path.dirname(STORAGE_STATE), { recursive: true });
  await page.context().storageState({ path: STORAGE_STATE });
  await browser.close();

  console.log(
    `Logged in as ${USERNAME}; run ${runId}; ${inventory.models.length} admin models in inventory.`,
  );
}
