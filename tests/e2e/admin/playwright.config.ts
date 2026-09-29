import { defineConfig, devices } from '@playwright/test';

export const BASE_URL = process.env.ADMIN_BASE_URL ?? 'http://127.0.0.1:8000';
export const STORAGE_STATE = '.auth/admin.json';

export default defineConfig({
  testDir: './specs',
  // Every spec shares one database, and 03-create seeds the rows 04/05/06 depend on.
  // Playwright runs files in path order, so the numeric prefixes are the schedule.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  globalSetup: require.resolve('./global-setup'),
  globalTeardown: require.resolve('./global-teardown'),
  reporter: [
    ['list'],
    ['html', { outputFolder: 'reports/html', open: 'never' }],
    ['json', { outputFile: 'reports/results.json' }],
  ],
  outputDir: 'reports/artifacts',
  use: {
    baseURL: BASE_URL,
    storageState: STORAGE_STATE,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // >= 1536px (Tailwind 2xl): below it unfold hides the changelist filter panel
    // behind a toggle button (change_list_filter_vertical.html uses `2xl:block`).
    viewport: { width: 1920, height: 1080 },
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
    acceptDownloads: true,
  },
  projects: [
    {
      name: 'chromium',
      // `channel: 'chromium'` runs the full browser build rather than
      // chrome-headless-shell, which Playwright would otherwise require as a
      // separate download.
      use: { ...devices['Desktop Chrome'], channel: 'chromium' },
    },
  ],
});
