import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { expectNoAxeViolations } from "src/tests/axe";
import AlertBanner from "./AlertBanner";
import CaseLayout, { CaseSection } from "./CaseLayout";

const CRUMBS = [
  { label: "Home", href: "/" },
  { label: "Applications to review", href: "/applications" },
];

describe("CaseLayout", () => {
  it("leads from the trail to the record's name, then its sections", async () => {
    const { container } = render(
      <CaseLayout
        breadcrumbs={CRUMBS}
        title="Jordan Sample"
        subtitle="Received Oct 14, 2026"
      >
        <CaseSection heading="License details">
          <p>PA-000123</p>
        </CaseSection>
        <CaseSection heading="Your review">
          <p>Decide.</p>
        </CaseSection>
      </CaseLayout>,
    );

    const trail = screen.getByRole("navigation", { name: "Breadcrumbs" });
    expect(
      within(trail)
        .getAllByRole("link")
        .map((link) => [link.textContent, link.getAttribute("href")]),
    ).toEqual([
      ["Home", "/"],
      ["Applications to review", "/applications"],
    ]);
    expect(
      within(trail).getByText("Jordan Sample").closest("li"),
    ).toHaveAttribute("aria-current", "page");
    expect(
      screen.getByRole("heading", { level: 1, name: "Jordan Sample" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Received Oct 14, 2026")).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent),
    ).toEqual(["License details", "Your review"]);
    await expectNoAxeViolations(container);
  });

  it("puts a banner above the sections, and no line under the name unless given", () => {
    render(
      <CaseLayout
        breadcrumbs={CRUMBS}
        title="Jordan Sample"
        banner={
          <AlertBanner type="info" slim>
            Note.
          </AlertBanner>
        }
      >
        <CaseSection heading="History">
          <p>None.</p>
        </CaseSection>
      </CaseLayout>,
    );

    const name = screen.getByRole("heading", { level: 1 });
    expect(name.nextElementSibling).toHaveClass("usa-alert");
  });
});
