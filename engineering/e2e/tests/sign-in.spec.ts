import { ADMIN, expect, signIn, test } from "./fixtures";

test.describe("Signing in", () => {
  test("A registered user signs in and sees their account on the dashboard", async ({
    page,
    expectAccessible,
  }) => {
    await test.step("Open the sign-in page", async () => {
      await page.goto("/login");
      await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
      await expectAccessible(page);
    });

    await test.step("Sign in with their email and password", async () => {
      await page.getByLabel("Email address").fill(ADMIN.email);
      await page.getByLabel("Password").fill(ADMIN.password);
      await page.getByRole("button", { name: "Sign in" }).click();
    });

    await test.step("See their name, email, and role on the dashboard", async () => {
      await expect(page).toHaveURL("/dashboard");
      const dashboard = page.getByRole("main");
      await expect(dashboard.getByRole("heading", { name: "Dashboard" })).toBeVisible();
      await expect(dashboard.getByText(ADMIN.email)).toBeVisible();
      await expect(dashboard.getByText("Gustavo Torrico")).toBeVisible();
      await expect(dashboard.getByRole("cell", { name: "admin" })).toBeVisible();
      await expect(page.getByRole("banner").getByText("Gustavo Torrico")).toBeVisible();
      await expectAccessible(page);
    });
  });

  test("A visitor reaches sign-in from the front door", async ({ page, expectAccessible }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "PA Compact", level: 1 })).toBeVisible();
    await expectAccessible(page);

    await page.getByRole("link", { name: "Sign in as staff" }).click();

    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  });

  test("A signed-in user's own card on the front door leads to their dashboard", async ({
    page,
    expectAccessible,
  }) => {
    await signIn(page, ADMIN);
    await page.getByRole("link", { name: "PA Compact" }).first().click();

    const own = page.getByRole("link", { name: "Go to your dashboard" });
    await expect(own).toBeVisible();
    await expectAccessible(page);
    await own.click();

    await expect(page).toHaveURL("/dashboard");
  });

  test("A wrong password is refused with a message, and the user stays on the sign-in page", async ({
    page,
    expectAccessible,
  }) => {
    await page.goto("/login");
    await page.getByLabel("Email address").fill(ADMIN.email);
    await page.getByLabel("Password").fill("Not-the-passw0rd");
    await page.getByRole("button", { name: "Sign in" }).click();

    // The wording is the identity provider's, and cognito-local's differs from Cognito's (ADR-0010).
    await expect(page.getByRole("heading", { name: "Error" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expectAccessible(page);
  });
});
