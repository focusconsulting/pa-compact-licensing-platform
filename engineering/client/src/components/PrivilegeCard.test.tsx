import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { CardGroup } from "@trussworks/react-uswds";

import { expectNoAxeViolations } from "src/tests/axe";
import PrivilegeCard, { type PrivilegeCardProps } from "./PrivilegeCard";

const BASE: PrivilegeCardProps = {
  state: "Kansas",
  number: "PA-KS-000001",
  status: "active",
  activeFrom: "2026-11-02",
  expires: "2027-06-30",
};

function renderCard(props: Partial<PrivilegeCardProps> = {}) {
  return render(
    <CardGroup>
      <PrivilegeCard
        state={BASE.state}
        number={BASE.number}
        status={props.status ?? BASE.status}
        activeFrom={BASE.activeFrom}
        expires={BASE.expires}
        view={props.view}
        discipline={props.discipline}
        detailsHref={props.detailsHref}
      />
    </CardGroup>,
  );
}

describe("PrivilegeCard", () => {
  it("names the state and shows the privilege's number and start", async () => {
    const { container } = renderCard({ detailsHref: "/privileges/1" });

    expect(
      screen.getByRole("heading", { level: 3, name: "Kansas" }),
    ).toBeInTheDocument();
    expect(screen.getByText("PA-KS-000001")).toBeInTheDocument();
    expect(screen.getByText("Nov 2, 2026")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View details for Kansas" }),
    ).toHaveAttribute("href", "/privileges/1");
    await expectNoAxeViolations(container);
  });

  it("follows an active privilege's tag with when it expires", () => {
    renderCard();

    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Expires: Jun 30, 2027")).not.toHaveClass(
      "text-error-dark",
    );
  });

  it("marks an expired privilege's date in red", () => {
    renderCard({ status: "expired" });

    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(screen.getByText("Expired: Jun 30, 2027")).toHaveClass(
      "text-error-dark",
    );
  });

  it("says a deactivated privilege was deactivated", () => {
    renderCard({ status: "inactive", view: "staff" });

    expect(screen.getByText("Deactivated")).toBeInTheDocument();
  });

  it("gives an encumbered privilege no qualifier, and staff its status", () => {
    renderCard({
      status: "encumbered",
      view: "staff",
      discipline: "Suspension",
    });

    expect(screen.getByText("Encumbered")).toBeInTheDocument();
    expect(screen.queryByText(/Expires|Expired|Deactivated/)).toBeNull();
    expect(screen.getByText("Suspension")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull();
  });
});
