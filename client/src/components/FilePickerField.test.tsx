import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";

import { FilePickerField } from "./FilePickerField";
import { renderWithForm } from "../tests/util";

describe("FilePickerField component", () => {
  it("renders the label", () => {
    renderWithForm(<FilePickerField id="doc" label="Upload document" />);
    expect(screen.getByText("Upload document")).toBeInTheDocument();
  });

  it("renders hint text when provided", () => {
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" hint="PDF only" />,
    );
    expect(screen.getByText("PDF only")).toBeInTheDocument();
  });

  it("does not render hint when not provided", () => {
    renderWithForm(<FilePickerField id="doc" label="Upload document" />);
    expect(screen.queryByText("PDF only")).not.toBeInTheDocument();
  });

  it("shows optional text when optional prop is set", () => {
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" optional />,
    );
    expect(screen.getByText(/Optional/i)).toBeInTheDocument();
  });

  it("renders a file input", () => {
    renderWithForm(<FilePickerField id="doc" label="Upload document" />);
    const input = document.querySelector('input[type="file"]');
    expect(input).toBeInTheDocument();
  });

  it("renders with accept attribute when provided", () => {
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" accept=".pdf" />,
    );
    const input = document.querySelector('input[type="file"]');
    expect(input).toHaveAttribute("accept", ".pdf");
  });

  it("unmounts without throwing", () => {
    const { unmount } = renderWithForm(
      <FilePickerField id="doc" label="Upload document" />,
    );
    expect(() => unmount()).not.toThrow();
  });
});
