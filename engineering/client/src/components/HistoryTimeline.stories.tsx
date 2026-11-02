import type { Meta, StoryObj } from "@storybook/nextjs";

import HistoryTimeline from "./HistoryTimeline";

const meta: Meta<typeof HistoryTimeline> = {
  title: "Components/HistoryTimeline",
  component: HistoryTimeline,
};

export default meta;
type Story = StoryObj<typeof HistoryTimeline>;

/** C6b. Given in any order; shown newest first. */
export const Application: Story = {
  args: {
    events: [
      {
        id: "1",
        on: "2026-10-14",
        what: "Application submitted",
        by: "Jordan Sample",
      },
      {
        id: "2",
        on: "2026-10-20",
        what: "Each requirement and the license checked",
        by: "Taylor Sample",
      },
      {
        id: "3",
        on: "2026-10-20",
        what: "Background check review recorded",
        by: "Taylor Sample",
      },
      {
        id: "4",
        on: "2026-10-20",
        what: "Decision recorded: Eligible",
        by: "Taylor Sample",
      },
      {
        id: "5",
        on: "2026-10-20",
        what: "Email sent to Jordan Sample",
        by: "PA Compact",
      },
    ],
  },
};
