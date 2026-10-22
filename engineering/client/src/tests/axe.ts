import axe from "axe-core";
import { expect } from "vitest";

/**
 * Fails the test if axe finds WCAG 2 A/AA violations in `container`.
 * jsdom has no layout or computed colours, so colour contrast is checked in
 * a real browser by the end-to-end tests instead (`engineering/e2e`).
 */
export async function expectNoAxeViolations(container: Element): Promise<void> {
  const results = await axe.run(container, {
    runOnly: {
      type: "tag",
      values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
    },
    rules: { "color-contrast": { enabled: false } },
  });
  const summary = results.violations.map(
    (v) =>
      `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(" ")).join(", ")})`,
  );
  expect(summary, `axe violations:\n${summary.join("\n")}`).toEqual([]);
}
