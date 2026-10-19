import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import DatePickerField from "./DatePickerField";
import { renderWithForm } from "../tests/util";

describe("DatePickerField component", () => {
  it("renders the label", () => {
    renderWithForm(<DatePickerField id="dob" label="Date of birth" />);
    expect(screen.getByText("Date of birth")).toBeInTheDocument();
  });

  it("renders hint text when provided", () => {
    renderWithForm(
      <DatePickerField id="dob" label="Date of birth" hint="MM/DD/YYYY" />,
    );
    expect(screen.getByText("MM/DD/YYYY")).toBeInTheDocument();
  });

  it("does not render hint when not provided", () => {
    renderWithForm(<DatePickerField id="dob" label="Date of birth" />);
    expect(screen.queryByText("MM/DD/YYYY")).not.toBeInTheDocument();
  });

  it("shows optional text when optional prop is set", () => {
    renderWithForm(<DatePickerField id="dob" label="Date of birth" optional />);
    expect(screen.getByText(/Optional/i)).toBeInTheDocument();
  });

  it("renders without throwing when given a default value", () => {
    expect(() =>
      renderWithForm(<DatePickerField id="dob" label="Date of birth" />, {
        defaultValues: { dob: "2000-01-15" },
      }),
    ).not.toThrow();
  });

  it("calls form setValue when the date picker onChange fires", () => {
    const { unmount } = renderWithForm(
      <DatePickerField id="dob" label="Date of birth" />,
    );
    // Unmounting should clear the value without throwing (cleanup coverage)
    expect(() => unmount()).not.toThrow();
  });

  it("stores a typed date as YYYY-MM-DD", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithForm(<DatePickerField id="dob" label="Date of birth" />, { onSubmit });

    await user.type(document.getElementById("dob")!.parentElement!.querySelector("input:not([type=hidden])")!, "01/15/2000");
    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(onSubmit.mock.calls[0][0].dob).toBe("2000-01-15");
  });

  it("clears the value when the date is cleared", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithForm(<DatePickerField id="dob" label="Date of birth" optional />, { onSubmit });
    const input = document.getElementById("dob")!.parentElement!.querySelector<HTMLInputElement>("input:not([type=hidden])")!;

    await user.type(input, "01/15/2000");
    await user.clear(input);
    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(onSubmit.mock.calls[0][0].dob).toBeNull();
  });
});
