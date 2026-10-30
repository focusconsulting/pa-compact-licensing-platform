import type { Meta, StoryObj } from "@storybook/nextjs";

import PageHeading from "./PageHeading";

const meta: Meta<typeof PageHeading> = {
  title: "Components/PageHeading",
  component: PageHeading,
};

export default meta;
type Story = StoryObj<typeof PageHeading>;

export const TitleOnly: Story = { args: { title: "Applications to review" } };

/** B2: the intro line is in the wireframe. */
export const WithIntro: Story = {
  args: {
    title: "Apply to join the PA Compact",
    intro:
      "Your state of qualifying license reviews your application. You'll get an email when it decides.",
  },
};
