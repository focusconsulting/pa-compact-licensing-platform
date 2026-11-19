import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test as base } from "@playwright/test";

/**
 * `test` with `expectAccessible(page)`: an axe scan for WCAG 2.1 A and AA,
 * colour contrast included, that fails the test on any violation. Every page a
 * test visits is scanned (constitution Principle V).
 */
export const test = base.extend<{ expectAccessible: (page: Page) => Promise<void> }>({
  // Fails any test that loads a page without a Content-Security-Policy, or whose pages
  // break it. The first check keeps the second from passing against a server that sends
  // no policy, such as `next dev`.
  page: async ({ page }, use) => {
    const unprotected: string[] = [];
    const violations: string[] = [];
    page.on("response", (response) => {
      const request = response.request();
      const isPage = request.isNavigationRequest() && request.frame() === page.mainFrame();
      if (isPage && response.status() < 300 && !response.headers()["content-security-policy"]) {
        unprotected.push(response.url());
      }
    });
    await page.exposeFunction("reportPolicyViolation", (violation: string) => {
      violations.push(violation);
    });
    await page.addInitScript(() => {
      document.addEventListener("securitypolicyviolation", (event) => {
        const report = (window as unknown as { reportPolicyViolation: (violation: string) => void })
          .reportPolicyViolation;
        report(`${event.effectiveDirective} blocked ${event.blockedURI} on ${event.documentURI}`);
      });
    });

    await use(page);

    expect(unprotected, "pages served without a Content-Security-Policy").toEqual([]);
    expect(violations, "Content-Security-Policy violations").toEqual([]);
  },

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

/** The password every login in the local Cognito mock uses (engineering/docs/demo.md). */
const LOCAL_PASSWORD = "Local-Passw0rd!";

/** A practitioner from `just seed demo`, signed in as `<first name>.<surname>@demo.example`. */
export function demoPa(name: string) {
  return { email: `${name}@demo.example`, password: LOCAL_PASSWORD };
}

/** Signs in through the sign-in page and waits to leave it. */
export async function signIn(page: Page, user: { email: string; password: string }) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(user.email);
  await page.getByLabel("Password").fill(user.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL((url) => url.pathname !== "/login");
}
