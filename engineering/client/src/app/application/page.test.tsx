import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { CognitoUserSession } from "amazon-cognito-identity-js";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuth } from "src/contexts/AuthContext";
import { getCurrentSession } from "src/lib/auth";
import {
  APPLICATION_ID,
  STATES,
  application,
  failure,
  ok,
  profile,
} from "src/tests/application";
import { expectNoAxeViolations } from "src/tests/axe";
import { routeFetch } from "src/tests/fetch";
import Page from "./page";

vi.mock("src/lib/auth");
vi.mock("src/contexts/AuthContext");
const push = vi.fn();
const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace }) }));

const APPLICATION = `/api/me/applications/${APPLICATION_ID}`;

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
    "GET /api/me/applications": ok([]),
    "GET /api/me/profile": ok(profile()),
    "GET /api/public/states": ok(STATES),
    "PATCH /api/me/profile": ok(profile()),
    "POST /api/me/applications": ok(application(), 201),
    [`PATCH ${APPLICATION}`]: ok(application()),
    ...overrides,
  });
}

async function bodies(spy: ReturnType<typeof routeFetch>, route: string) {
  const sent = spy.mock.calls
    .map(([input]) => input as Request)
    .filter((r) => `${r.method} ${new URL(r.url).pathname}` === route);
  return Promise.all(sent.map((r) => r.clone().json()));
}

async function fillDate(
  group: string,
  month: string,
  day: string,
  year: string,
) {
  const fields = within(screen.getByRole("group", { name: group }));
  await userEvent.selectOptions(fields.getByRole("combobox"), month);
  const [dayInput, yearInput] = fields.getAllByRole("textbox");
  await userEvent.type(dayInput, day);
  await userEvent.type(yearInput, year);
}

async function fillEverything() {
  await userEvent.type(
    await screen.findByRole("textbox", { name: "Address Line 1 *" }),
    "100 Sample Street",
  );
  await userEvent.type(
    screen.getByRole("textbox", { name: "City or town *" }),
    "Sample City",
  );
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "State or Province *" }),
    "KS",
  );
  await userEvent.type(
    screen.getByRole("textbox", { name: "ZIP code / Postal code *" }),
    "66601",
  );
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "State *" }),
    "OK",
  );
  await userEvent.type(
    screen.getByRole("textbox", { name: "License number *" }),
    "PA-000123",
  );
  await fillDate("License expiration date", "12", "31", "2027");
  await fillDate("Date of birth", "03", "14", "1988");
  await userEvent.type(
    screen.getByRole("textbox", { name: "NCCPA certification number *" }),
    "1234567",
  );
}

describe("the application's first step", () => {
  it("starts a PA's application with their license and details", async () => {
    const spy = answers();
    const { container } = render(<Page />);
    await fillEverything();

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/application/statements"),
    );
    expect(await bodies(spy, "PATCH /api/me/profile")).toEqual([
      {
        date_of_birth: "1988-03-14",
        residence: {
          line1: "100 Sample Street",
          line2: null,
          city: "Sample City",
          region: "KS",
          postal_code: "66601",
          country_code: "US",
        },
        nccpa_certification_number: "1234567",
        other_names: [],
      },
    ]);
    expect(await bodies(spy, "POST /api/me/applications")).toEqual([
      { sql_state_code: "OK" },
    ]);
    expect(await bodies(spy, `PATCH ${APPLICATION}`)).toEqual([
      {
        claimed_license_number: "PA-000123",
        claimed_license_expires_on: "2027-12-31",
        sql_state_code: "OK",
      },
    ]);
    await expectNoAxeViolations(container);
  });

  it("shows a draft as the PA left it, and keeps names it does not show", async () => {
    const spy = answers({
      "GET /api/me/applications": ok([
        application({
          claimed_license_number: "PA-9",
          claimed_license_expires_on: "2027-01-31",
        }),
      ]),
      "GET /api/me/profile": ok(
        profile({
          date_of_birth: "1988-03-14",
          residence: {
            line1: "1 Main Street",
            line2: "Apt 2",
            city: "Topeka",
            region: "KS",
            postal_code: "66601",
            country_code: "US",
          },
          nccpa_certification_number: "1234567",
          other_names: [
            {
              first_name: "Jo",
              middle_name: null,
              last_name: "Smith",
              name_suffix: null,
            },
            {
              first_name: null,
              middle_name: null,
              last_name: "Jones",
              name_suffix: null,
            },
          ],
        }),
      ),
    });
    render(<Page />);

    expect(
      await screen.findByRole("textbox", { name: /^Address Line 2/ }),
    ).toHaveValue("Apt 2");
    await userEvent.type(
      screen.getByRole("textbox", { name: /^Middle name/ }),
      "Lee",
    );
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => expect(push).toHaveBeenCalled());
    const [saved] = await bodies(spy, "PATCH /api/me/profile");
    expect(saved.other_names).toEqual([
      { first_name: "Jo", middle_name: "Lee", last_name: "Smith" },
      {
        first_name: null,
        middle_name: null,
        last_name: "Jones",
        name_suffix: null,
      },
    ]);
    expect(await bodies(spy, "POST /api/me/applications")).toEqual([]);
    expect(await bodies(spy, `PATCH ${APPLICATION}`)).toEqual([
      {
        claimed_license_number: "PA-9",
        claimed_license_expires_on: "2027-01-31",
      },
    ]);
  });

  it("shows the state's request and leaves its state as it is", async () => {
    const spy = answers({
      "GET /api/me/applications": ok([
        application({
          status: "info_requested",
          request_note: "Upload your NCCPA certificate.",
          claimed_license_number: "PA-9",
          claimed_license_expires_on: "2027-01-31",
        }),
      ]),
      "GET /api/me/profile": ok(
        profile({
          date_of_birth: "1988-03-14",
          residence: {
            line1: "1 Main Street",
            line2: null,
            city: "Topeka",
            region: "KS",
            postal_code: "66601",
            country_code: "US",
          },
          nccpa_certification_number: "1234567",
        }),
      ),
    });
    render(<Page />);

    expect(
      await screen.findByText("Upload your NCCPA certificate."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("combobox", { name: "State *" }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => expect(push).toHaveBeenCalled());
    expect(await bodies(spy, `PATCH ${APPLICATION}`)).toEqual([
      {
        claimed_license_number: "PA-9",
        claimed_license_expires_on: "2027-01-31",
      },
    ]);
  });

  it("sends a PA whose application is with the state to its receipt", async () => {
    answers({
      "GET /api/me/applications": ok([application({ status: "submitted" })]),
    });
    render(<Page />);

    await waitFor(() =>
      expect(replace).toHaveBeenCalledWith("/application/received"),
    );
  });

  it("sends an eligible PA to their dashboard", async () => {
    answers({
      "GET /api/me/applications": ok([application({ status: "eligible" })]),
    });
    render(<Page />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(
      screen.queryByRole("button", { name: "Continue" }),
    ).not.toBeInTheDocument();
  });

  it("shows what the state verified as text, and doesn't send it", async () => {
    const spy = answers({
      "GET /api/me/applications": ok([
        application({
          claimed_license_number: "PA-9",
          claimed_license_expires_on: "2027-01-31",
        }),
      ]),
      "GET /api/me/profile": ok(
        profile({
          date_of_birth: "1988-03-14",
          residence: {
            line1: "1 Main Street",
            line2: null,
            city: "Topeka",
            region: "KS",
            postal_code: "66601",
            country_code: "US",
          },
          nccpa_certification_number: "1234567",
          other_names: [
            {
              first_name: "Jo",
              middle_name: null,
              last_name: "Smith",
              name_suffix: null,
            },
          ],
          verified_fields: [
            "date_of_birth",
            "other_names",
            "nccpa_certification_number",
          ],
        }),
      ),
    });
    render(<Page />);

    expect(await screen.findByText("Mar 14, 1988")).toBeInTheDocument();
    expect(screen.getByText("Jo Smith")).toBeInTheDocument();
    expect(screen.getByText("1234567")).toBeInTheDocument();
    expect(
      screen.queryByRole("textbox", { name: /NCCPA/ }),
    ).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => expect(push).toHaveBeenCalled());
    const [saved] = await bodies(spy, "PATCH /api/me/profile");
    expect(Object.keys(saved)).toEqual(["residence"]);
  });

  it("leaves out verified other names when there are none", async () => {
    answers({
      "GET /api/me/applications": ok([application()]),
      "GET /api/me/profile": ok(profile({ verified_fields: ["other_names"] })),
    });
    render(<Page />);

    await screen.findByRole("button", { name: "Continue" });
    expect(
      screen.queryByText("Other names you use or have used (optional)"),
    ).not.toBeInTheDocument();
  });

  it("asks for a last name when another name has only a first name", async () => {
    const spy = answers();
    render(<Page />);
    await fillEverything();
    await userEvent.type(
      screen.getByRole("textbox", { name: /^First name/ }),
      "Jo",
    );

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(
      await screen.findByText(/Enter a last name for the other name/),
    ).toBeInTheDocument();
    expect(await bodies(spy, "PATCH /api/me/profile")).toEqual([]);
  });

  it("says when the chosen state stopped taking applications", async () => {
    answers({ "POST /api/me/applications": failure("STATE_NOT_LIVE") });
    render(<Page />);
    await fillEverything();

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(
      await screen.findByText(
        "That state isn't taking applications. Choose another state.",
      ),
    ).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });

  it.each([
    ["the API refuses", failure("VALIDATION_ERROR", 422)],
    ["the API answers with no code", new Response(null, { status: 500 })],
  ])("says the answers were not saved when %s", async (_, answer) => {
    answers({ "PATCH /api/me/profile": answer });
    render(<Page />);
    await fillEverything();

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(
      await screen.findByText("We couldn't save your answers. Try again."),
    ).toBeInTheDocument();
  });

  it("says the answers were not saved when the network fails", async () => {
    answers();
    render(<Page />);
    await fillEverything();
    vi.mocked(globalThis.fetch).mockRejectedValue(new TypeError("offline"));

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(
      await screen.findByText("We couldn't save your answers. Try again."),
    ).toBeInTheDocument();
  });

  it("says when the application cannot be loaded", async () => {
    answers({ "GET /api/me/profile": failure("NOT_FOUND", 404) });
    render(<Page />);

    expect(
      await screen.findByText(
        "We couldn't load your application. Try again later.",
      ),
    ).toBeInTheDocument();
  });

  it.each([
    ["loads", {}],
    ["fails", { "GET /api/me/profile": failure("NOT_FOUND", 404) }],
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
