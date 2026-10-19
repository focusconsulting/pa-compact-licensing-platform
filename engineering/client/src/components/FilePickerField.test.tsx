import { describe, it, expect, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

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

  it("stores the chosen file's name", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" optional />,
      { onSubmit },
    );

    await user.upload(
      document.querySelector<HTMLInputElement>('input[type="file"]')!,
      new File(["x"], "proof.pdf"),
    );
    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(onSubmit.mock.calls[0][0].doc).toBe("proof.pdf");
  });

  it("restores a previously chosen file name from the form defaults", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithForm(<FilePickerField id="doc" label="Upload document" />, {
      defaultValues: { doc: "earlier.pdf" },
      onSubmit,
    });

    expect(document.querySelector('input[type="file"]')).not.toBeRequired();
    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit.mock.calls[0][0].doc).toBe("earlier.pdf");
  });

  it("restores a file name inside a field array", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    renderWithForm(
      <FilePickerField id="proofs.0.file" label="Upload document" />,
      {
        defaultValues: { proofs: [{ file: "first.pdf" }] },
        onSubmit,
      },
    );

    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit.mock.calls[0][0].proofs).toEqual([{ file: "first.pdf" }]);
  });
});
