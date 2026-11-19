import type { Meta, StoryObj } from "@storybook/nextjs";

import Practitioner from "../../app/verify/practitioner/page";

const meta: Meta<typeof Practitioner> = {
  title: "App/Verify/Practitioner",
  component: Practitioner,
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof Practitioner>;

/** V3: the API's example PA, served by the Prism mock, reached from a search. */
export const FromResults: Story = {
  parameters: {
    nextjs: {
      navigation: {
        query: {
          id: "5f0c2d6e-8a41-4b7c-9d13-6e2f4a8b1c90",
          first_name: "Pat",
          last_name: "Morgan",
        },
      },
    },
  },
};

/** An address that names no PA. */
export const Missing: Story = {};
