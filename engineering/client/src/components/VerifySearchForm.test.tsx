import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { expectNoAxeViolations } from "src/tests/axe";
import VerifySearchForm from "./VerifySearchForm";

const search = () => screen.getByRole("button", { name: "Search" });

describe("VerifySearchForm", () => {
  it("searches by both names, without the spaces around them", async () => {
    const onSearch = vi.fn();
    const { container } = render(<VerifySearchForm onSearch={onSearch} />);

    expect(screen.getByRole("radio", { name: "Name" })).toBeChecked();
    await userEvent.type(
      screen.getByRole("textbox", { name: /First name/ }),
      " Jordan ",
    );
    await userEvent.type(
      screen.getByRole("textbox", { name: /Last name/ }),
      "Sample",
    );
    await userEvent.click(search());

    expect(onSearch).toHaveBeenCalledWith({
      first_name: "Jordan",
      last_name: "Sample",
    });
    await expectNoAxeViolations(container);
  });

  it("does not search with a name missing", async () => {
    const onSearch = vi.fn();
    render(<VerifySearchForm onSearch={onSearch} />);

    await userEvent.type(
      screen.getByRole("textbox", { name: /First name/ }),
      "Jordan",
    );
    await userEvent.click(search());

    expect(onSearch).not.toHaveBeenCalled();
  });

  it("searches by a Compact Privilege number alone", async () => {
    const onSearch = vi.fn();
    const { container } = render(<VerifySearchForm onSearch={onSearch} />);

    await userEvent.click(
      screen.getByRole("radio", { name: "Compact Privilege number" }),
    );
    expect(screen.queryByRole("textbox", { name: /Last name/ })).toBeNull();
    await userEvent.type(
      screen.getByRole("textbox", { name: /Compact Privilege number/ }),
      "pa-ok-000001 ",
    );
    await userEvent.click(search());

    expect(onSearch).toHaveBeenCalledWith({ privilege_number: "pa-ok-000001" });
    await expectNoAxeViolations(container);
  });

  it("goes back to searching by name", async () => {
    render(
      <VerifySearchForm
        search={{ privilege_number: "PA-OK-000001" }}
        onSearch={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("radio", { name: "Name" }));

    expect(
      screen.getByRole("textbox", { name: /First name/ }),
    ).toBeInTheDocument();
  });

  it("shows the search it was given", () => {
    const { unmount } = render(
      <VerifySearchForm
        search={{ first_name: "Jordan", last_name: "Sample" }}
        onSearch={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("textbox", { name: /First name/ }),
    ).toHaveDisplayValue("Jordan");
    expect(
      screen.getByRole("textbox", { name: /Last name/ }),
    ).toHaveDisplayValue("Sample");
    unmount();

    render(
      <VerifySearchForm
        search={{ privilege_number: "PA-OK-000001" }}
        onSearch={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("radio", { name: "Compact Privilege number" }),
    ).toBeChecked();
    expect(
      screen.getByRole("textbox", { name: /Compact Privilege number/ }),
    ).toHaveDisplayValue("PA-OK-000001");
  });
});
