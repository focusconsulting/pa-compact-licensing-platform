import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";

import { expectNoAxeViolations } from "src/tests/axe";
import DataTable, { type Column } from "./DataTable";

interface Row {
  id: string;
  name: string;
  received: string;
}

const COLUMNS: Column<Row>[] = [
  { key: "name", header: "Name", cell: (row) => row.name },
  { key: "received", header: "Received", cell: (row) => row.received },
];

const ROWS: Row[] = [
  { id: "1", name: "Riley Sample", received: "Oct 15, 2026" },
  { id: "2", name: "Jordan Sample", received: "Oct 14, 2026" },
];

describe("DataTable", () => {
  it("heads each row with its first column", async () => {
    const { container } = render(
      <DataTable
        columns={COLUMNS}
        rows={ROWS}
        rowKey={(row) => row.id}
        caption="Needs work"
      />,
    );

    const table = screen.getByRole("table", { name: "Needs work" });
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((cell) => cell.textContent),
    ).toEqual(["Name", "Received"]);
    expect(
      within(table)
        .getAllByRole("rowheader")
        .map((cell) => cell.textContent),
    ).toEqual(["Riley Sample", "Jordan Sample"]);
    expect(
      within(table).getByRole("cell", { name: "Oct 14, 2026" }),
    ).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });
});
