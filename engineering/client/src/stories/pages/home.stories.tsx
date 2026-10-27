import type { Meta, StoryObj } from "@storybook/nextjs";

import Home from "../../app/page";

const meta: Meta<typeof Home> = {
  title: "App/Page",
  component: Home,
  parameters: {
    // More on how to position stories at: https://storybook.js.org/docs/react/configure/story-layout
    layout: "fullscreen",
  },
};

export default meta;
type Story = StoryObj<typeof Home>;

/** The signed-in user from the API's example, served by the Prism mock. */
export const Default: Story = {};
