import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { TextField } from "./TextField";
import { renderWithForm } from "../tests/util";

describe("TextField component", () => {
  it("renders with label and id", () => {
    renderWithForm(<TextField id="some-id" label="some-name" />);
    const field = screen.getByRole("textbox", { name: /some-name/ });
    expect(field).toBeInstanceOf(HTMLInputElement);
    expect(field).toHaveAttribute("id", "some-id");
  });

  it("is required by default", () => {
    renderWithForm(<TextField id="some-id" label="some-name" />);
    expect(screen.getByRole("textbox", { name: /some-name/ })).toBeRequired();
  });

  it("renders optional correctly", () => {
    renderWithForm(
      <TextField id="optional" label="optional" optional />,
    );
    expect(screen.getByRole("textbox", { name: /optional/ })).not.toBeRequired();
  });

  it("renders with hint", () => {
    renderWithForm(
      <TextField id="some-id" label="some-name" hint="some-hint" />,
    );
    const hint = screen.getByText("some-hint");
    expect(hint).toHaveClass("usa-hint");
  });

  it("renders with controlled value prop", () => {
    renderWithForm(
      <TextField
        id="some-id"
        label="some-name"
        value="hello"
        onChange={() => {}}
      />,
    );
    expect(screen.getByRole("textbox", { name: /some-name/ })).toHaveDisplayValue(
      "hello",
    );
  });

  it("renders disabled state", () => {
    renderWithForm(
      <TextField id="some-id" label="some-name" disabled />,
    );
    expect(screen.getByRole("textbox", { name: /some-name/ })).toBeDisabled();
  });
});
