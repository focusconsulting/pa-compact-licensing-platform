import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { SelectField } from "./SelectField";
import { renderWithForm } from "../tests/util";

describe("SelectField component", () => {
  const options = [
    ["foo", "Foo"],
    ["bar", "Bar"],
  ];

  it("renders with label and id", () => {
    renderWithForm(<SelectField id="some-id" label="some-name" />);
    const field = screen.getByRole("combobox", { name: /some-name/ });
    expect(field).toBeInstanceOf(HTMLSelectElement);
    expect(field).toHaveAttribute("id", "some-id");
  });

  it("is optional by default with enabled placeholder", () => {
    renderWithForm(<SelectField id="some-id" label="some-name" />);
    expect(screen.getByRole("combobox", { name: /some-name/ })).not.toBeRequired();
    const placeholder = screen.getByText("- Select -");
    expect(placeholder).toBeEnabled();
    expect(placeholder).toBeVisible();
  });

  it("renders required correctly with disabled placeholder", () => {
    renderWithForm(
      <SelectField id="req" label="required" required />,
    );
    expect(screen.getByRole("combobox", { name: /required/ })).toBeRequired();
    const placeholder = screen.getByText("- Select -");
    expect(placeholder).toBeDisabled();
  });

  it("renders all options", () => {
    renderWithForm(
      <SelectField id="some-id" label="some-name" options={options} />,
    );
    for (const [value, displayValue] of options) {
      const option = screen.getByRole("option", { name: displayValue });
      expect(option).toHaveValue(value);
    }
  });

  it("renders and submits form default value", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    renderWithForm(
      <SelectField id="some-id" label="some-name" options={options} />,
      { defaultValues: { "some-id": "bar" }, onSubmit: handler },
    );
    expect(screen.getByRole("combobox", { name: /some-name/ })).toHaveValue("bar");
    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ "some-id": "bar" }),
    );
  });

  it("submits user-selected value", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    renderWithForm(
      <SelectField id="some-id" label="some-name" options={options} />,
      { defaultValues: { "some-id": "bar" }, onSubmit: handler },
    );
    await user.selectOptions(screen.getByRole("combobox", { name: /some-name/ }), "foo");
    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(handler).toHaveBeenCalledWith(
      expect.objectContaining({ "some-id": "foo" }),
    );
  });
});
