import type { Meta, StoryObj } from "@storybook/nextjs";

import {
  CurrentUserContext,
  type CurrentUser,
} from "src/contexts/CurrentUserContext";
import AppShell from "./AppShell";

const meta: Meta<typeof AppShell> = {
  title: "Components/AppShell",
  component: AppShell,
  parameters: { layout: "fullscreen" },
  args: {
    children: (
      <div className="usa-section">
        <div className="grid-container">
          <h1>Page</h1>
        </div>
      </div>
    ),
  },
};

export default meta;
type Story = StoryObj<typeof AppShell>;

const sample: CurrentUser = {
  user_id: "8f14e45f-ceea-467f-a0e6-2b5c3d1a9e2b",
  email: "taylor@sample-state.example",
  given_name: "Taylor",
  family_name: "Sample",
  role: "state_staff",
  state_code: "KS",
  is_active: true,
  permissions: ["read_general", "write"],
};

function signedInAs(user: CurrentUser | null): Story["decorators"] {
  return [
    (Story) => (
      <CurrentUserContext.Provider value={{ user, error: null }}>
        <Story />
      </CurrentUserContext.Provider>
    ),
  ];
}

export const SignedOut: Story = { decorators: signedInAs(null) };

export const PA: Story = {
  decorators: signedInAs({
    ...sample,
    given_name: "Jordan",
    role: "licensee",
    state_code: null,
    permissions: ["manage_own_record"],
  }),
};

export const StateStaff: Story = {
  decorators: signedInAs(sample),
  parameters: { nextjs: { navigation: { pathname: "/applications" } } },
};

/** Not drawn in Figma yet: the items are placeholders. */
export const Commission: Story = {
  decorators: signedInAs({
    ...sample,
    given_name: "Casey",
    role: "compact_admin",
    state_code: null,
    permissions: ["read_general", "read_private", "compact_admin"],
  }),
};
