// SAMPLE ONLY, not for merge. Story for FLOW-02/SCR-02 drafted from Figma.
import type { Meta, StoryObj } from "@storybook/react";

import SqlCaseView, { sampleRecord, waitingRecord } from "../../components/samples/SqlCaseView";

const meta: Meta<typeof SqlCaseView> = {
  title: "Samples/FLOW-02 SCR-02 Case view",
  component: SqlCaseView,
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof SqlCaseView>;

export const ReadyToReview: Story = { args: { record: sampleRecord } };
export const WaitingForThePA: Story = { args: { record: waitingRecord } };
