import type { Meta, StoryObj } from "@storybook/nextjs";

import Verify from "../../app/verify/page";

const meta: Meta<typeof Verify> = {
  title: "App/Verify",
  component: Verify,
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof Verify>;

/** V1: the search alone. */
export const Search: Story = {};

/** V2: the API's example result, served by the Prism mock. */
export const Results: Story = {
  parameters: {
    nextjs: {
      navigation: { query: { first_name: "Pat", last_name: "Morgan" } },
    },
  },
};
