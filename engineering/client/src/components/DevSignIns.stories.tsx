import type { Meta, StoryObj } from "@storybook/nextjs";

import DevSignIns from "./DevSignIns";

/** Stands in for the local Cognito mock, which Storybook does not run. */
function answerListUsers(answer: () => Response) {
  const original = globalThis.fetch;
  globalThis.fetch = () => Promise.resolve(answer());
  return () => {
    globalThis.fetch = original;
  };
}

const meta: Meta<typeof DevSignIns> = {
  title: "Components/DevSignIns",
  component: DevSignIns,
  args: { onPick: () => {} },
};

export default meta;
type Story = StoryObj<typeof DevSignIns>;

/** Local builds only (ADR-0020): each address signs in as that user. */
export const Listed: Story = {
  beforeEach: () =>
    answerListUsers(() =>
      Response.json({
        Users: [
          { Username: "kansas.staff@demo.example" },
          { Username: "avery.active@demo.example" },
          { Username: "pia.expired@demo.example" },
        ],
      }),
    ),
};

/** The mock is not running. */
export const MockNotAnswering: Story = {
  beforeEach: () => answerListUsers(() => Response.json({}, { status: 500 })),
};
