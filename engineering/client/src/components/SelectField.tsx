import { Label, Select } from "@trussworks/react-uswds";

import "src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import React, { FormEventHandler } from "react";

export interface SelectFieldProps {
  id?: string;
  label?: string;
  hint?: string;
  options?: string[][];
  inputRef?: React.RefObject<HTMLSelectElement | null>;
  onChange?: FormEventHandler;
  defaultValue?: string;
  placeholder?: string;
  required?: boolean;
  showValuesInLabels?: boolean;
  /** What to fix, shown under the label; an empty string marks the field in error without a message. */
  error?: string;
}

/**
 * A labelled USWDS select of `[value, label]` options, with an optional hint. Registers with the
 * surrounding form unless given its own `onChange` or `inputRef`.
 */
export function SelectField({
  id,
  label,
  hint,
  options,
  inputRef,
  onChange,
  defaultValue,
  placeholder = "- Select -",
  required = false,
  showValuesInLabels = false,
  error,
}: SelectFieldProps) {
  const valueFilter = (val: string) => (val === "" ? null : val);
  const register = useFormContext()?.register;
  const selectReg =
    !onChange && !inputRef && id && register
      ? register(id, { required, setValueAs: valueFilter })
      : null;

  const optionElements = options?.map(([key, value]) => (
    <option value={key} key={key}>
      {showValuesInLabels ? [key, value].join(" - ") : value}
    </option>
  ));

  const describedBy = [hint && `${id}Hint`, error && `${id}Error`]
    .filter(Boolean)
    .join(" ");

  const field = (
    <>
      {label && (
        <Label
          htmlFor={id ?? ""}
          requiredMarker={required}
          error={Boolean(error)}
        >
          {label}
        </Label>
      )}
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
      <Select
        id={id ?? ""}
        validationStatus={error !== undefined ? "error" : undefined}
        aria-describedby={describedBy || undefined}
        defaultValue={defaultValue ?? ""}
        name={selectReg?.name ?? id ?? ""}
        required={required}
        inputRef={
          (inputRef ?? selectReg?.ref) as
            React.RefObject<HTMLSelectElement> | undefined
        }
        onBlur={selectReg?.onBlur}
        onChange={onChange ?? selectReg?.onChange}
      >
        {/* TODO: This should be selected by default. Selecting this option shouldn't count as a value */}
        <option hidden={required} disabled={required} key={null} value="">
          {placeholder}
        </option>
        {optionElements}
      </Select>
    </>
  );
  return error ? (
    <div className="usa-form-group usa-form-group--error">{field}</div>
  ) : (
    field
  );
}

export default SelectField;
