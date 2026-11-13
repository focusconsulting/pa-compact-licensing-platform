import { render, screen, waitFor } from "@testing-library/react";
import type { CognitoUserSession } from "amazon-cognito-identity-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuth } from "src/contexts/AuthContext";
import { getCurrentSession } from "src/lib/auth";
import { STATES, application, failure, ok } from "src/tests/application";
import { expectNoAxeViolations } from "src/tests/axe";
import { routeFetch } from "src/tests/fetch";
import Page from "./page";

vi.mock("src/lib/auth");
vi.mock("src/contexts/AuthContext");
const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace }),
}));

const SUBMITTED = application({
  status: "submitted",
  opened_at: "2026-10-14T15:00:00Z",
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({
    isLoading: false,
    idToken: "valid-token",
    email: "pa@example.com",
    signOut: vi.fn(),
    signIn: vi.fn(),
    completeNewPassword: vi.fn(),
  });
  vi.mocked(getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => "valid-token" }),
  } as CognitoUserSession);
});

function answers(overrides: Record<string, Response> = {}) {
  return routeFetch({
    "GET /api/me/applications": ok([SUBMITTED]),
    "GET /api/public/states": ok(STATES),
    ...overrides,
  });
}

describe("the application received page", () => {
  it("says when the PA applied and what the state does next", async () => {
    answers();
    const { container } = render(<Page />);

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Application received",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "You applied on Oct 14, 2026. Kansas will review it next.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("listitem").map((item) => item.textContent),
    ).toEqual([
      "Kansas checks your license against its records.",
      "To join the PA Compact, submit to a criminal background check, including fingerprints, through Kansas's process within 60 days of applying.",
      "If Kansas needs more information, PA Compact will email you.",
      "If Kansas confirms you're eligible, PA Compact will email you. Then you can apply for Compact Privileges to practice in other states, and pay their fees.",
    ]);
    await expectNoAxeViolations(container);
  });

  it("says when the PA resubmitted, and that the state reviews it again", async () => {
    answers({
      "GET /api/me/applications": ok([
        {
          ...SUBMITTED,
          request_note: "Upload your NCCPA certificate.",
          sworn_at: "2026-10-21T15:00:00Z",
        },
      ]),
    });
    render(<Page />);

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Application resubmitted",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "You resubmitted it on Oct 21, 2026. Kansas will review it again.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("listitem").map((item) => item.textContent),
    ).toEqual([
      "Kansas reviews your application again.",
      "If you haven't yet, submit to a criminal background check through Kansas's process within 60 days of your application.",
      "If Kansas needs more information, PA Compact will email you.",
      "If Kansas confirms you're eligible, PA Compact will email you. Then you can apply for Compact Privileges to practice in other states, and pay their fees.",
    ]);
  });

  it("names the state by its code when the list does not have it", async () => {
    answers({ "GET /api/public/states": ok([]) });
    render(<Page />);

    expect(
      await screen.findByText(
        "You applied on Oct 14, 2026. KS will review it next.",
      ),
    ).toBeInTheDocument();
  });

  it("sends a PA with nothing submitted to the first step", async () => {
    answers({ "GET /api/me/applications": ok([application()]) });
    render(<Page />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/application"));
  });

  it("says when the application cannot be loaded", async () => {
    answers({ "GET /api/me/applications": failure("NOT_FOUND", 404) });
    render(<Page />);

    expect(
      await screen.findByText(
        "We couldn't load your application. Try again later.",
      ),
    ).toBeInTheDocument();
  });

  it.each([
    ["loads", {}],
    ["fails", { "GET /api/me/applications": failure("NOT_FOUND", 404) }],
  ])("ignores what %s after the PA has left", async (_, overrides) => {
    answers(overrides);
    const { unmount, container } = render(<Page />);
    unmount();

    await new Promise((resolve) => {
      setTimeout(resolve, 0);
    });

    expect(container).toBeEmptyDOMElement();
  });
});
