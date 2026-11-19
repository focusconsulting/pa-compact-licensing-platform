import type { Meta, StoryObj } from "@storybook/nextjs";

import Dashboard from "../../app/dashboard/page";

const meta: Meta<typeof Dashboard> = {
  title: "App/Dashboard",
  component: Dashboard,
  parameters: {
    // More on how to position stories at: https://storybook.js.org/docs/react/configure/story-layout
    layout: "fullscreen",
  },
};

export default meta;
type Story = StoryObj<typeof Dashboard>;

/** The signed-in user from the API's example, served by the Prism mock. */
export const Default: Story = {};
