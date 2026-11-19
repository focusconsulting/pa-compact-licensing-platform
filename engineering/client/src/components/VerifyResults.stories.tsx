import type { Meta, StoryObj } from "@storybook/nextjs";

import VerifyResults from "./VerifyResults";

const KANSAS = { code: "KS", name: "Kansas" };
const OKLAHOMA = { code: "OK", name: "Oklahoma" };

const JORDAN = {
  id: "5f0c2d6e-8a41-4b7c-9d13-6e2f4a8b1c90",
  first_name: "Jordan",
  last_name: "Sample",
  name_suffix: null,
  state_of_qualifying_license: KANSAS,
  privilege_states: [OKLAHOMA],
};

const meta: Meta<typeof VerifyResults> = {
  title: "Components/VerifyResults",
  component: VerifyResults,
  args: {
    search: { first_name: "Jordan", last_name: "Sample" },
    onPage: () => {},
  },
};

export default meta;
type Story = StoryObj<typeof VerifyResults>;

/** V2: two PAs share a name; the suffix and the states tell them apart. */
export const Results: Story = {
  args: {
    holders: [
      JORDAN,
      {
        ...JORDAN,
        id: "0d1f5c2a-7b3e-4a6d-8c9f-1e2a3b4c5d6e",
        name_suffix: "Jr.",
        state_of_qualifying_license: { code: "MO", name: "Missouri" },
        privilege_states: [OKLAHOMA, KANSAS],
      },
    ],
    page: { number: 1, size: 25, total: 2 },
  },
};

/** V2e: a misspelling and a PA with no privilege look the same, so the message covers both. */
export const NoMatch: Story = {
  args: {
    search: { first_name: "Jordan", last_name: "Sampel" },
    holders: [],
    page: { number: 1, size: 25, total: 0 },
  },
};

/** More results than fit one page. */
export const Paged: Story = {
  args: { holders: [JORDAN], page: { number: 2, size: 25, total: 60 } },
};
