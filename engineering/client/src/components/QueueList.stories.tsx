import type { Meta, StoryObj } from "@storybook/nextjs";
import { Link } from "@trussworks/react-uswds";

import type { Column } from "./DataTable";
import QueueList from "./QueueList";

interface Application {
  id: string;
  name: string;
  received: string;
  receivedOn: string;
  needs: string;
}

const COLUMNS: Column<Application>[] = [
  {
    key: "name",
    header: "Name",
    cell: (row) => <Link href={`#${row.id}`}>{row.name}</Link>,
  },
  { key: "received", header: "Received", cell: (row) => row.received },
  { key: "needs", header: "What needs work", cell: (row) => row.needs },
];

const RILEY: Application = {
  id: "riley",
  name: "Riley Sample",
  received: "Oct 15, 2026",
  receivedOn: "2026-10-15",
  needs: "Date of birth doesn't match",
};

const meta: Meta<typeof QueueList<Application>> = {
  title: "Components/QueueList",
  component: QueueList,
  args: {
    columns: COLUMNS,
    rowKey: (row) => row.id,
  },
};

export default meta;
type Story = StoryObj<typeof QueueList<Application>>;

/** C3: a group with records. */
export const WithRecords: Story = {
  args: {
    heading: "Needs work",
    rows: [RILEY],
    empty: "No applications need work.",
  },
};

/** C6: a group with nothing in it. */
export const Empty: Story = {
  args: {
    heading: "Ready to approve",
    rows: [],
    empty: "No applications are ready to approve.",
  },
};

/** The ticket's age column and CompactConnect's filter chip. Neither is drawn in Figma yet. */
export const WithAgeAndFilters: Story = {
  args: {
    heading: "Needs work",
    rows: [RILEY],
    receivedOn: (row) => row.receivedOn,
    empty: "No applications need work.",
    filters: ["{filter}"],
    onClearFilters: () => {},
  },
};
