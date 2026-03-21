import { Label, TextInput } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import "/src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import { ChangeEventHandler, default as React, FormEventHandler } from "react";

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
}

// TODO: forward
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
}: TextFieldProps) {
  const { t } = useTranslation("common");
  const register = useFormContext()?.register;

  // TODO: forward input props instead of drilling
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
        <span className="usa-hint" id={id + "Hint"}>
          {hint}
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
        {...(!inputRef && !onChange && register
          ? register(id, { required: !optional })
          : { name: id, inputRef, onChange })}
      />
    </>
  );
}

export default TextField;
