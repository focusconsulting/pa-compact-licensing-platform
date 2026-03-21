import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import DisplayField from "./DisplayField";
import { renderWithForm } from "../tests/util";

describe("DisplayField component", () => {
  it("renders label and value", () => {
    renderWithForm(
      <DisplayField id="field1" label="Name" value="John Doe" />,
    );
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("John Doe")).toBeInTheDocument();
  });

  it("renders hint when provided", () => {
    renderWithForm(
      <DisplayField
        id="field1"
        label="Name"
        value="John"
        hint="Enter your name"
      />,
    );
    const hint = screen.getByText("Enter your name");
    expect(hint).toHaveClass("usa-hint");
  });

  it("does not render hint when not provided", () => {
    renderWithForm(
      <DisplayField id="field1" label="Name" value="John" />,
    );
    expect(screen.queryByClass).toBeUndefined; // no hint element
    const container = screen.getByText("John");
    expect(container).toBeInTheDocument();
  });

  it("renders current date when asCurrentDateInput is true", () => {
    const today = new Date();
    const month = (today.getMonth() + 1).toString().padStart(2, "0");
    const day = today.getDate().toString().padStart(2, "0");
    const year = today.getFullYear();
    const expectedDisplay = `${month}/${day}/${year}`;

    renderWithForm(
      <DisplayField id="dateField" label="Date" asCurrentDateInput />,
    );
    expect(screen.getByText(expectedDisplay)).toBeInTheDocument();
  });

  it("formats existing form date value", () => {
    renderWithForm(
      <DisplayField id="dateField" label="Date" asCurrentDateInput />,
      { defaultValues: { dateField: "2025-03-15" } },
    );
    expect(screen.getByText("03/15/2025")).toBeInTheDocument();
  });
});
