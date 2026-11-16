import { demoPa, expect, signIn, test } from "./fixtures";

// Submits an application for Ned Bar-Ended, whose bar has ended and who has none yet. Run it on
// a fresh `just seed demo`: once Ned has applied, a second run finds his application under review.
test("A PA applies to join, signs the statements, and sees their application under review", async ({
  page,
  expectAccessible,
}) => {
  await signIn(page, demoPa("ned.bar-ended"));

  await test.step("The dashboard sends them to apply, which starts by explaining how", async () => {
    await expect(page).toHaveURL(/\/application$/);
    await expect(page.getByRole("heading", { name: "Join the PA Compact" })).toBeVisible();
    await expectAccessible(page);
    await page.getByRole("button", { name: "Start your application" }).click();
  });

  await test.step("Step 1 keeps their profile, and asks for their state and license", async () => {
    await expect(page.getByRole("textbox", { name: /Address Line 1/ })).toHaveValue(
      "100 Sample Street",
    );
    await page.getByRole("combobox", { name: "State *", exact: true }).selectOption("KS");
    await page.getByRole("textbox", { name: /License number/ }).fill("KS-PA-12345");
    const expires = page.getByRole("group", { name: "License expiration date" });
    await expires.getByRole("combobox").selectOption("12");
    await expires.getByRole("textbox", { name: /Day/ }).fill("31");
    await expires.getByRole("textbox", { name: /Year/ }).fill("2027");
    await expectAccessible(page);
    await page.getByRole("button", { name: "Continue" }).click();
  });

  await test.step("Step 2 has them accept each statement and sign", async () => {
    await expect(page.getByRole("heading", { name: "Statements and submit", level: 1 })).toBeVisible();
    await expect(page.getByText(/through Kansas' process/)).toBeVisible();
    // USWDS draws each checkbox on its label, so click the label as a person would.
    for (const checkbox of await page.getByRole("checkbox").all()) {
      await page.locator(`label[for="${await checkbox.getAttribute("id")}"]`).click();
      await expect(checkbox).toBeChecked();
    }
    await page.getByRole("textbox", { name: /Type your full legal name/ }).fill("Ned Bar-Ended");
    await expectAccessible(page);
    await page.getByRole("button", { name: "Submit application" }).click();
  });

  await test.step("The receipt says what happens next, and the dashboard shows it under review", async () => {
    await expect(page.getByRole("heading", { name: "Application received" })).toBeVisible();
    await expectAccessible(page);
    await page.getByRole("link", { name: "Dashboard" }).click();
    await expect(page.getByRole("main").getByText("Under review")).toBeVisible();
  });
});
