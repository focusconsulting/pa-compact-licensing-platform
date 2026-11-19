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
    verifyTotpSetup: vi.fn(),
    answerTotp: vi.fn(),
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
      "To join the PA Compact, submit to a criminal background check, including fingerprints, through Kansas' process within 60 days of applying.",
      "If Kansas needs more information, Kansas will contact you.",
      "If Kansas confirms you're eligible, PA Compact will email you. Then you can apply for Compact Privileges to practice in other states, and pay their fees.",
    ]);
    await expectNoAxeViolations(container);
  });

  it("gives a state whose name doesn't end in s the full possessive", async () => {
    answers({
      "GET /api/me/applications": ok([{ ...SUBMITTED, sql_state_code: "OK" }]),
    });
    render(<Page />);

    expect(
      await screen.findByText(/through Oklahoma's process within 60 days/),
    ).toBeInTheDocument();
  });

  it("says the application cannot be loaded when its state is not listed", async () => {
    answers({ "GET /api/public/states": ok([]) });
    render(<Page />);

    expect(
      await screen.findByText(
        "We couldn't load your application. Try again later.",
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
