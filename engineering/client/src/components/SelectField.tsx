import { Label, Select } from "@trussworks/react-uswds";

import "/src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import { default as React, FormEventHandler } from "react";

export interface SelectFieldProps {
  id?: string;
  label?: string;
  options?: string[][];
  inputRef?: React.RefObject<HTMLSelectElement | null>;
  onChange?: FormEventHandler;
  defaultValue?: string;
  placeholder?: string;
  required?: boolean;
  showValuesInLabels?: boolean;
}

export function SelectField({
  id,
  label,
  options,
  inputRef,
  onChange,
  defaultValue,
  placeholder = "- Select -",
  required = false,
  showValuesInLabels = false,
}: SelectFieldProps) {
  const valueFilter = (val: string) => {
    return val == "" ? null : val;
  };
  const register = useFormContext()?.register;
  const selectReg =
    !onChange && !inputRef && id && register
      ? register(id, { required, setValueAs: valueFilter })
      : null;

  const optionElements = options?.map(([key, value]) => {
    return (
      <option value={key} key={key}>
        {showValuesInLabels ? [key, value].join(" - ") : value}
      </option>
    );
  });

  return (
    <>
      {label && (
        <Label htmlFor={id ?? ""} requiredMarker={required}>
          {label}
        </Label>
      )}
      <Select
        id={id ?? ""}
        defaultValue={defaultValue ?? ""}
        name={selectReg?.name ?? id ?? ""}
        required={required}
        inputRef={(inputRef ?? selectReg?.ref ?? undefined) as React.RefObject<HTMLSelectElement> | undefined}
        onBlur={selectReg?.onBlur ?? undefined}
        onChange={onChange ?? selectReg?.onChange ?? undefined}
      >
        {/*TODO: This should be selected by default. Selecting this option shouldn't count as a value*/}
        <option hidden={required} disabled={required} key={null} value="">
          {placeholder}
        </option>
        {optionElements?.length && optionElements}
      </Select>
    </>
  );
}

export default SelectField;
