import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations } from "src/tests/axe";
import { routeFetch } from "src/tests/fetch";
import { HOLDER_ID, holder } from "src/tests/verification";
import Page from "./page";

let query = "";
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(query),
}));

const HOLDER = `GET /api/public/privilege-holders/${HOLDER_ID}`;
const ok = (body: unknown) => Response.json({ data: body });
const refuse = (status: number) =>
  Response.json({ code: "ERROR", details: [] }, { status });

beforeEach(() => {
  vi.clearAllMocks();
  query = `id=${HOLDER_ID}`;
});

describe("a PA's public page", () => {
  it("shows the name, the state of qualifying license, and each privilege", async () => {
    routeFetch({ [HOLDER]: ok(holder({ name_suffix: "Jr." })) });
    const { container } = render(<Page />);

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Jordan Sample Jr.",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        level: 2,
        name: "State of qualifying license",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Kansas")).toBeInTheDocument();
    expect(
      screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent),
    ).toEqual(["Oklahoma", "Missouri", "Colorado"]);
    expect(screen.getByText("PA-OK-000001")).toBeInTheDocument();
    expect(screen.getByText("Oct 23, 2026")).toBeInTheDocument();
    expect(screen.getByText("Expires: Jun 30, 2027")).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("says only that a privilege expired, and of an inactive one only that it is inactive", async () => {
    routeFetch({ [HOLDER]: ok(holder()) });
    render(<Page />);

    const cards = await screen.findAllByRole("listitem");
    expect(within(cards[1]).getByText("Expired")).toBeInTheDocument();
    expect(within(cards[2]).getByText("Inactive")).toBeInTheDocument();
    expect(
      within(cards[2]).queryByText(/Deactivated|Expire/),
    ).not.toBeInTheDocument();
  });

  it("leads back to the results it was opened from", async () => {
    query = `id=${HOLDER_ID}&first_name=Jordan&last_name=Sample&page=2`;
    routeFetch({ [HOLDER]: ok(holder()) });
    render(<Page />);

    expect(
      await screen.findByRole("link", { name: "Back to results" }),
    ).toHaveAttribute(
      "href",
      "/verify?first_name=Jordan&last_name=Sample&page=2",
    );
  });

  it("offers a new search when it was opened from a link", async () => {
    routeFetch({ [HOLDER]: ok(holder()) });
    render(<Page />);

    expect(
      await screen.findByRole("link", { name: "Look up another PA" }),
    ).toHaveAttribute("href", "/verify");
  });

  it.each([
    ["is not listed", 404],
    ["has an address that is not a PA's", 422],
  ])("says so when the PA %s", async (_, status) => {
    routeFetch({ [HOLDER]: refuse(status) });
    const { container } = render(<Page />);

    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "We couldn't find that PA",
      }),
    ).toBeInTheDocument();
    await expectNoAxeViolations(container);
  });

  it("says so, and asks nothing of the API, when the address names no PA", () => {
    query = "";
    const fetchSpy = routeFetch({});
    render(<Page />);

    expect(
      screen.getByRole("heading", { name: "We couldn't find that PA" }),
    ).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("asks a visitor who is over the limit to wait", async () => {
    routeFetch({ [HOLDER]: refuse(429) });
    render(<Page />);

    expect(
      await screen.findByRole("heading", { name: "Too many searches" }),
    ).toBeInTheDocument();
  });

  it.each([
    ["the API fails", { [HOLDER]: refuse(500) }],
    ["the API cannot be reached", {}],
  ])("says the PA could not be looked up when %s", async (_, routes) => {
    routeFetch(routes);
    render(<Page />);

    expect(
      await screen.findByText("We couldn't look that up. Try again later."),
    ).toBeInTheDocument();
  });

  it.each([
    ["answers", { [HOLDER]: ok(holder()) }],
    ["fails", {}],
  ])(
    "ignores a lookup that %s after the visitor has left",
    async (_, routes) => {
      const fetchSpy = routeFetch(routes);
      const { unmount, container } = render(<Page />);
      unmount();

      await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
      await new Promise((resolve) => {
        setTimeout(resolve, 0);
      });

      expect(container).toBeEmptyDOMElement();
    },
  );
});
