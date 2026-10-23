import type { Meta, StoryObj } from "@storybook/react";
import { http, HttpResponse } from "msw";

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

/** The signed-in user from the API's example, through the generated mocks. */
export const Default: Story = {};

/** The API refuses the signed-in user. */
export const Forbidden: Story = {
  parameters: {
    msw: {
      handlers: {
        api: [
          http.get("*/api/me", () =>
            HttpResponse.json(
              { code: "FORBIDDEN", details: ["User not found"] },
              { status: 403 },
            ),
          ),
        ],
      },
    },
  },
};
