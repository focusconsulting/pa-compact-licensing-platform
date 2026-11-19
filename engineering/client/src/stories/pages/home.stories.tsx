import type { Meta, StoryObj } from "@storybook/nextjs";

import Home from "../../app/page";
import { CurrentUserContext } from "../../contexts/CurrentUserContext";

const meta: Meta<typeof Home> = {
  title: "App/Front door",
  component: Home,
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof Home>;

/** V0s: every story is signed in, as the API's example user, so their own card leads to their dashboard. */
export const SignedIn: Story = {};

/** V0: what a visitor sees, and what everyone sees until the session check finishes. */
export const SignedOut: Story = {
  decorators: [
    (Story) => (
      <CurrentUserContext.Provider value={{ user: null, error: null }}>
        <Story />
      </CurrentUserContext.Provider>
    ),
  ],
};
