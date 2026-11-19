import type { Meta, StoryObj } from "@storybook/nextjs";

import VerifySearchForm from "./VerifySearchForm";

const meta: Meta<typeof VerifySearchForm> = {
  title: "Components/VerifySearchForm",
  component: VerifySearchForm,
  args: { onSearch: () => {} },
};

export default meta;
type Story = StoryObj<typeof VerifySearchForm>;

/** V1: both names are required. */
export const ByName: Story = {};

/** V1n: one field, with the number's format as its hint. */
export const ByNumber: Story = {
  args: { search: { privilege_number: "PA-OK-000123" } },
};

/** V2: above its results, the form shows the search that found them. */
export const Filled: Story = {
  args: { search: { first_name: "Jordan", last_name: "Sample" } },
};
