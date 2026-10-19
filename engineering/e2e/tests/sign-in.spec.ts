import { ADMIN, expect, test } from "./fixtures";

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
      await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
      await expect(page.getByText(ADMIN.email)).toBeVisible();
      await expect(page.getByText("Gustavo Torrico")).toBeVisible();
      await expect(page.getByRole("cell", { name: "admin" })).toBeVisible();
      await expectAccessible(page);
    });
  });

  test("A wrong password is refused with a message, and the user stays on the sign-in page", async ({
    page,
    expectAccessible,
  }) => {
    await page.goto("/login");
    await page.getByLabel("Email address").fill(ADMIN.email);
    await page.getByLabel("Password").fill("Not-the-passw0rd");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByText("Incorrect username or password.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
    await expectAccessible(page);
  });
});
