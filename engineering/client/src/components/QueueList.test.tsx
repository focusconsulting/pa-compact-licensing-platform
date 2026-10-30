import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { expectNoAxeViolations } from "src/tests/axe";
import type { Column } from "./DataTable";
import QueueList, { daysSince } from "./QueueList";

interface Row {
  id: string;
  name: string;
  received: string;
}

const COLUMNS: Column<Row>[] = [
  { key: "name", header: "Name", cell: (row) => row.name },
  { key: "received", header: "Received", cell: (row) => row.received },
];

const RILEY: Row = { id: "1", name: "Riley Sample", received: "2026-10-15" };
const JORDAN: Row = { id: "2", name: "Jordan Sample", received: "2026-10-29" };

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(2026, 9, 30, 9, 0));
});
afterEach(() => vi.useRealTimers());

describe("daysSince", () => {
  it("counts whole calendar days to today", () => {
    expect(daysSince("2026-10-30")).toBe(0);
    expect(daysSince("2026-10-29")).toBe(1);
    expect(daysSince("2026-10-15")).toBe(15);
  });
});

describe("QueueList", () => {
  it("heads the group with its name and count, then lists its records", async () => {
    const { container } = render(
      <QueueList
        heading="Needs work"
        intro="Check each one."
        columns={COLUMNS}
        rows={[RILEY, JORDAN]}
        rowKey={(row) => row.id}
        empty="Nothing needs work."
      />,
    );

    expect(
      screen.getByRole("heading", { level: 2, name: "Needs work (2)" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Check each one.")).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Needs work (2)" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Age" })).toBeNull();
    expect(screen.queryByText("Nothing needs work.")).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("adds each record's age", () => {
    render(
      <QueueList
        heading="Needs work"
        columns={COLUMNS}
        rows={[RILEY, JORDAN]}
        rowKey={(row) => row.id}
        receivedOn={(row) => row.received}
        empty="Nothing needs work."
      />,
    );

    expect(
      screen.getByRole("columnheader", { name: "Age" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "15 days" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "1 day" })).toBeInTheDocument();
  });

  it("says so when the group is empty", () => {
    render(
      <QueueList
        heading="Ready to approve"
        columns={COLUMNS}
        rows={[]}
        rowKey={(row) => row.id}
        empty="No applications are ready to approve."
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Ready to approve (0)" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
    expect(
      screen.getByText("No applications are ready to approve."),
    ).toBeInTheDocument();
  });

  it("shows what it's filtered by, and clears it", async () => {
    vi.useRealTimers();
    const onClearFilters = vi.fn();
    const { container } = render(
      <QueueList
        heading="Applications to review"
        columns={COLUMNS}
        rows={[RILEY]}
        rowKey={(row) => row.id}
        empty="None."
        filters={["Needs work", "Oct 2026"]}
        onClearFilters={onClearFilters}
      />,
    );

    const chip = screen.getByText("Viewing:");
    expect(within(chip).getByText("Needs work, Oct 2026")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: "Clear filters" }),
    );
    expect(onClearFilters).toHaveBeenCalled();
    await expectNoAxeViolations(container);
  });

  it("shows no chip without filters", () => {
    render(
      <QueueList
        heading="Needs work"
        columns={COLUMNS}
        rows={[RILEY]}
        rowKey={(row) => row.id}
        empty="None."
        filters={[]}
      />,
    );

    expect(screen.queryByText("Viewing:")).toBeNull();
  });
});
