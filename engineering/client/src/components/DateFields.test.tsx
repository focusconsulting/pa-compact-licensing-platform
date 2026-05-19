import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { DateFields } from "./DateFields";
import { renderWithForm } from "../tests/util";

describe("DateFields component", () => {
  // DateFields labels are " Month", " Day", " Year" (name prefix + label joined with space)
  // When no name is provided, the prefix is undefined, so labels become "undefined Month" etc.
  // Actually looking at the code: [name, t("month")].join(" ") where name is optional

  it("renders month, day, and year inputs", () => {
    renderWithForm(<DateFields id="some-id" />);
    expect(screen.getByRole("combobox", { name: /Month/ })).toBeInstanceOf(HTMLSelectElement);
    expect(screen.getByRole("textbox", { name: /Day/ })).toBeInstanceOf(HTMLInputElement);
    expect(screen.getByRole("textbox", { name: /Year/ })).toBeInstanceOf(HTMLInputElement);
  });

  it("is required by default", () => {
    renderWithForm(<DateFields id="some-id" />);
    expect(screen.getByRole("combobox", { name: /Month/ })).toBeRequired();
    expect(screen.getByRole("textbox", { name: /Day/ })).toBeRequired();
    expect(screen.getByRole("textbox", { name: /Year/ })).toBeRequired();
  });

  it("renders optional correctly", () => {
    renderWithForm(
      <DateFields
        id="some-id"
        optionalYear
        optionalMonth
        optionalDay
      />,
    );
    expect(screen.getByRole("combobox", { name: /Month/ })).not.toBeRequired();
    expect(screen.getByRole("textbox", { name: /Day/ })).not.toBeRequired();
    expect(screen.getByRole("textbox", { name: /Year/ })).not.toBeRequired();
  });

  it("renders with default value from form", () => {
    renderWithForm(<DateFields id="some-id" />, {
      defaultValues: { "some-id": "2025-01-10" },
    });
    expect(screen.getByRole("combobox", { name: /Month/ })).toHaveValue("01");
    expect(screen.getByRole("textbox", { name: /Day/ })).toHaveValue("10");
    expect(screen.getByRole("textbox", { name: /Year/ })).toHaveValue("2025");
  });

  it("submits user input", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    renderWithForm(<DateFields id="some-id" />, {
      defaultValues: { "some-id": "2025-01-10" },
      onSubmit: handler,
    });

    await user.clear(screen.getByRole("textbox", { name: /Day/ }));
    await user.type(screen.getByRole("textbox", { name: /Day/ }), "20");
    await user.clear(screen.getByRole("textbox", { name: /Year/ }));
    await user.type(screen.getByRole("textbox", { name: /Year/ }), "2026");
    await user.selectOptions(screen.getByRole("combobox", { name: /Month/ }), "02");

    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ "some-id": "2026-02-20" }),
    );
  });
});
