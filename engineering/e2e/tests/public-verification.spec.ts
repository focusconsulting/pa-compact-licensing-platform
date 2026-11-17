import { expect, test } from "./fixtures";

// Reads the PAs `just seed demo` creates (engineering/docs/demo.md) and changes none of
// them. Nobody signs in: FLOW-08 is for anyone.
test.describe("Looking up a PA's Compact Privileges, with no account", () => {
  test("Anyone finds a PA by name and sees that their privilege is active", async ({
    page,
    expectAccessible,
  }) => {
    await test.step("Open the lookup page", async () => {
      await page.goto("/verify");
      await expect(
        page.getByRole("heading", { name: "Look up a Compact Privilege", level: 1 }),
      ).toBeVisible();
      await expectAccessible(page);
    });

    await test.step("Search by first and last name, in any letter case", async () => {
      await page.getByLabel("First name").fill("avery");
      await page.getByLabel("Last name").fill("ACTIVE");
      await page.getByRole("button", { name: "Search" }).click();
      await expect(page.getByRole("heading", { name: "Results (1)" })).toBeVisible();
      const row = page.getByRole("row", { name: /Avery Active/ });
      await expect(row).toContainText("Kansas");
      await expect(row).toContainText("Oklahoma");
      await expectAccessible(page);
    });

    await test.step("Open the PA and read their privilege", async () => {
      await page.getByRole("link", { name: "Avery Active" }).click();
      await expect(page.getByRole("heading", { name: "Avery Active", level: 1 })).toBeVisible();
      const card = page.getByRole("listitem").filter({ hasText: "Oklahoma" });
      await expect(card.getByText("Active", { exact: true })).toBeVisible();
      await expect(card.getByText(/^PA-OK-\d{6}$/)).toBeVisible();
      await expect(card.getByText(/^Expires: /)).toBeVisible();
      await expectAccessible(page);
    });

    await test.step("Go back to the results", async () => {
      await page.getByRole("link", { name: "Back to results" }).click();
      await expect(page.getByRole("link", { name: "Avery Active" })).toBeVisible();
      await expect(page.getByLabel("Last name")).toHaveValue("ACTIVE");
    });
  });

  test("Anyone finds the same PA by their Compact Privilege number", async ({
    page,
    expectAccessible,
  }) => {
    const number = await test.step("Read the number from the PA's page", async () => {
      await page.goto("/verify?first_name=Avery&last_name=Active");
      await page.getByRole("link", { name: "Avery Active" }).click();
      return page.getByText(/^PA-OK-\d{6}$/).innerText();
    });

    await test.step("Search by that number", async () => {
      await page.goto("/verify");
      // USWDS draws each radio on its label, so click the label as a person would.
      await page.locator('label[for="search-by-number"]').click();
      await page.getByRole("textbox", { name: "Compact Privilege number" }).fill(number);
      await page.getByRole("button", { name: "Search" }).click();
      await expect(page.getByRole("link", { name: "Avery Active" })).toBeVisible();
      await expectAccessible(page);
    });
  });

  test("An expired privilege says that it expired, and not when", async ({ page, expectAccessible }) => {
    await page.goto("/verify?first_name=Pia&last_name=Expired");
    await page.getByRole("link", { name: "Pia Expired" }).click();

    const card = page.getByRole("listitem").filter({ hasText: "Oklahoma" });
    await expect(card.getByText("Inactive", { exact: true })).toBeVisible();
    await expect(card.getByText("Expired", { exact: true })).toBeVisible();
    await expectAccessible(page);
  });

  for (const [who, first, last] of [
    ["a PA whose state license was suspended", "Lex", "License-Action"],
    ["a PA whose privilege was suspended", "Enzo", "Encumbered"],
  ]) {
    test(`An inactive privilege gives no reason: ${who}`, async ({ page, expectAccessible }) => {
      await page.goto(`/verify?first_name=${first}&last_name=${last}`);
      await page.getByRole("link", { name: `${first} ${last}` }).click();

      // The card, not the page: one demo PA's surname is itself a reason.
      const card = page.getByRole("listitem").filter({ hasText: "Oklahoma" });
      await expect(card.getByText("Inactive", { exact: true })).toBeVisible();
      await expect(card).not.toContainText(/suspen|adverse|encumber|deactivat|disciplin|expir/i);
      await expectAccessible(page);
    });
  }

  test("A search that matches no one says so, and what the search needs", async ({
    page,
    expectAccessible,
  }) => {
    await page.goto("/verify");
    await page.getByLabel("First name").fill("Avery");
    await page.getByLabel("Last name").fill("Activ");
    await page.getByRole("button", { name: "Search" }).click();

    await expect(page.getByRole("heading", { name: "Results (0)" })).toBeVisible();
    await expect(
      page.getByText(/No PA with a Compact Privilege is named Avery Activ\./),
    ).toBeVisible();
    await expectAccessible(page);
  });

  test("A PA with no privilege is not listed", async ({ page }) => {
    await page.goto("/verify?first_name=Sam&last_name=Submitted");

    await expect(page.getByRole("heading", { name: "Results (0)" })).toBeVisible();
  });

  test("An address that names no PA says the PA couldn't be found", async ({
    page,
    expectAccessible,
  }) => {
    await page.goto("/verify/practitioner?id=00000000-0000-4000-8000-000000000000");

    await expect(
      page.getByRole("heading", { name: "We couldn't find that PA", level: 1 }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Look up another PA" })).toBeVisible();
    await expectAccessible(page);
  });
});
