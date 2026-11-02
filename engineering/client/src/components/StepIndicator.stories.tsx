import type { Meta, StoryObj } from "@storybook/nextjs";

import StepIndicator from "./StepIndicator";

const meta: Meta<typeof StepIndicator> = {
  title: "Components/StepIndicator",
  component: StepIndicator,
  args: { steps: ["Your license and details", "Statements and submit"] },
};

export default meta;
type Story = StoryObj<typeof StepIndicator>;

/** B2. */
export const FirstStep: Story = { args: { current: 0 } };

/** B6. */
export const LastStep: Story = { args: { current: 1 } };
