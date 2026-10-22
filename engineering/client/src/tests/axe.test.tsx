import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { expectNoAxeViolations } from "./axe";

describe("expectNoAxeViolations", () => {
  it("reports a real violation, so a passing run means something", async () => {
    const { container } = render(<input type="text" />);
    await expect(expectNoAxeViolations(container)).rejects.toThrow(/label/);
  });
});
