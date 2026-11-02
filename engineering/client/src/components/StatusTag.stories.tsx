import type { Meta, StoryObj } from "@storybook/nextjs";

import { STATUS_TONES, type StatusKind, type StatusView } from "src/lib/status";
import StatusTag from "./StatusTag";

// Loosely typed, to render every status from a list.
const AnyStatusTag = StatusTag as (props: {
  kind: StatusKind;
  status: string;
  view?: StatusView;
}) => JSX.Element;

const meta: Meta<typeof StatusTag> = {
  title: "Components/StatusTag",
  component: StatusTag,
};

export default meta;
type Story = StoryObj<typeof StatusTag>;

function Every({ kind }: { kind: StatusKind }) {
  return (
    <table className="usa-table usa-table--borderless">
      <thead>
        <tr>
          <th scope="col">Status</th>
          {(["staff", "public"] as StatusView[]).map((view) => (
            <th key={view} scope="col">
              {view}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Object.keys(STATUS_TONES[kind]).map((status) => (
          <tr key={status}>
            <th scope="row" className="font-mono-2xs">
              {status}
            </th>
            {(["staff", "public"] as StatusView[]).map((view) => (
              <td key={view}>
                <AnyStatusTag kind={kind} status={status} view={view} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export const Application: Story = {
  render: () => <Every kind="application" />,
};
export const PrivilegeRequest: Story = {
  render: () => <Every kind="privilegeRequest" />,
};
/** The public sees only the Active/Inactive pill. */
export const Privilege: Story = { render: () => <Every kind="privilege" /> };
/** The public sees only the Active/Inactive pill. */
export const License: Story = { render: () => <Every kind="license" /> };
