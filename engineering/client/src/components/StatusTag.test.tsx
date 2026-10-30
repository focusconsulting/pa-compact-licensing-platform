import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import labels from "src/i18n/en/status.json";
import {
  PILL,
  PILL_TONES,
  STATUS_TONES,
  type StatusKind,
  type StatusView,
} from "src/lib/status";
import { expectNoAxeViolations } from "src/tests/axe";
import StatusTag from "./StatusTag";

// Loosely typed, to render every status from a list.
const AnyStatusTag = StatusTag as (props: {
  kind: StatusKind;
  status: string;
  view?: StatusView;
}) => JSX.Element;

// Every status of every kind, from the contract the API's enums are checked against.
const EVERY = (Object.keys(STATUS_TONES) as StatusKind[]).flatMap((kind) =>
  Object.entries(STATUS_TONES[kind]).map(([status, tone]) => ({
    kind,
    status,
    tone,
  })),
);

function renderTag(kind: StatusKind, status: string, view?: StatusView) {
  render(<AnyStatusTag kind={kind} status={status} view={view} />);
}

describe("StatusTag", () => {
  it.each(EVERY)(
    "shows staff the $kind status $status in its tone",
    ({ kind, status, tone }) => {
      renderTag(kind, status, "staff");

      const tag = screen.getByText(
        (labels[kind] as Record<string, string>)[status],
      );
      expect(tag).toHaveClass("usa-tag", `status-tag--${tone}`);
    },
  );

  it.each(
    EVERY.filter(({ kind }) => kind === "privilege" || kind === "license"),
  )(
    "shows the public the pill for the $kind status $status",
    ({ kind, status }) => {
      renderTag(kind, status, "public");

      const pill = (
        PILL[kind as keyof typeof PILL] as Record<string, "active" | "inactive">
      )[status];
      expect(screen.getByText(labels.pill[pill])).toHaveClass(
        `status-tag--${PILL_TONES[pill]}`,
      );
    },
  );

  it.each(
    EVERY.filter(
      ({ kind }) => kind === "application" || kind === "privilegeRequest",
    ),
  )(
    "shows the public the $kind status $status itself",
    ({ kind, status, tone }) => {
      renderTag(kind, status, "public");

      expect(
        screen.getByText((labels[kind] as Record<string, string>)[status]),
      ).toHaveClass(`status-tag--${tone}`);
    },
  );

  it("shows the pill when no view is given", () => {
    render(<StatusTag kind="license" status="encumbered" />);

    expect(screen.getByText("Inactive")).toBeInTheDocument();
    expect(screen.queryByText("Encumbered")).toBeNull();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <StatusTag kind="application" status="eligible" />,
    );

    await expectNoAxeViolations(container);
  });
});
