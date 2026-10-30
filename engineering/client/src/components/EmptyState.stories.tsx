import type { Meta, StoryObj } from "@storybook/nextjs";
import { Button } from "@trussworks/react-uswds";

import EmptyState from "./EmptyState";

const meta: Meta<typeof EmptyState> = {
  title: "Components/EmptyState",
  component: EmptyState,
};

export default meta;
type Story = StoryObj<typeof EmptyState>;

/** C6: a queue section with nothing in it. */
export const MessageOnly: Story = {
  args: { children: "No applications are ready to approve." },
};

/** C8: the next step sits under the message. */
export const WithAction: Story = {
  args: {
    children: "You don't have any privileges yet.",
    action: <Button type="button">Apply for privileges</Button>,
  },
};
