import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations } from "src/tests/axe";
import { routeFetch } from "src/tests/fetch";
import { found, summary } from "src/tests/verification";
import Page from "./page";

const push = vi.fn();
let query = "";
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  useSearchParams: () => new URLSearchParams(query),
}));

const SEARCH = "GET /api/public/privilege-holders";

beforeEach(() => {
  vi.clearAllMocks();
  query = "";
});

describe("the public verification page", () => {
  it("shows the search alone, and asks nothing of the API, until someone searches", async () => {
    const fetchSpy = routeFetch({});
    const { container } = render(<Page />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Look up a Compact Privilege",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2 })).toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
    await expectNoAxeViolations(container);
  });

  it("puts a search in the address", async () => {
    render(<Page />);

    await userEvent.type(
      screen.getByRole("textbox", { name: /First name/ }),
      "Jordan",
    );
    await userEvent.type(
      screen.getByRole("textbox", { name: /Last name/ }),
      "Sample",
    );
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(push).toHaveBeenCalledWith(
      "/verify?first_name=Jordan&last_name=Sample",
    );
  });

  it("shows the results of the search in the address, under the search", async () => {
    query = "first_name=Jordan&last_name=Sample";
    const fetchSpy = routeFetch({ [SEARCH]: found([summary()]) });
    const { container } = render(<Page />);

    expect(
      await screen.findByRole("link", { name: "Jordan Sample" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: /First name/ }),
    ).toHaveDisplayValue("Jordan");
    const [request] = fetchSpy.mock.calls[0] as [Request];
    expect(new URL(request.url).search).toBe(
      "?first_name=Jordan&last_name=Sample&page=1",
    );
    await expectNoAxeViolations(container);
  });

  it("asks for the page in the address, and moves to another", async () => {
    query = "privilege_number=PA-OK-000001&page=2";
    const fetchSpy = routeFetch({ [SEARCH]: found([summary()], 60) });
    render(<Page />);

    await userEvent.click(await screen.findByRole("button", { name: /Next/ }));

    const [request] = fetchSpy.mock.calls[0] as [Request];
    expect(new URL(request.url).searchParams.get("page")).toBe("2");
    expect(push).toHaveBeenCalledWith(
      "/verify?privilege_number=PA-OK-000001&page=2",
    );
  });

  it("asks a visitor who is over the limit to wait, keeping their search", async () => {
    query = "first_name=Jordan&last_name=Sample";
    routeFetch({
      [SEARCH]: Response.json(
        { code: "RATE_LIMITED", details: [] },
        { status: 429 },
      ),
    });
    const { container } = render(<Page />);

    expect(
      await screen.findByRole("heading", { name: "Too many searches" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: /Last name/ }),
    ).toHaveDisplayValue("Sample");
    expect(screen.queryByText(/Results/)).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("says when the search could not be made", async () => {
    query = "first_name=Jordan&last_name=Sample";
    routeFetch({});
    render(<Page />);

    expect(
      await screen.findByText("We couldn't look that up. Try again later."),
    ).toBeInTheDocument();
  });

  it("drops one search's results when the address changes to another", async () => {
    query = "first_name=Jordan&last_name=Sample";
    routeFetch({
      [SEARCH]: [found([summary()]), found([summary({ last_name: "Other" })])],
    });
    const { rerender } = render(<Page />);
    await screen.findByRole("link", { name: "Jordan Sample" });

    query = "first_name=Jordan&last_name=Other";
    rerender(<Page />);

    expect(screen.queryByRole("link", { name: "Jordan Sample" })).toBeNull();
    expect(
      await screen.findByRole("link", { name: "Jordan Other" }),
    ).toBeInTheDocument();
  });

  it("clears the results when the visitor switches the kind of search, until they search again", async () => {
    query = "first_name=Jordan&last_name=Sample";
    routeFetch({ [SEARCH]: found([summary()]) });
    render(<Page />);
    await screen.findByRole("link", { name: "Jordan Sample" });

    await userEvent.click(
      screen.getByRole("radio", { name: "Compact Privilege number" }),
    );

    expect(screen.queryByRole("link", { name: "Jordan Sample" })).toBeNull();
    expect(screen.queryByRole("heading", { level: 2 })).toBeNull();

    await userEvent.click(screen.getByRole("radio", { name: "Name" }));
    await userEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(
      screen.getByRole("link", { name: "Jordan Sample" }),
    ).toBeInTheDocument();
  });

  it.each([
    ["answers", { [SEARCH]: found([summary()]) }],
    ["fails", {}],
  ])(
    "ignores a search that %s after the visitor has left",
    async (_, routes) => {
      query = "first_name=Jordan&last_name=Sample";
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
