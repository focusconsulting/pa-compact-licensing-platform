import type { Meta, StoryObj } from "@storybook/nextjs";

import "src/styles/status-tag.scss";

/**
 * The names in `engineering/docs/design/tokens.md`, rendered with the values
 * `_uswds-theme.scss` sets, so a brand change can be checked by eye.
 */
const meta: Meta = {
  title: "Design/Theme",
};

export default meta;
type Story = StoryObj;

const GRADES = ["lighter", "light", "", "dark", "darker"];
const FAMILIES = [
  "primary",
  "secondary",
  "base",
  "info",
  "success",
  "warning",
  "error",
];
const TYPE_SCALE = ["3xs", "2xs", "xs", "sm", "md", "lg", "xl", "2xl", "3xl"];
const UNITS = ["05", "1", "105", "2", "205", "3", "4", "5", "6", "8", "10"];
const RADII = ["0", "sm", "md", "lg", "pill"];
const TONES = ["success", "info", "warning", "error", "neutral"];

const swatch = (family: string, grade: string) =>
  grade ? `${family}-${grade}` : family;

export const Colour: Story = {
  render: () => (
    <div className="padding-2">
      {FAMILIES.map((family) => (
        <div key={family} className="display-flex margin-bottom-1">
          {GRADES.map((grade) => (
            <div key={grade} className="width-15 font-mono-3xs">
              <div className={`bg-${swatch(family, grade)} height-6`} />
              {swatch(family, grade)}
            </div>
          ))}
        </div>
      ))}
    </div>
  ),
};

export const Type: Story = {
  render: () => (
    <div className="padding-2">
      {TYPE_SCALE.map((size) => (
        <p key={size} className={`font-sans-${size} margin-y-1`}>
          {size}: Public Sans
        </p>
      ))}
      <p className="text-normal">normal</p>
      <p className="text-semibold">semibold</p>
      <p className="text-bold">bold</p>
      <h1>Heading 1</h1>
      <h2>Heading 2</h2>
      <h3>Heading 3</h3>
    </div>
  ),
};

export const Spacing: Story = {
  render: () => (
    <div className="padding-2">
      {UNITS.map((unit) => (
        <div key={unit} className="display-flex flex-align-center margin-y-1">
          <span className="font-mono-3xs width-5">{unit}</span>
          <div className={`bg-primary height-2 width-${unit}`} />
        </div>
      ))}
    </div>
  ),
};

export const Radius: Story = {
  render: () => (
    <div className="padding-2 display-flex">
      {RADII.map((radius) => (
        <div
          key={radius}
          className={`bg-base-lighter radius-${radius} width-10 height-6 margin-right-2 padding-1 font-mono-3xs`}
        >
          {radius}
        </div>
      ))}
    </div>
  ),
};

export const StatusTagTones: Story = {
  render: () => (
    <div className="padding-2 display-flex">
      {TONES.map((tone) => (
        <span
          key={tone}
          className={`status-tag--${tone} padding-x-1 padding-y-05 margin-right-1 radius-sm font-sans-2xs`}
        >
          {tone}
        </span>
      ))}
    </div>
  ),
};
