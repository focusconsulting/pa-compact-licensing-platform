import { describe, it, expect, vi, beforeEach } from "vitest";
import type { CognitoUserSession } from "amazon-cognito-identity-js";

import * as authLib from "src/lib/auth";
import { routeFetch } from "src/tests/fetch";
import {
  UploadError,
  contentTypeFor,
  uploadDocument,
  waitForScan,
} from "./documents";

vi.mock("src/lib/auth");

const DOCUMENT = {
  id: "0b9c7a52-4f1e-4d38-9f43-2a5d6f1c8e70",
  file_name: "proof.pdf",
  content_type: "application/pdf",
  size_bytes: 3,
  kind: "proof",
  scan_status: "pending",
  created_at: "2026-11-05T15:04:05Z",
};

function created() {
  return Response.json(
    {
      data: {
        document: DOCUMENT,
        upload: {
          url: "http://storage.test/documents",
          fields: {
            key: `documents/${DOCUMENT.id}`,
            "Content-Type": "application/pdf",
          },
          expires_at: "2026-11-05T15:09:05Z",
        },
      },
    },
    { status: 201 },
  );
}

function scanned(scan_status: string) {
  return Response.json({ data: { ...DOCUMENT, scan_status } });
}

beforeEach(() => {
  vi.mocked(authLib.getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => "token" }),
  } as CognitoUserSession);
});

describe("contentTypeFor", () => {
  it("maps each accepted extension, whatever its case, and nothing else", () => {
    expect(contentTypeFor("Scan.JPEG")).toBe("image/jpeg");
    expect(contentTypeFor("roster.csv")).toBe("text/csv");
    expect(contentTypeFor("tool.exe")).toBeUndefined();
    expect(contentTypeFor("README")).toBeUndefined();
  });
});

describe("uploadDocument", () => {
  it("creates the document, then posts the form's fields and the file to storage", async () => {
    const fetchSpy = routeFetch({
      "POST /api/me/documents": created(),
      "POST /documents": new Response(null, { status: 204 }),
    });
    const file = new File(["%PD"], "proof.pdf");

    const document = await uploadDocument({ kind: "me" }, file, "proof");

    expect(document.id).toBe(DOCUMENT.id);
    const [create] = fetchSpy.mock.calls[0] as [Request];
    expect(await create.json()).toEqual({
      file_name: "proof.pdf",
      content_type: "application/pdf",
      size_bytes: 3,
      kind: "proof",
    });
    const [url, init] = fetchSpy.mock.calls[1] as [string, RequestInit];
    expect(url).toBe("http://storage.test/documents");
    const form = init.body as FormData;
    expect([...form.keys()]).toEqual(["key", "Content-Type", "file"]);
    expect(new Headers(init.headers).has("Authorization")).toBe(false);
  });

  it("uploads to a state's documents", async () => {
    routeFetch({
      "POST /api/states/KS/documents": created(),
      "POST /documents": new Response(null, { status: 204 }),
    });

    const document = await uploadDocument(
      { kind: "state", stateCode: "KS" },
      new File(["%PD"], "proof.pdf"),
      "order",
    );

    expect(document.scan_status).toBe("pending");
  });

  it.each([
    ["the type is not accepted", "tool.exe", {}],
    [
      "the API refuses it",
      "proof.pdf",
      {
        "POST /api/me/documents": Response.json(
          { code: "VALIDATION_ERROR", details: [] },
          { status: 422 },
        ),
      },
    ],
    [
      "storage refuses it",
      "proof.pdf",
      {
        "POST /api/me/documents": created(),
        "POST /documents": new Response("EntityTooLarge", { status: 400 }),
      },
    ],
  ])("fails when %s", async (_, name, routes) => {
    routeFetch(routes);

    await expect(
      uploadDocument({ kind: "me" }, new File(["%PD"], name), "proof"),
    ).rejects.toEqual(new UploadError("failed"));
  });
});

describe("waitForScan", () => {
  it("polls until the scan finds the file clean", async () => {
    const fetchSpy = routeFetch({
      [`GET /api/me/documents/${DOCUMENT.id}`]: [
        scanned("pending"),
        scanned("clean"),
      ],
    });

    const document = await waitForScan(
      { kind: "me" },
      DOCUMENT.id,
      new AbortController().signal,
      1,
    );

    expect(document.scan_status).toBe("clean");
    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it("reads a state's document", async () => {
    routeFetch({
      [`GET /api/states/KS/documents/${DOCUMENT.id}`]: scanned("clean"),
    });

    const document = await waitForScan(
      { kind: "state", stateCode: "KS" },
      DOCUMENT.id,
      new AbortController().signal,
    );

    expect(document.id).toBe(DOCUMENT.id);
  });

  it.each([
    ["infected", "rejected"],
    ["error", "failed"],
  ])("rejects a document whose scan is %s as %s", async (status, reason) => {
    routeFetch({ [`GET /api/me/documents/${DOCUMENT.id}`]: scanned(status) });

    await expect(
      waitForScan({ kind: "me" }, DOCUMENT.id, new AbortController().signal),
    ).rejects.toEqual(new UploadError(reason as "rejected" | "failed"));
  });

  it("fails when the API cannot find the document", async () => {
    routeFetch({
      [`GET /api/me/documents/${DOCUMENT.id}`]: Response.json(
        { code: "NOT_FOUND", details: [] },
        { status: 404 },
      ),
    });

    await expect(
      waitForScan({ kind: "me" }, DOCUMENT.id, new AbortController().signal),
    ).rejects.toEqual(new UploadError("failed"));
  });

  it("stops polling when aborted", async () => {
    routeFetch({
      [`GET /api/me/documents/${DOCUMENT.id}`]: scanned("pending"),
    });
    const controller = new AbortController();

    const waiting = waitForScan(
      { kind: "me" },
      DOCUMENT.id,
      controller.signal,
      60_000,
    );
    await vi.waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    controller.abort(new Error("gone"));

    await expect(waiting).rejects.toThrow("gone");
  });
});
