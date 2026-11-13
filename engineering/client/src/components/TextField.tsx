import { Label, TextInput } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import "src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import React, { ChangeEventHandler, FormEventHandler } from "react";

export interface TextFieldProps {
  id: string;
  label: string;
  hint?: string;
  type?: "text" | "email" | "number" | "password" | "search" | "tel" | "url";
  optional?: boolean;
  disabled?: boolean;
  onBeforeInput?: FormEventHandler;
  pattern?: string;
  placeholder?: string;
  minLength?: number;
  maxLength?: number;
  inputRef?: React.RefObject<HTMLInputElement>;
  onChange?: ChangeEventHandler;
  value?: string;
  /** What to fix, shown under the label with the field marked in error. */
  error?: string;
}

// TODO: forward
/**
 * A labelled USWDS text input with an optional hint. Registers with the
 * surrounding form unless given its own `onChange` or `inputRef`.
 */
export function TextField({
  id,
  label,
  hint,
  type = "text",
  optional = false,
  disabled = false,
  onBeforeInput,
  pattern,
  placeholder,
  minLength,
  maxLength,
  inputRef,
  onChange,
  value,
  error,
}: TextFieldProps) {
  const { t } = useTranslation("common");
  const register = useFormContext()?.register;

  const describedBy = [hint && `${id}Hint`, error && `${id}Error`]
    .filter(Boolean)
    .join(" ");

  // TODO: forward input props instead of drilling
  const field = (
    <>
      <Label
        htmlFor={id}
        hint={optional ? t("optionalText") : null}
        requiredMarker={!optional}
        error={Boolean(error)}
      >
        {label}
      </Label>
      {hint && (
        <span className="usa-hint" id={`${id}Hint`}>
          {hint}
        </span>
      )}
      {error && (
        <span className="usa-error-message" id={`${id}Error`}>
          {error}
        </span>
      )}
      <TextInput
        id={id}
        type={type}
        onBeforeInput={onBeforeInput}
        pattern={pattern}
        placeholder={placeholder}
        minLength={minLength}
        maxLength={maxLength}
        autoCorrect="off"
        autoCapitalize="on"
        required={!optional}
        disabled={disabled}
        value={value}
        validationStatus={error ? "error" : undefined}
        aria-describedby={describedBy || undefined}
        {...(!inputRef && !onChange && register
          ? register(id, { required: !optional })
          : { name: id, inputRef, onChange })}
      />
    </>
  );
  return error ? (
    <div className="usa-form-group usa-form-group--error">{field}</div>
  ) : (
    field
  );
}

export default TextField;
