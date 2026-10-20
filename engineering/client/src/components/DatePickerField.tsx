import { useFormContext } from "react-hook-form";
import { DatePicker, Label } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import "src/styles/form.scss";
import { useEffect } from "react";

export interface DatePickerFieldProps {
  id: string;
  label: string;
  hint?: string;
  optional?: boolean;
}

/** A USWDS date picker whose value is stored in the form as YYYY-MM-DD, or null when cleared. */
function DatePickerField({
  id,
  label,
  hint,
  optional = false,
}: DatePickerFieldProps) {
  const { t } = useTranslation("common");
  // Must be rendered inside a react-hook-form FormProvider.
  const form = useFormContext();
  const reg = form.register(id, { required: false, shouldUnregister: true });

  // The picker sends MM/DD/YYYY, or an empty string when the field is cleared.
  const updateValue = (val = "") => {
    const [month, day, year] = val.split("/");
    const newVal = month && day && year ? `${year}-${month}-${day}` : null;
    form.setValue(id, newVal);
    void reg.onChange({ target: { id, value: newVal } });
  };

  useEffect(
    () => () => {
      form.setValue(id, null);
    },
    [form, id],
  );

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
      <DatePicker
        id={id}
        name={id}
        onChange={updateValue}
        defaultValue={form?.getValues(id) as string}
        required={!optional}
      />
    </>
  );
}

export default DatePickerField;
