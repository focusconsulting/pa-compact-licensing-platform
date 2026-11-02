import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Button } from "@trussworks/react-uswds";

import { expectNoAxeViolations } from "src/tests/axe";
import EmptyState from "./EmptyState";

describe("EmptyState", () => {
  it("says what isn't here yet", () => {
    render(<EmptyState>No applications are ready to approve.</EmptyState>);

    expect(
      screen.getByText("No applications are ready to approve."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("offers the next step where the design has one", async () => {
    const { container } = render(
      <EmptyState action={<Button type="button">Apply for privileges</Button>}>
        You don&apos;t have any privileges yet.
      </EmptyState>,
    );

    expect(
      screen.getByRole("button", { name: "Apply for privileges" }),
    ).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });
});
