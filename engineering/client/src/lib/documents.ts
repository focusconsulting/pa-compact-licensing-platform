import type { components } from "src/api/schema";
import { api } from "src/lib/api";

/** A document's details as the API returns them; `scan_status` is `clean` once it may be downloaded. */
export type DocumentDetails = components["schemas"]["DocumentOut"];

/** Where an upload goes: the signed-in PA's own documents, or a state's. */
export type UploadTarget =
  { kind: "me" } | { kind: "state"; stateCode: string };

/** The API's limit; checked here only to tell the user sooner (constitution Principle II). */
export const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;

/** Each file extension the API accepts, and the content type it declares for it. */
export const CONTENT_TYPES: Record<string, string> = {
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".csv": "text/csv",
  ".docx":
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

const SCAN_POLL_MS = 2000;

/** Why an upload did not finish, for the field to tell the user. */
export class UploadError extends Error {
  constructor(readonly reason: "rejected" | "failed") {
    super(reason);
  }
}

/** The content type the API expects for a file name, or undefined when it accepts none. */
export function contentTypeFor(fileName: string): string | undefined {
  const dot = fileName.lastIndexOf(".");
  return dot < 0 ? undefined : CONTENT_TYPES[fileName.slice(dot).toLowerCase()];
}

async function create(
  target: UploadTarget,
  body: components["schemas"]["DocumentUploadIn"],
) {
  if (target.kind === "me") {
    return api.POST("/api/me/documents", { body });
  }
  return api.POST("/api/states/{state_code}/documents", {
    params: { path: { state_code: target.stateCode } },
    body,
  });
}

async function details(target: UploadTarget, documentId: string) {
  if (target.kind === "me") {
    return api.GET("/api/me/documents/{document_id}", {
      params: { path: { document_id: documentId } },
    });
  }
  return api.GET("/api/states/{state_code}/documents/{document_id}", {
    params: { path: { state_code: target.stateCode, document_id: documentId } },
  });
}

/**
 * Creates the document, then posts the file straight to storage with the
 * returned form; the API never handles the bytes. Resolves to the `pending`
 * document. The form carries its own signature, so the post has no bearer token.
 */
export async function uploadDocument(
  target: UploadTarget,
  file: File,
  kind: string,
): Promise<DocumentDetails> {
  const contentType = contentTypeFor(file.name);
  if (!contentType) {
    throw new UploadError("failed");
  }
  const { data } = await create(target, {
    file_name: file.name,
    content_type: contentType as components["schemas"]["DocumentType"],
    size_bytes: file.size,
    kind,
  });
  if (!data) {
    throw new UploadError("failed");
  }
  const form = new FormData();
  Object.entries(data.data.upload.fields).forEach(([name, value]) =>
    form.append(name, value),
  );
  // Last: storage ignores fields after the file.
  form.append("file", file);
  const stored = await globalThis.fetch(data.data.upload.url, {
    method: "POST",
    body: form,
  });
  if (!stored.ok) {
    throw new UploadError("failed");
  }
  return data.data.document;
}

/**
 * Polls the document until its malware scan finishes. Resolves to the clean
 * document; rejects with `rejected` when malware was found and `failed` when
 * the file could not be checked. Stops when `signal` aborts.
 */
export async function waitForScan(
  target: UploadTarget,
  documentId: string,
  signal: AbortSignal,
  pollMs = SCAN_POLL_MS,
): Promise<DocumentDetails> {
  const { data } = await details(target, documentId);
  if (!data) {
    throw new UploadError("failed");
  }
  const status = data.data.scan_status;
  if (status === "clean") {
    return data.data;
  }
  if (status === "infected") {
    throw new UploadError("rejected");
  }
  if (status === "error") {
    throw new UploadError("failed");
  }
  signal.throwIfAborted();
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, pollMs);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(signal.reason);
      },
      { once: true },
    );
  });
  return waitForScan(target, documentId, signal, pollMs);
}
