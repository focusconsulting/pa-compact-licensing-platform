import type { Meta, StoryObj } from "@storybook/nextjs";

import CardActionMenu from "./CardActionMenu";

const meta: Meta<typeof CardActionMenu> = {
  title: "Components/CardActionMenu",
  component: CardActionMenu,
  parameters: { layout: "padded" },
  args: {
    record: "Kansas privilege",
    actions: [
      { key: "deactivate", label: "Deactivate", onSelect: () => {} },
      { key: "report", label: "Report discipline", onSelect: () => {} },
    ],
  },
  decorators: [
    (Story) => (
      <div className="display-flex flex-justify-end height-card">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof CardActionMenu>;

export const Closed: Story = {};

export const Open: Story = {
  play: async ({ canvas, userEvent }) => {
    await userEvent.click(canvas.getByRole("button", { name: /Actions/ }));
  },
};
