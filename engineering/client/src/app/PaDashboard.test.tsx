import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { CognitoUserSession } from "amazon-cognito-identity-js";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import { getCurrentSession } from "src/lib/auth";
import type { Dashboard } from "src/lib/application";
import { APPLICATION_ID, STATES, failure, ok } from "src/tests/application";
import { expectNoAxeViolations } from "src/tests/axe";
import { routeFetch } from "src/tests/fetch";
import PaDashboard from "./PaDashboard";

vi.mock("src/lib/auth");
const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace }),
}));

type Summary = Dashboard["applications"][number];

// The withdraw modal's focus trap counts an element as visible only if it has layout, which jsdom never gives.
beforeAll(() => {
  vi.spyOn(Element.prototype, "getClientRects").mockReturnValue([
    {},
  ] as unknown as DOMRectList);
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => "valid-token" }),
  } as CognitoUserSession);
});

function summary(overrides: Partial<Summary> = {}): Summary {
  return {
    id: APPLICATION_ID,
    kind: "initial",
    status: "submitted",
    sql_state_code: "KS",
    claimed_license_number: "PA-000123",
    opened_at: "2026-10-14T15:00:00Z",
    decided_at: null,
    withdrawn_at: null,
    denial_reason: null,
    denial_reason_detail: null,
    resubmit_by: null,
    timeline: [],
    ...overrides,
  };
}

function dashboard(overrides: Partial<Dashboard> = {}): Dashboard {
  return {
    qualifying_license: null,
    applications: [summary()],
    privileges: [],
    primary_action: {
      kind: "apply_for_privileges",
      available: false,
      reasons: ["not_yet_eligible", "application_in_review"],
    },
    ...overrides,
  };
}

const ELIGIBLE = dashboard({
  qualifying_license: {
    state_code: "KS",
    license_number: "PA-000123",
    expires_on: "2027-06-30",
    status: "active",
    verified_by_state: "KS",
    verified_at: "2026-10-20T15:00:00Z",
  },
  applications: [
    summary({ status: "eligible", decided_at: "2026-10-20T15:00:00Z" }),
  ],
  primary_action: {
    kind: "apply_for_privileges",
    available: true,
    reasons: [],
  },
});

const WITHDRAW = `POST /api/me/applications/${APPLICATION_ID}/withdraw`;

function answers(shown: Dashboard | Response | Response[], overrides = {}) {
  const answer =
    shown instanceof Response || Array.isArray(shown) ? shown : ok(shown);
  return routeFetch({
    "GET /api/me/dashboard": answer,
    "GET /api/public/states": ok(STATES),
    [WITHDRAW]: ok(summary({ status: "withdrawn" })),
    ...overrides,
  });
}

describe("the PA dashboard", () => {
  it("shows an application under review, with the way to withdraw it", async () => {
    answers(dashboard());
    const { container } = render(<PaDashboard />);

    expect(
      await screen.findByRole("heading", { level: 1, name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Kansas · License PA-000123")).toBeInTheDocument();
    expect(screen.getByText("Under review")).toBeInTheDocument();
    expect(
      screen.getByText(/Sent to Kansas on Oct 14, 2026/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Kansas checks your license. If you haven't yet, submit to a criminal background check through Kansas's process within 60 days of your application.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Withdraw application" }),
    ).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("withdraws after the PA confirms, then says so", async () => {
    const spy = answers([
      ok(dashboard()),
      ok(
        dashboard({
          applications: [
            summary({
              status: "withdrawn",
              withdrawn_at: "2026-10-16T15:00:00Z",
            }),
          ],
        }),
      ),
    ]);
    render(<PaDashboard />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Withdraw application" }),
    );

    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      "Withdraw your application to join the PA Compact?",
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleDescription(
      "Kansas will stop reviewing it. To join later, you'll need to apply again.",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Yes, withdraw application" }),
    );

    expect(
      await screen.findByText("Application withdrawn"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "You withdrew your application on Oct 16, 2026. PA Compact emailed you and Kansas.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Withdrawn on Oct 16, 2026/)).toBeInTheDocument();
    const withdrawals = spy.mock.calls.filter(
      ([r]) => (r as Request).method === "POST",
    );
    expect(withdrawals).toHaveLength(1);
  });

  it("does not withdraw when the PA cancels", async () => {
    const spy = answers(dashboard());
    render(<PaDashboard />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Withdraw application" }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(spy.mock.calls.some(([r]) => (r as Request).method === "POST")).toBe(
      false,
    );
  });

  it("says when the application could not be withdrawn", async () => {
    answers(dashboard(), { [WITHDRAW]: failure("INVALID_TRANSITION") });
    render(<PaDashboard />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Withdraw application" }),
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Yes, withdraw application" }),
    );

    expect(
      await screen.findByText(
        "We couldn't withdraw your application. Try again.",
      ),
    ).toBeInTheDocument();
  });

  it("shows a withdrawn application without the alert on a later visit", async () => {
    answers(
      dashboard({
        applications: [
          summary({
            status: "withdrawn",
            withdrawn_at: "2026-10-16T15:00:00Z",
          }),
        ],
      }),
    );
    render(<PaDashboard />);

    expect(
      await screen.findByText(
        "Kansas has stopped reviewing it. To join the PA Compact later, apply again.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText("Application withdrawn")).not.toBeInTheDocument();
  });

  it("shows a decision of not eligible, with how to appeal", async () => {
    answers(
      dashboard({
        applications: [
          summary({ status: "denied", decided_at: "2026-10-20T15:00:00Z" }),
        ],
      }),
    );
    render(<PaDashboard />);

    expect(
      await screen.findByText(/Kansas decided on Oct 20, 2026/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Kansas found you not eligible. You can appeal to Kansas under its law. To find out how and by when, contact Kansas.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "You can apply again through Kansas or another state where you hold a license.",
      ),
    ).toBeInTheDocument();
  });

  it("shows when a state withdrew eligibility", async () => {
    answers(
      dashboard({
        applications: [
          summary({
            status: "eligibility_withdrawn",
            decided_at: "2026-10-20T15:00:00Z",
          }),
        ],
      }),
    );
    render(<PaDashboard />);

    expect(
      await screen.findByText("Eligibility withdrawn"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Kansas decided on Oct 20, 2026/),
    ).toBeInTheDocument();
  });

  it("shows an eligible PA their license and the way to apply for privileges", async () => {
    answers(ELIGIBLE);
    const { container } = render(<PaDashboard />);

    expect(
      await screen.findByText(
        "Kansas · License PA-000123 · Active · Expires Jun 30, 2027",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Verified by Kansas, Oct 20, 2026/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/You don't have any Compact Privileges yet/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Apply for Compact Privileges" }),
    ).toHaveAttribute("href", "/privileges");
    await expectNoAxeViolations(container);
  });

  it("does not offer privileges while the action is unavailable", async () => {
    answers({
      ...ELIGIBLE,
      primary_action: {
        kind: "apply_for_privileges",
        available: false,
        reasons: ["two_year_bar"],
      },
    });
    render(<PaDashboard />);

    expect(await screen.findByText(/Verified by Kansas/)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Apply for Compact Privileges" }),
    ).not.toBeInTheDocument();
  });

  it("lists the PA's privileges", async () => {
    answers({
      ...ELIGIBLE,
      privileges: [
        {
          id: "9a4b2c1d-0e3f-4a5b-8c7d-6e5f4a3b2c1d",
          remote_state_code: "OK",
          privilege_number: "PA-OK-000001",
          status: "active",
          issued_at: "2026-10-25T15:00:00Z",
          expires_on: "2027-06-30",
          expires_in_days: 230,
          history: [],
        },
      ],
    });
    const { container } = render(<PaDashboard />);

    expect(await screen.findByText(/PA-OK-000001/)).toBeInTheDocument();
    expect(
      screen.queryByText(/You don't have any Compact Privileges yet/),
    ).not.toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("names a state by its code when the list does not have it", async () => {
    answers(dashboard({ applications: [summary({ sql_state_code: "ZZ" })] }));
    render(<PaDashboard />);

    expect(
      await screen.findByText("ZZ · License PA-000123"),
    ).toBeInTheDocument();
  });

  it.each([
    ["no application", []],
    ["a draft", [summary({ status: "draft" })]],
  ])("sends a PA with %s to the application", async (_, applications) => {
    answers(dashboard({ applications }));
    render(<PaDashboard />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/application"));
    expect(
      screen.queryByRole("heading", { name: "Dashboard" }),
    ).not.toBeInTheDocument();
  });

  it("shows what the state asked for, by when, and the ways to answer it", async () => {
    answers(
      dashboard({
        applications: [
          summary({
            status: "info_requested",
            resubmit_by: "2026-12-13",
            timeline: [
              {
                kind: "applied",
                status: "submitted",
                at: "2026-10-14T15:00:00Z",
              },
              {
                kind: "info_requested",
                status: "info_requested",
                at: "2026-10-19T15:00:00Z",
                note: "Upload your NCCPA certificate.",
              },
            ],
          }),
        ],
      }),
    );
    const { container } = render(<PaDashboard />);

    expect(
      await screen.findByText(/Kansas asked on Oct 19, 2026/),
    ).toBeInTheDocument();
    expect(screen.getByText("Information requested")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Kansas needs more information. Update your application and resubmit it by Dec 13, 2026. If Kansas doesn't have it by then, your application is withdrawn.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Kansas's note" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Upload your NCCPA certificate."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Update your application" }),
    ).toHaveAttribute("href", "/application");
    expect(
      screen.getByRole("button", { name: "Withdraw application" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Kansas asked for more information."),
    ).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
    await expectNoAxeViolations(container);
  });

  it("lists every step of every application, newest first", async () => {
    answers(
      dashboard({
        applications: [
          summary({
            id: "a2",
            timeline: [
              {
                kind: "applied_again",
                status: "submitted",
                at: "2026-10-19T15:00:00Z",
              },
            ],
          }),
          summary({
            id: "a1",
            status: "withdrawn",
            withdrawn_at: "2026-10-16T15:00:00Z",
            timeline: [
              {
                kind: "applied",
                status: "submitted",
                at: "2026-10-14T15:00:00Z",
              },
              {
                kind: "withdrawn_by_pa",
                status: "withdrawn",
                at: "2026-10-16T15:00:00Z",
              },
            ],
          }),
        ],
      }),
    );
    render(<PaDashboard />);

    expect(
      await screen.findByRole("heading", { name: "History" }),
    ).toBeInTheDocument();
    const rows = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.textContent);
    expect(rows).toEqual([
      "Oct 19, 2026You applied again.",
      "Oct 16, 2026You withdrew your application.",
      "Oct 14, 2026You applied.",
    ]);
  });

  it("says when the PA resubmitted (B-n1r)", async () => {
    answers(
      dashboard({
        applications: [
          summary({
            timeline: [
              {
                kind: "applied",
                status: "submitted",
                at: "2026-10-14T15:00:00Z",
              },
              {
                kind: "info_requested",
                status: "info_requested",
                at: "2026-10-19T15:00:00Z",
              },
              {
                kind: "resubmitted",
                status: "submitted",
                at: "2026-10-21T15:00:00Z",
              },
            ],
          }),
        ],
      }),
    );
    render(<PaDashboard />);

    expect(
      await screen.findByText(/Resubmitted on Oct 21, 2026/),
    ).toBeInTheDocument();
    expect(
      screen.getByText("You resubmitted your application."),
    ).toBeInTheDocument();
  });

  it("has no history before the state has an application", async () => {
    answers(dashboard());
    render(<PaDashboard />);

    expect(await screen.findByText("Under review")).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "History" }),
    ).not.toBeInTheDocument();
  });

  it("says when the dashboard cannot be loaded", async () => {
    answers(failure("NOT_FOUND", 404));
    render(<PaDashboard />);

    expect(
      await screen.findByText(
        "We couldn't load your application. Try again later.",
      ),
    ).toBeInTheDocument();
  });

  it.each([
    ["loads", ok(dashboard())],
    ["fails", failure("NOT_FOUND", 404)],
  ])("ignores what %s after the PA has left", async (_, answer) => {
    answers(answer);
    const { unmount, container } = render(<PaDashboard />);
    unmount();

    await new Promise((resolve) => {
      setTimeout(resolve, 0);
    });

    expect(container).toBeEmptyDOMElement();
  });
});
