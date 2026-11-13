import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { CognitoUserSession } from "amazon-cognito-identity-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuth } from "src/contexts/AuthContext";
import { getCurrentSession } from "src/lib/auth";
import {
  APPLICATION_ID,
  ATTESTATIONS,
  STATES,
  application,
  failure,
  ok,
} from "src/tests/application";
import { expectNoAxeViolations } from "src/tests/axe";
import { routeFetch } from "src/tests/fetch";
import Page from "./page";

vi.mock("src/lib/auth");
vi.mock("src/contexts/AuthContext");
const push = vi.fn();
const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace }) }));

const ACCEPT = `POST /api/me/applications/${APPLICATION_ID}/attestations`;
const SUBMIT = `POST /api/me/applications/${APPLICATION_ID}/submit`;

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

function answers(overrides: Record<string, Response | Response[]> = {}) {
  return routeFetch({
    "GET /api/me/applications": ok([application()]),
    "GET /api/public/attestations": ok(ATTESTATIONS),
    "GET /api/public/states": ok(STATES),
    [ACCEPT]: ok(application(), 201),
    [SUBMIT]: ok(application({ status: "submitted" })),
    ...overrides,
  });
}

async function bodies(spy: ReturnType<typeof routeFetch>, route: string) {
  const sent = spy.mock.calls
    .map(([input]) => input as Request)
    .filter((r) => `${r.method} ${new URL(r.url).pathname}` === route);
  return Promise.all(sent.map((r) => r.clone().json()));
}

async function check(name: string) {
  const box = await screen.findByRole("checkbox", { name });
  if (!(box as HTMLInputElement).checked) await userEvent.click(box);
}

async function agreeToEverything() {
  await check("I hold a current NCCPA certification.");
  await check("I understand");
  await check(
    "I swear that the information in this application is true and accurate.",
  );
  await userEvent.type(
    screen.getByRole("textbox", { name: "Type your full legal name *" }),
    "Jordan Alex Sample",
  );
}

describe("the application's statements and submit step", () => {
  it("accepts each statement, then submits with the sworn name", async () => {
    const spy = answers();
    const { container } = render(<Page />);

    expect(
      await screen.findByText(
        "To join the PA Compact, submit to a criminal background check, including fingerprints, through Kansas's process within 60 days of applying.",
      ),
    ).toBeInTheDocument();
    await agreeToEverything();
    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/application/received"),
    );
    const accepted = await bodies(spy, ACCEPT);
    expect(accepted).toEqual(
      expect.arrayContaining([
        { code: "nccpa_current", version: 1 },
        { code: "background_check", version: 1 },
        { code: "truthfulness", version: 2 },
      ]),
    );
    expect(await bodies(spy, SUBMIT)).toEqual([
      { sworn: true, sworn_name: "Jordan Alex Sample", document_ids: [] },
    ]);
    await expectNoAxeViolations(container);
  });

  it("asks for every statement again to resubmit, and sends the PA's upload", async () => {
    const spy = answers({
      "GET /api/me/applications": ok([
        application({
          status: "info_requested",
          requested_at: "2026-10-19T15:00:00Z",
          attestations: ATTESTATIONS.map((a) => ({
            code: a.code,
            version: a.version,
            accepted_at: "2026-10-14T15:00:00Z",
          })),
        }),
      ]),
      "GET /api/me/documents/unattached": ok([{ id: "d1" }]),
    });
    const { container } = render(<Page />);

    expect(
      await screen.findByText(
        "You're resubmitting, so agree to the statements and sign again.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("checkbox", { name: "I understand" }),
    ).not.toBeChecked();
    await expectNoAxeViolations(container);
    await agreeToEverything();
    await userEvent.click(
      screen.getByRole("button", { name: "Resubmit application" }),
    );

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/application/received"),
    );
    expect(await bodies(spy, ACCEPT)).toHaveLength(ATTESTATIONS.length);
    expect(await bodies(spy, SUBMIT)).toEqual([
      { sworn: true, sworn_name: "Jordan Alex Sample", document_ids: ["d1"] },
    ]);
  });

  it("says which answers need fixing, and accepts nothing (B6e)", async () => {
    const spy = answers();
    const { container } = render(<Page />);

    await check("I understand");
    await check(
      "I swear that the information in this application is true and accurate.",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    expect(
      await screen.findByRole("heading", { name: "2 answers need fixing" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Agree to the statements *" }),
    ).toHaveAccessibleDescription("Tick the statements to agree to them");
    expect(screen.getByText("Type your full name to sign")).toBeInTheDocument();
    expect(await bodies(spy, ACCEPT)).toEqual([]);
    expect(await bodies(spy, SUBMIT)).toEqual([]);
    await expectNoAxeViolations(container);
  });

  it("asks for the background check and the sworn statement on their own", async () => {
    answers();
    render(<Page />);

    await check("I hold a current NCCPA certification.");
    await userEvent.type(
      screen.getByRole("textbox", { name: "Type your full legal name *" }),
      "Jordan Alex Sample",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    expect(
      await screen.findByRole("heading", { name: "2 answers need fixing" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Tick the box to confirm you understand"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Tick the statement to agree to it"),
    ).toBeInTheDocument();
  });

  it("checks what the PA already accepted, and accepts only what is new", async () => {
    const spy = answers({
      "GET /api/me/applications": ok([
        application({
          attestations: [
            {
              code: "nccpa_current",
              version: 1,
              accepted_at: "2026-11-12T15:00:00Z",
            },
            {
              code: "truthfulness",
              version: 1,
              accepted_at: "2026-11-12T15:00:00Z",
            },
          ],
        }),
      ]),
    });
    render(<Page />);

    expect(
      await screen.findByRole("checkbox", {
        name: "I hold a current NCCPA certification.",
      }),
    ).toBeChecked();
    expect(
      screen.getByRole("checkbox", {
        name: "I swear that the information in this application is true and accurate.",
      }),
    ).not.toBeChecked();
    await agreeToEverything();
    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    await waitFor(() => expect(push).toHaveBeenCalled());
    expect((await bodies(spy, ACCEPT)).map((b) => b.code).sort()).toEqual([
      "background_check",
      "truthfulness",
    ]);
  });

  it("names the state by its code when the list does not have it", async () => {
    answers({ "GET /api/public/states": ok([]) });
    render(<Page />);

    expect(
      await screen.findByText(/through KS's process within 60 days/),
    ).toBeInTheDocument();
  });

  it("does not submit until every statement is checked", async () => {
    const spy = answers();
    render(<Page />);
    await userEvent.type(
      await screen.findByRole("textbox", {
        name: "Type your full legal name *",
      }),
      "Jordan Alex Sample",
    );

    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    expect(await bodies(spy, SUBMIT)).toEqual([]);
  });

  it("asks the PA to read the statements again when one changed", async () => {
    answers({
      [SUBMIT]: failure("ATTESTATIONS_OUT_OF_DATE", 409, ["nccpa_current"]),
      "GET /api/public/attestations": [
        ok(ATTESTATIONS),
        ok([
          { ...ATTESTATIONS[0], version: 2, text: "Reworded." },
          ...ATTESTATIONS.slice(1),
        ]),
      ],
    });
    render(<Page />);
    await agreeToEverything();

    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    expect(
      await screen.findByRole("checkbox", { name: "Reworded." }),
    ).not.toBeChecked();
    expect(push).not.toHaveBeenCalled();
  });

  it.each([
    [
      "STATE_NOT_LIVE",
      "That state isn't taking applications. Choose another state.",
    ],
    ["INVALID_TRANSITION", "We couldn't save your answers. Try again."],
  ])("says what went wrong when submit answers %s", async (code, message) => {
    answers({ [SUBMIT]: failure(code) });
    render(<Page />);
    await agreeToEverything();

    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    expect(await screen.findByText(message)).toBeInTheDocument();
  });

  it("says the answers were not saved when the network fails", async () => {
    answers();
    render(<Page />);
    await agreeToEverything();
    vi.mocked(globalThis.fetch).mockRejectedValue(new TypeError("offline"));

    await userEvent.click(
      screen.getByRole("button", { name: "Submit application" }),
    );

    expect(
      await screen.findByText("We couldn't save your answers. Try again."),
    ).toBeInTheDocument();
  });

  it("goes back to the first step", async () => {
    answers();
    render(<Page />);

    expect(await screen.findByRole("link", { name: "Back" })).toHaveAttribute(
      "href",
      "/application",
    );
  });

  it("sends a PA with no open application to the first step", async () => {
    answers({ "GET /api/me/applications": ok([]) });
    render(<Page />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/application"));
  });

  it("leaves out sections whose statements the catalogue does not have", async () => {
    answers({ "GET /api/public/attestations": ok([ATTESTATIONS[0]]) });
    render(<Page />);

    expect(
      await screen.findByRole("heading", { name: "Statements" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Background check" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Sworn statement" }),
    ).not.toBeInTheDocument();
  });

  it("says when the application cannot be loaded", async () => {
    answers({ "GET /api/public/attestations": failure("NOT_FOUND", 404) });
    render(<Page />);

    expect(
      await screen.findByText(
        "We couldn't load your application. Try again later.",
      ),
    ).toBeInTheDocument();
  });

  it.each([
    ["loads", {}],
    ["fails", { "GET /api/public/attestations": failure("NOT_FOUND", 404) }],
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
