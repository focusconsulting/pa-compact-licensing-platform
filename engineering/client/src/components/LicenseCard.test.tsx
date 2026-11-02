import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CardGroup } from "@trussworks/react-uswds";

import { expectNoAxeViolations } from "src/tests/axe";
import CardActionMenu from "./CardActionMenu";
import LicenseCard, { type LicenseCardProps } from "./LicenseCard";

const BASE: LicenseCardProps = {
  state: "Sample State",
  number: "PA-000123",
  status: "active",
  expires: "2027-06-30",
};

function renderCard(props: Partial<LicenseCardProps> = {}) {
  return render(
    <CardGroup>
      <LicenseCard
        state={props.state ?? BASE.state}
        number={props.number ?? BASE.number}
        status={props.status ?? BASE.status}
        expires={props.expires ?? BASE.expires}
        view={props.view}
        discipline={props.discipline}
        note={props.note}
        actions={props.actions}
      />
    </CardGroup>,
  );
}

describe("LicenseCard", () => {
  it("names the state and shows the license's number and expiry", async () => {
    const { container } = renderCard();

    expect(
      screen.getByRole("heading", { level: 3, name: "Sample State" }),
    ).toBeInTheDocument();
    expect(screen.getByText("PA-000123")).toBeInTheDocument();
    expect(screen.getByText("Jun 30, 2027")).toBeInTheDocument();
    expect(screen.queryByText(/Discipline status/)).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("shows the public the pill and staff the computed status", () => {
    renderCard({ status: "encumbered" });
    expect(screen.getByText("Inactive")).toBeInTheDocument();

    renderCard({ status: "encumbered", view: "staff" });
    expect(screen.getByText("Encumbered")).toBeInTheDocument();
  });

  it("shows the discipline status, the state's note, and staff actions", () => {
    renderCard({
      discipline: "Probation",
      note: "Under review by the board.",
      actions: (
        <CardActionMenu
          record="Sample State license"
          actions={[
            { key: "x", label: "Report discipline", onSelect: vi.fn() },
          ]}
        />
      ),
    });

    expect(screen.getByText("Probation")).toBeInTheDocument();
    expect(screen.getByText("Under review by the board.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Actions for Sample State license" }),
    ).toBeInTheDocument();
  });
});
