import { useFormContext } from "react-hook-form";
import { DatePicker, Label } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import "/src/styles/form.scss";
import { useEffect } from "react";

export interface DatePickerFieldProps {
  id: string;
  label: string;
  hint?: string;
  optional?: boolean;
}

function DatePickerField({
  id,
  label,
  hint,
  optional = false,
}: DatePickerFieldProps) {
  const { t } = useTranslation("common");
  const form = useFormContext();
  const register = form?.register;
  const reg =
    id && register
      ? register(id, { required: false, shouldUnregister: true })
      : null;

  const updateValue = (val?: string) => {
    const date = val?.split("/");
    if (date) {
      const [month, day, year] = date;
      const newVal = `${year}-${month}-${day}`;
      form.setValue(id, newVal);
      void reg?.onChange({ target: { id, value: newVal } });
    }
  };

  useEffect(() => {
    return () => {
      form.setValue(id, null);
    };
  }, [form, id]);

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
