import { Label } from "@trussworks/react-uswds";

import "/src/styles/form.scss";
import { useFormContext } from "react-hook-form";

export interface DisplayFieldProps {
  id: string;
  label: string;
  value?: string;
  hint?: string;
  labelClassName?: string;
  asCurrentDateInput?: boolean;
}

// TODO: dry out date formatting functions
function getFreshValues() {
  const date = new Date();
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, "0");
  const day = date.getDate().toString().padStart(2, "0");
  const value = `${year}-${month}-${day}`;
  const displayValue = `${month}/${day}/${year}`;

  return [value, displayValue];
}

function getFormValues(formVal: string) {
  const date = formVal.split("-");
  const [year, month, day] = date;
  const value = `${year}-${month}-${day}`;
  const displayValue = `${month}/${day}/${year}`;

  return [value, displayValue];
}

function DisplayField({
  id,
  label,
  value,
  hint,
  labelClassName,
  asCurrentDateInput = false,
}: DisplayFieldProps) {
  const form = useFormContext();
  let displayValue = value;
  if (asCurrentDateInput) {
    const formVal: string | null = form?.getValues(id) as string | null;
    [value, displayValue] = formVal ? getFormValues(formVal) : getFreshValues();
    if (!formVal) form?.setValue(id, value);
  }

  return (
    <>
      <Label htmlFor="{id}" className={labelClassName ?? "card-entry-heading"}>
        {label}
      </Label>
      {hint && (
        <span className="usa-hint" id={id + "Hint"}>
          {hint}
        </span>
      )}
      <div id={id}>{displayValue}</div>
    </>
  );
}

export default DisplayField;
