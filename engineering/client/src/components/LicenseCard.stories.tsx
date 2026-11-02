import type { Meta, StoryObj } from "@storybook/nextjs";
import { CardGroup } from "@trussworks/react-uswds";

import CardActionMenu from "./CardActionMenu";
import LicenseCard from "./LicenseCard";

const meta: Meta<typeof LicenseCard> = {
  title: "Components/LicenseCard",
  component: LicenseCard,
  decorators: [
    (Story) => (
      <CardGroup>
        <Story />
      </CardGroup>
    ),
  ],
  args: {
    state: "Sample State",
    number: "PA-000123",
    status: "active",
    expires: "2027-06-30",
  },
};

export default meta;
type Story = StoryObj<typeof LicenseCard>;

/** What a PA sees: the Active/Inactive pill. */
export const Public: Story = {};

/** Staff see the computed status, discipline, the state's note, and their actions. */
export const StaffEncumbered: Story = {
  args: {
    status: "encumbered",
    view: "staff",
    discipline: "{discipline status}",
    note: "{status line from the state}",
    actions: (
      <CardActionMenu
        record="Sample State license"
        actions={[{ key: "report", label: "{action}", onSelect: () => {} }]}
      />
    ),
  },
};
