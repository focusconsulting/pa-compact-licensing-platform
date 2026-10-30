import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { expectNoAxeViolations } from "src/tests/axe";
import PageHeading from "./PageHeading";

describe("PageHeading", () => {
  it("is the page's h1", () => {
    render(<PageHeading title="Applications to review" />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Applications to review" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("paragraph")).toBeNull();
  });

  it("shows the intro line under it when there is one", async () => {
    const { container } = render(
      <PageHeading title="Sample State" intro="PAs who chose Sample State." />,
    );

    expect(screen.getByText("PAs who chose Sample State.")).toHaveClass(
      "usa-intro",
    );
    await expectNoAxeViolations(container);
  });
});
