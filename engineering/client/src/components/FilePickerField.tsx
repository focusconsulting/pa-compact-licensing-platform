import { FileInput, FileInputRef, Label } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import "src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import { ChangeEvent, useEffect, useRef, useState } from "react";

import {
  MAX_UPLOAD_BYTES,
  UploadError,
  UploadTarget,
  contentTypeFor,
  uploadDocument,
  waitForScan,
} from "src/lib/documents";

/** What the field stores in the form: the uploaded document, once its scan is clean. */
export interface UploadedDocument {
  id: string;
  fileName: string;
}

export interface FilePickerFieldProps {
  id: string;
  label: string;
  /** What the document is, such as `nccpa_certificate`; free text until Q-07. */
  kind: string;
  /** Whose documents it joins; the PA's own unless a state's. */
  target?: UploadTarget;
  accept?: string;
  hint?: string;
  optional?: boolean;
  disabled?: boolean;
}

type Status =
  | { state: "idle" }
  | { state: "uploading" | "scanning" | "uploaded"; name: string }
  | {
      state: "tooLarge" | "wrongType" | "rejected" | "failed";
      name: string;
    };

const ME: UploadTarget = { kind: "me" };

/**
 * A USWDS file input that uploads the chosen file, waits for its malware scan,
 * and stores `{ id, fileName }` in the form once it is clean. A failed or
 * rejected file leaves the field empty. A value in the form's defaults shows as
 * the chosen file.
 */
export function FilePickerField({
  id,
  label,
  kind,
  target = ME,
  accept,
  hint,
  optional = false,
  disabled = false,
}: FilePickerFieldProps) {
  const { t } = useTranslation("common");
  const form = useFormContext();
  const ref = useRef<FileInputRef | null>(null);
  const pending = useRef<AbortController | null>(null);
  const [status, setStatus] = useState<Status>({ state: "idle" });

  useEffect(() => {
    const restored = form?.getValues(id) as UploadedDocument | undefined;
    if (restored?.fileName && ref.current) {
      ref.current.files[0] = new File([], restored.fileName);
      ref.current.input!.required = false;
      setStatus({ state: "uploaded", name: restored.fileName });
    }
  }, [id, form]);

  // Stop polling when the field goes away.
  useEffect(() => () => pending.current?.abort(), []);

  const upload = async (e: ChangeEvent<HTMLInputElement>) => {
    pending.current?.abort();
    form?.setValue(id, undefined);
    const file = e.target.files?.[0];
    if (!file) {
      setStatus({ state: "idle" });
      return;
    }
    const { name } = file;
    if (!contentTypeFor(name)) {
      setStatus({ state: "wrongType", name });
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setStatus({ state: "tooLarge", name });
      return;
    }
    const controller = new AbortController();
    pending.current = controller;
    try {
      setStatus({ state: "uploading", name });
      const document = await uploadDocument(target, file, kind);
      setStatus({ state: "scanning", name });
      await waitForScan(target, document.id, controller.signal);
      form?.setValue(id, { id: document.id, fileName: name });
      setStatus({ state: "uploaded", name });
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      const reason = error instanceof UploadError ? error.reason : "failed";
      setStatus({ state: reason, name });
    }
  };

  const isError = ["tooLarge", "wrongType", "rejected", "failed"].includes(
    status.state,
  );
  const message =
    status.state === "idle"
      ? null
      : t(`filePicker.${status.state}`, { name: status.name });
  const describedBy = [hint && `${id}Hint`, message && `${id}Status`]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      <Label
        htmlFor={id}
        hint={optional ? t("optionalText") : null}
        requiredMarker={!optional}
      >
        {label}
      </Label>
      {hint && (
        <span className="usa-hint" id={`${id}Hint`}>
          {hint}
        </span>
      )}
      <span
        id={`${id}Status`}
        className={isError ? "usa-error-message" : "usa-hint"}
        role={isError ? "alert" : "status"}
      >
        {message}
      </span>
      <FileInput
        id={id}
        name={id}
        accept={accept}
        required={!optional}
        disabled={disabled}
        onChange={upload}
        aria-describedby={describedBy || undefined}
        ref={ref}
      />
    </>
  );
}

export default FilePickerField;
