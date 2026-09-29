import { test as base } from '@playwright/test';
import { PageProbe } from './health';

/**
 * Every test gets a probe wired to its page, so console errors, failed requests
 * and bad subresources are captured without each spec remembering to.
 */
export const test = base.extend<{ probe: PageProbe }>({
  probe: async ({ page }, use) => {
    await use(new PageProbe(page));
  },
});

export { expect } from '@playwright/test';
