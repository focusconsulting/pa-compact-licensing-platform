import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { expectNoAxeViolations } from "src/tests/axe";
import AlertBanner from "./AlertBanner";

describe("AlertBanner", () => {
  it("shows a heading and text, announced politely", async () => {
    const { container } = render(
      <AlertBanner type="success" heading="Decision recorded">
        PA Compact emailed Jordan Sample.
      </AlertBanner>,
    );

    const alert = screen.getByRole("status");
    expect(alert).toHaveClass("usa-alert--success");
    expect(
      screen.getByRole("heading", { level: 2, name: "Decision recorded" }),
    ).toBeInTheDocument();
    expect(screen.getByText("PA Compact emailed Jordan Sample.")).toHaveClass(
      "usa-alert__text",
    );
    await expectNoAxeViolations(container);
  });

  it.each(["error", "emergency"] as const)(
    "announces an %s at once",
    (type) => {
      render(<AlertBanner type={type} heading="Something went wrong" />);

      expect(screen.getByRole("alert")).toHaveClass(`usa-alert--${type}`);
    },
  );

  it("takes the heading level that fits the page", () => {
    render(<AlertBanner type="info" heading="Note" headingLevel="h3" />);

    expect(screen.getByRole("heading", { level: 3 })).toBeInTheDocument();
  });

  it("can be one slim line with no heading", () => {
    render(
      <AlertBanner type="info" slim>
        No license record on file.
      </AlertBanner>,
    );

    expect(screen.getByRole("status")).toHaveClass("usa-alert--slim");
    expect(screen.queryByRole("heading")).toBeNull();
  });
});
