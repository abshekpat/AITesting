import { Locator, Page, expect } from '@playwright/test';

/** Custom wait conditions that go beyond Playwright's built-in auto-waiting. */
export class WaitHelper {
  constructor(private readonly page: Page) {}

  async waitForCount(locator: Locator, count: number, timeoutMs = 10_000) {
    await expect(locator).toHaveCount(count, { timeout: timeoutMs });
  }

  async waitForNetworkIdle(timeoutMs = 10_000) {
    await this.page.waitForLoadState('networkidle', { timeout: timeoutMs });
  }

  async waitForUrlContains(fragment: string, timeoutMs = 10_000) {
    await this.page.waitForURL((url) => url.toString().includes(fragment), { timeout: timeoutMs });
  }

  async waitForEnabled(locator: Locator, timeoutMs = 10_000) {
    await expect(locator).toBeEnabled({ timeout: timeoutMs });
  }
}