import type { Meta, StoryObj } from "@storybook/nextjs";
import { Link } from "@trussworks/react-uswds";

import AlertBanner from "./AlertBanner";

const meta: Meta<typeof AlertBanner> = {
  title: "Components/AlertBanner",
  component: AlertBanner,
};

export default meta;
type Story = StoryObj<typeof AlertBanner>;

/** C6: after recording a decision. */
export const Success: Story = {
  args: {
    type: "success",
    heading: "Decision recorded: Jordan Sample is eligible",
    children: (
      <>
        PA Compact emailed Jordan Sample.
        <br />
        <Link href="#record">View Jordan Sample&apos;s record</Link>
      </>
    ),
  },
};

/** C4b: one line, no heading. */
export const InfoSlim: Story = {
  args: {
    type: "info",
    slim: true,
    children: "Sample State has no license record for Riley Sample.",
  },
};

export const Warning: Story = {
  args: {
    type: "warning",
    heading: "{heading}",
    children: "{text}",
  },
};

/** Announced at once (`role="alert"`). */
export const Error: Story = {
  args: {
    type: "error",
    heading: "{heading}",
    children: "{text}",
  },
};
