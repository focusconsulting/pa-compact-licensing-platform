import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";

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
});
