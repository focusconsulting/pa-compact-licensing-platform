import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { CognitoUserSession } from "amazon-cognito-identity-js";

import * as authLib from "src/lib/auth";
import { MAX_UPLOAD_BYTES } from "src/lib/documents";
import { routeFetch } from "src/tests/fetch";
import { FilePickerField } from "./FilePickerField";
import { renderWithForm } from "../tests/util";
import { expectNoAxeViolations } from "../tests/axe";

vi.mock("src/lib/auth");

const ID = "0b9c7a52-4f1e-4d38-9f43-2a5d6f1c8e70";
const DOCUMENT = {
  id: ID,
  file_name: "proof.pdf",
  content_type: "application/pdf",
  size_bytes: 1,
  kind: "proof",
  scan_status: "pending",
  created_at: "2026-11-05T15:04:05Z",
};

function upload(scanStatus: string | string[]) {
  const statuses = Array.isArray(scanStatus) ? scanStatus : [scanStatus];
  return routeFetch({
    "POST /api/me/documents": Response.json(
      {
        data: {
          document: DOCUMENT,
          upload: {
            url: "http://storage.test/documents",
            fields: { key: `documents/${ID}` },
            expires_at: "2026-11-05T15:09:05Z",
          },
        },
      },
      { status: 201 },
    ),
    "POST /documents": new Response(null, { status: 204 }),
    [`GET /api/me/documents/${ID}`]: statuses.map((scan_status) =>
      Response.json({ data: { ...DOCUMENT, scan_status } }),
    ),
  });
}

function fileInput() {
  return document.querySelector<HTMLInputElement>('input[type="file"]')!;
}

beforeEach(() => {
  vi.mocked(authLib.getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => "token" }),
  } as CognitoUserSession);
});

describe("FilePickerField component", () => {
  it("renders the label", () => {
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
    );
    expect(screen.getByText("Upload document")).toBeInTheDocument();
  });

  it("renders hint text when provided", () => {
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="proof"
        hint="PDF only"
      />,
    );
    expect(screen.getByText("PDF only")).toBeInTheDocument();
    expect(fileInput()).toHaveAttribute("aria-describedby", "docHint");
  });

  it("shows optional text when optional prop is set", () => {
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="proof"
        optional
      />,
    );
    expect(screen.getByText(/Optional/i)).toBeInTheDocument();
  });

  it("renders with accept attribute when provided", () => {
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="proof"
        accept=".pdf"
      />,
    );
    expect(fileInput()).toHaveAttribute("accept", ".pdf");
  });

  it("uploads the file, waits for its scan, and stores the document", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    upload("clean");
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="proof"
        optional
      />,
      { onSubmit },
    );

    await user.upload(fileInput(), new File(["%"], "proof.pdf"));
    expect(await screen.findByText("proof.pdf uploaded.")).toHaveAttribute(
      "role",
      "status",
    );
    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(onSubmit.mock.calls[0][0].doc).toEqual({
      id: ID,
      fileName: "proof.pdf",
    });
  });

  it("puts the status on its own line below the hint", async () => {
    const user = userEvent.setup();
    upload("clean");
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="proof"
        hint="PDF only"
      />,
    );

    await user.upload(fileInput(), new File(["%"], "proof.pdf"));

    expect(await screen.findByText("proof.pdf uploaded.")).toHaveClass(
      "margin-top-1",
    );
    expect(fileInput()).toHaveAttribute(
      "aria-describedby",
      "docHint docStatus",
    );
  });

  it("says it is checking the file while the scan runs", async () => {
    const user = userEvent.setup();
    upload("pending");
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
    );

    await user.upload(fileInput(), new File(["%"], "proof.pdf"));

    expect(
      await screen.findByText("Checking proof.pdf for viruses…"),
    ).toBeInTheDocument();
  });

  it.each([
    [
      "infected",
      "proof.pdf was rejected because it may contain a virus. Choose another file.",
    ],
    [
      "error",
      "proof.pdf could not be uploaded. Try again, or choose another file.",
    ],
  ])("leaves the field empty when the scan is %s", async (status, message) => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    upload(status);
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="proof"
        optional
      />,
      { onSubmit },
    );

    await user.upload(fileInput(), new File(["%"], "proof.pdf"));
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    await user.click(screen.getByRole("button", { name: "Submit" }));

    expect(onSubmit.mock.calls[0][0].doc).toBeUndefined();
    expect(fileInput().getAttribute("aria-describedby")).toBe("docStatus");
  });

  it("refuses a file of a type the API does not accept, without uploading it", async () => {
    const user = userEvent.setup();
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
    );

    await user.upload(fileInput(), new File(["MZ"], "tool.exe"));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "tool.exe is not a PDF, PNG, JPEG, CSV, or Word (.docx) file.",
    );
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("refuses a file over 20 MB, without uploading it", async () => {
    const user = userEvent.setup();
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
    );
    const big = new File(["%"], "scan.pdf");
    Object.defineProperty(big, "size", { value: MAX_UPLOAD_BYTES + 1 });

    await user.upload(fileInput(), big);

    expect(screen.getByRole("alert")).toHaveTextContent(
      "scan.pdf is larger than 20 MB.",
    );
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("clears the message when the choice is cleared", async () => {
    const user = userEvent.setup();
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
    );
    await user.upload(fileInput(), new File(["MZ"], "tool.exe"));

    fireEvent.change(fileInput(), { target: { files: [] } });

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("drops an earlier upload's scan when another file is chosen", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    upload(["pending", "pending", "clean"]);
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="proof"
        optional
      />,
      { onSubmit },
    );
    await user.upload(fileInput(), new File(["%"], "first.pdf"));
    await screen.findByText("Checking first.pdf for viruses…");

    await user.upload(fileInput(), new File(["%"], "tool.exe"));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "tool.exe is not a PDF",
    );
  });

  it("stops checking when it unmounts", async () => {
    const user = userEvent.setup();
    const fetchSpy = upload("pending");
    const { unmount } = renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
    );
    await user.upload(fileInput(), new File(["%"], "proof.pdf"));
    await screen.findByText("Checking proof.pdf for viruses…");
    const calls = fetchSpy.mock.calls.length;

    unmount();

    expect(fetchSpy.mock.calls.length).toBe(calls);
  });

  it("uploads to a state's documents", async () => {
    const user = userEvent.setup();
    routeFetch({
      "POST /api/states/KS/documents": Response.json(
        { code: "FORBIDDEN", details: [] },
        { status: 403 },
      ),
    });
    renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload document"
        kind="order"
        target={{ kind: "state", stateCode: "KS" }}
      />,
    );

    await user.upload(fileInput(), new File(["%"], "order.pdf"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "order.pdf could not be uploaded.",
    );
  });

  it("says the upload failed when the network does", async () => {
    const user = userEvent.setup();
    routeFetch({});
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
    );

    await user.upload(fileInput(), new File(["%"], "proof.pdf"));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "proof.pdf could not be uploaded.",
    );
  });

  it("shows a document from the form defaults as the chosen file", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const earlier = { id: ID, fileName: "earlier.pdf" };
    renderWithForm(
      <FilePickerField id="doc" label="Upload document" kind="proof" />,
      {
        defaultValues: { doc: earlier },
        onSubmit,
      },
    );

    expect(fileInput()).not.toBeRequired();
    expect(screen.getByText("earlier.pdf uploaded.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit.mock.calls[0][0].doc).toEqual(earlier);
  });

  it("restores a document inside a field array", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const first = { id: ID, fileName: "first.pdf" };
    renderWithForm(
      <FilePickerField
        id="proofs.0.file"
        label="Upload document"
        kind="proof"
      />,
      { defaultValues: { proofs: [{ file: first }] }, onSubmit },
    );

    await user.click(screen.getByRole("button", { name: "Submit" }));
    expect(onSubmit.mock.calls[0][0].proofs).toEqual([{ file: first }]);
  });

  it("has no axe violations", async () => {
    const { container } = renderWithForm(
      <FilePickerField
        id="doc"
        label="Upload a document"
        kind="proof"
        hint="PDF only"
      />,
    );
    await expectNoAxeViolations(container);
  });
});
