import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { expectNoAxeViolations } from "src/tests/axe";
import HistoryTimeline from "./HistoryTimeline";

const EVENTS = [
  {
    id: "1",
    on: "2026-10-14",
    what: "Application submitted",
    by: "Jordan Sample",
  },
  {
    id: "3",
    on: "2026-10-20T15:00:00Z",
    what: "Decision recorded: Eligible",
    by: "Taylor Sample",
  },
  {
    id: "2",
    on: "2026-10-20T14:00:00Z",
    what: "Each requirement and the license checked",
    by: "Taylor Sample",
  },
];

describe("HistoryTimeline", () => {
  it("lists what happened, newest first, with the date and who did it", async () => {
    const { container } = render(<HistoryTimeline events={EVENTS} />);

    expect(screen.getByRole("table", { name: "History" })).toBeInTheDocument();
    expect(
      screen.getAllByRole("columnheader").map((cell) => cell.textContent),
    ).toEqual(["Date", "What happened", "By"]);
    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((row) => row.textContent)).toEqual([
      "Oct 20, 2026Decision recorded: EligibleTaylor Sample",
      "Oct 20, 2026Each requirement and the license checkedTaylor Sample",
      "Oct 14, 2026Application submittedJordan Sample",
    ]);
    await expectNoAxeViolations(container);
  });

  it("takes another name", () => {
    render(<HistoryTimeline events={EVENTS} caption="Privilege history" />);

    expect(
      screen.getByRole("table", { name: "Privilege history" }),
    ).toBeInTheDocument();
  });
});
