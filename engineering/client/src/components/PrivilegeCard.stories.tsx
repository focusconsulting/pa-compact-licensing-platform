import type { Meta, StoryObj } from "@storybook/nextjs";
import { CardGroup } from "@trussworks/react-uswds";

import PrivilegeCard from "./PrivilegeCard";

const meta: Meta<typeof PrivilegeCard> = {
  title: "Components/PrivilegeCard",
  component: PrivilegeCard,
  decorators: [
    (Story) => (
      <CardGroup>
        <Story />
      </CardGroup>
    ),
  ],
  args: {
    state: "Kansas",
    number: "PA-KS-000001",
    activeFrom: "2026-11-02",
    expires: "2027-06-30",
    detailsHref: "#",
  },
};

export default meta;
type Story = StoryObj<typeof PrivilegeCard>;

export const Active: Story = { args: { status: "active" } };

/** A past expiry is red. */
export const Expired: Story = { args: { status: "expired" } };

export const Deactivated: Story = { args: { status: "inactive" } };

/** Staff see the computed status; discipline shows as its own field. */
export const StaffEncumbered: Story = {
  args: {
    status: "encumbered",
    view: "staff",
    discipline: "{discipline status}",
  },
};
