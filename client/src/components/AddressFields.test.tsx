import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AddressFields from "./AddressFields";
import { renderWithForm } from "../tests/util";

describe("AddressFields component", () => {
  it("renders fieldset with the given label as legend", () => {
    renderWithForm(
      <AddressFields id="home" label="Home Address" hint="Enter your address" />,
    );
    expect(screen.getByRole("group", { name: /Home Address/ })).toBeInTheDocument();
  });

  it("renders address line 1 and line 2 text inputs", () => {
    renderWithForm(
      <AddressFields id="home" label="Home Address" hint="Enter your address" />,
    );
    expect(
      screen.getByRole("textbox", { name: /Address line 1/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("textbox", { name: /Address line 2/i }),
    ).toBeInTheDocument();
  });

  it("renders city, state, and zip inputs", () => {
    renderWithForm(
      <AddressFields id="home" label="Home Address" hint="Enter your address" />,
    );
    expect(screen.getByRole("textbox", { name: /City/i })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /State/i })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Zip/i })).toBeInTheDocument();
  });

  it("renders a country select field", () => {
    renderWithForm(
      <AddressFields id="home" label="Home Address" hint="Enter your address" />,
    );
    expect(screen.getByRole("combobox")).toBeInTheDocument();
  });

  it("displays the hint text", () => {
    renderWithForm(
      <AddressFields id="home" label="Home Address" hint="Enter your mailing address" />,
    );
    expect(screen.getByText("Enter your mailing address")).toBeInTheDocument();
  });

  it("reflects typed value in address line 1 input", async () => {
    const user = userEvent.setup();
    renderWithForm(<AddressFields id="addr" label="Address" hint="hint" />);

    const line1Input = screen.getByRole("textbox", { name: /Address line 1/i });
    await user.type(line1Input, "123 Main St");

    expect(line1Input).toHaveValue("123 Main St");
  });
});
