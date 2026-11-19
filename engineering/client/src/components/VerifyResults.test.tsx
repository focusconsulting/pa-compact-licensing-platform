import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations } from "src/tests/axe";
import { HOLDER_ID, summary } from "src/tests/verification";
import VerifyResults from "./VerifyResults";

const BY_NAME = { first_name: "Jordan", last_name: "Sample" };
const JUNIOR_ID = "0d1f5c2a-7b3e-4a6d-8c9f-1e2a3b4c5d6e";

describe("VerifyResults", () => {
  it("lists each PA with their states, linked to their page", async () => {
    const { container } = render(
      <VerifyResults
        search={BY_NAME}
        holders={[
          summary(),
          summary({ id: JUNIOR_ID, name_suffix: "Jr.", privilege_states: [] }),
        ]}
        page={{ number: 1, size: 25, total: 2 }}
        onPage={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 2, name: "Results (2)" }),
    ).toBeInTheDocument();
    const [, first, second] = screen.getAllByRole("row");
    expect(
      within(first).getByRole("link", { name: "Jordan Sample" }),
    ).toHaveAttribute(
      "href",
      `/verify/practitioner?id=${HOLDER_ID}&first_name=Jordan&last_name=Sample`,
    );
    expect(within(first).getByText("Kansas")).toBeInTheDocument();
    expect(within(first).getByText("Oklahoma, Missouri")).toBeInTheDocument();
    expect(
      within(second).getByRole("link", { name: "Jordan Sample Jr." }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("navigation")).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("says what a name search needs when no one matches", async () => {
    const { container } = render(
      <VerifyResults
        search={{ first_name: "Jordan", last_name: "Sampel" }}
        holders={[]}
        page={{ number: 1, size: 25, total: 0 }}
        onPage={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Results (0)" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No PA with a Compact Privilege is named Jordan Sampel/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).toBeNull();
    await expectNoAxeViolations(container);
  });

  it("names the number when no privilege has it", () => {
    render(
      <VerifyResults
        search={{ privilege_number: "PA-OK-999999" }}
        holders={[]}
        page={{ number: 1, size: 25, total: 0 }}
        onPage={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/No Compact Privilege has the number PA-OK-999999/),
    ).toBeInTheDocument();
  });

  it("pages through more results than fit, keeping the page in each PA's link", async () => {
    const onPage = vi.fn();
    const { container } = render(
      <VerifyResults
        search={BY_NAME}
        holders={[summary()]}
        page={{ number: 2, size: 25, total: 60 }}
        onPage={onPage}
      />,
    );

    expect(screen.getByRole("link", { name: "Jordan Sample" })).toHaveAttribute(
      "href",
      `/verify/practitioner?id=${HOLDER_ID}&first_name=Jordan&last_name=Sample&page=2`,
    );
    const pages = screen.getByRole("navigation", { name: "Pages of results" });
    await userEvent.click(within(pages).getByRole("button", { name: /Next/ }));
    await userEvent.click(
      within(pages).getByRole("button", { name: /Previous/ }),
    );
    await userEvent.click(
      within(pages).getByRole("button", { name: "Page 1" }),
    );

    expect(onPage.mock.calls).toEqual([[3], [1], [1]]);
    await expectNoAxeViolations(container);
  });
});
