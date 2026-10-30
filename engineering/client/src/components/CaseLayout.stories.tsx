import type { Meta, StoryObj } from "@storybook/nextjs";
import {
  SummaryBox,
  SummaryBoxContent,
  SummaryBoxHeading,
} from "@trussworks/react-uswds";

import CaseLayout, { CaseSection } from "./CaseLayout";
import DataTable from "./DataTable";
import HistoryTimeline from "./HistoryTimeline";

const meta: Meta<typeof CaseLayout> = {
  title: "Components/CaseLayout",
  component: CaseLayout,
  parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj<typeof CaseLayout>;

const LICENSE = [
  { item: "License number", applied: "PA-000123", record: "PA-000123" },
  { item: "Date of birth", applied: "Mar 14, 1988", record: "Mar 14, 1988" },
];

/** C4: an application under review. */
export const ApplicationReview: Story = {
  args: {
    breadcrumbs: [
      { label: "Home", href: "/" },
      { label: "Applications to review", href: "/applications" },
    ],
    title: "Jordan Sample",
    subtitle: "Received Oct 14, 2026",
    children: (
      <>
        <CaseSection heading="License details">
          <DataTable
            caption="License details"
            rowKey={(row) => row.item}
            rows={LICENSE}
            columns={[
              { key: "item", header: "Item", cell: (row) => row.item },
              {
                key: "applied",
                header: "Jordan Sample",
                cell: (row) => row.applied,
              },
              {
                key: "record",
                header: "Sample State's record",
                cell: (row) => row.record,
              },
            ]}
          />
        </CaseSection>
        <CaseSection heading="Your review">
          <p>{"{review form}"}</p>
        </CaseSection>
      </>
    ),
  },
};

/** C6b: a PA's record, with its summary box and history. */
export const PractitionerRecord: Story = {
  args: {
    breadcrumbs: [
      { label: "Home", href: "/" },
      { label: "PA records", href: "/practitioners" },
    ],
    title: "Jordan Sample",
    banner: (
      <SummaryBox>
        <SummaryBoxHeading headingLevel="h2">
          Eligible to join the PA Compact
        </SummaryBoxHeading>
        <SummaryBoxContent>
          Sample State is Jordan Sample&apos;s state of qualifying license.
        </SummaryBoxContent>
      </SummaryBox>
    ),
    children: (
      <CaseSection heading="History">
        <HistoryTimeline
          events={[
            {
              id: "1",
              on: "2026-10-14",
              what: "Application submitted",
              by: "Jordan Sample",
            },
            {
              id: "2",
              on: "2026-10-20",
              what: "Decision recorded: Eligible",
              by: "Taylor Sample",
            },
          ]}
        />
      </CaseSection>
    ),
  },
};
