import type { Meta, StoryObj } from "@storybook/nextjs";

import DataTable, { type Column } from "./DataTable";

interface Detail {
  item: string;
  applied: string;
  record: string;
}

const COLUMNS: Column<Detail>[] = [
  { key: "item", header: "Item", cell: (row) => row.item },
  { key: "applied", header: "Jordan Sample", cell: (row) => row.applied },
  { key: "record", header: "Sample State's record", cell: (row) => row.record },
];

const meta: Meta<typeof DataTable<Detail>> = {
  title: "Components/DataTable",
  component: DataTable,
};

export default meta;
type Story = StoryObj<typeof DataTable<Detail>>;

/** C4's license details. */
export const LicenseDetails: Story = {
  args: {
    caption: "License details",
    columns: COLUMNS,
    rowKey: (row) => row.item,
    rows: [
      { item: "License number", applied: "PA-000123", record: "PA-000123" },
      {
        item: "Date of birth",
        applied: "Mar 14, 1988",
        record: "Mar 14, 1988",
      },
      {
        item: "Last 4 of Social Security number",
        applied: "1234",
        record: "1234",
      },
    ],
  },
};
