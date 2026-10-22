import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test as base } from "@playwright/test";

/**
 * `test` with `expectAccessible(page)`: an axe scan for WCAG 2.1 A and AA,
 * colour contrast included, that fails the test on any violation. Every page a
 * test visits is scanned (constitution Principle V).
 */
export const test = base.extend<{ expectAccessible: (page: Page) => Promise<void> }>({
  expectAccessible: async ({}, use) => {
    await use(async (page) => {
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      const summary = results.violations.map(
        (v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(", ")})`,
      );
      expect(summary, `axe violations on ${page.url()}`).toEqual([]);
    });
  },
});

export { expect };

/** A user from engineering/mocks/cognito/db/local_licensing.json and engineering/api/seed/users.sql. */
export const ADMIN = {
  email: "gustavo.torrico@focusconsulting.io",
  password: "Local-Passw0rd!",
};
