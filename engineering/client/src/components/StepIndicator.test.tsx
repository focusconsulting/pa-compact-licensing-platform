import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { expectNoAxeViolations } from "src/tests/axe";
import StepIndicator from "./StepIndicator";

const STEPS = ["Your license and details", "Statements and submit", "Review"];

const segment = (label: string) => screen.getAllByText(label)[0].closest("li");

describe("StepIndicator", () => {
  it("marks steps before the current one complete, and those after it not", async () => {
    const { container } = render(<StepIndicator steps={STEPS} current={1} />);

    expect(segment(STEPS[0])).toHaveClass(
      "usa-step-indicator__segment--complete",
    );
    expect(segment(STEPS[1])).toHaveClass(
      "usa-step-indicator__segment--current",
    );
    expect(segment(STEPS[2])).not.toHaveClass(
      "usa-step-indicator__segment--complete",
      "usa-step-indicator__segment--current",
    );
    await expectNoAxeViolations(container);
  });

  it("heads with the current step, at h2 unless told otherwise", () => {
    render(<StepIndicator steps={STEPS} current={0} />);

    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
      /Step\s*1\s*of 3\s*Your license and details/,
    );
  });

  it("takes another heading level", () => {
    render(<StepIndicator steps={STEPS} current={0} headingLevel="h3" />);

    expect(screen.getByRole("heading", { level: 3 })).toBeInTheDocument();
  });
});
