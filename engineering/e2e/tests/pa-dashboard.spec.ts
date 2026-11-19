import { demoPa, expect, signIn, test } from "./fixtures";

// Reads the PAs `just seed demo` creates (engineering/docs/demo.md) and changes none of them.
test.describe("A PA's dashboard", () => {
  test("An application under review says when it was sent, and offers to withdraw it", async ({
    page,
    expectAccessible,
  }) => {
    await signIn(page, demoPa("sam.submitted"));

    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { name: "Dashboard", level: 1 })).toBeVisible();
    await expect(main.getByText("Under review")).toBeVisible();
    await expect(main.getByText(/Sent to Kansas on/)).toBeVisible();
    await expect(main.getByText(/through Kansas' process/)).toBeVisible();
    await expect(main.getByRole("button", { name: "Withdraw application" })).toBeVisible();
    await expectAccessible(page);
  });

  test("A denial says how to appeal", async ({ page, expectAccessible }) => {
    await signIn(page, demoPa("dee.denied"));

    const main = page.getByRole("main");
    await expect(main.getByText("Not eligible", { exact: true })).toBeVisible();
    await expect(main.getByText(/You can appeal to Kansas/)).toBeVisible();
    await expectAccessible(page);
  });

  test("A withdrawn application says when", async ({ page, expectAccessible }) => {
    await signIn(page, demoPa("wren.withdrawn"));

    const main = page.getByRole("main");
    await expect(main.getByText(/Withdrawn on/)).toBeVisible();
    await expectAccessible(page);
  });

  test("An eligible PA sees their license, when Kansas verified it, and their privileges", async ({
    page,
    expectAccessible,
  }) => {
    await signIn(page, demoPa("avery.active"));

    const main = page.getByRole("main");
    await expect(main.getByRole("heading", { name: "Your qualifying license" })).toBeVisible();
    await expect(main.getByText(/Verified by Kansas/)).toBeVisible();
    await expect(main.getByRole("heading", { name: "Your Compact Privileges" })).toBeVisible();
    await expectAccessible(page);
  });

  test("A barred PA is told why they can't apply, not sent to apply", async ({
    page,
    expectAccessible,
  }) => {
    await signIn(page, demoPa("bea.barred-until"));

    await expect(page.getByText(/You can't apply to join the PA Compact yet/)).toBeVisible();
    await expect(page).toHaveURL("/dashboard");
    await expectAccessible(page);
  });

  test("A PA with a draft goes back to their application", async ({ page }) => {
    await signIn(page, demoPa("dana.draft"));

    await expect(page).toHaveURL(/\/application$/);
  });
});
