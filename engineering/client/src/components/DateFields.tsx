import {
  DateInputGroup,
  FormGroup,
  Label,
  TextInput,
} from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";
import { useFormContext } from "react-hook-form";
import { useCallback, useEffect, useState, ChangeEvent } from "react";

import { SelectField } from "./SelectField";
import "src/styles/form.scss";

export interface DateFieldsProps {
  id: string;
  name?: string;
  optionalDay?: boolean;
  optionalMonth?: boolean;
  optionalYear?: boolean;
}

interface DatePartProps {
  id: string;
  label: string;
  unit: "day" | "year";
  length: number;
  required: boolean;
  defaultValue: string;
  onChange: (value: string) => void;
}

/** A day or year input. USWDS's DateInput can't mark its label required, so this builds the same markup with a Label that can. */
function DatePart({
  id,
  label,
  unit,
  length,
  required,
  defaultValue,
  onChange,
}: DatePartProps) {
  return (
    <FormGroup className={`usa-form-group--${unit}`}>
      <Label htmlFor={id} requiredMarker={required}>
        {label}
      </Label>
      <TextInput
        id={id}
        name={id}
        type="text"
        inputMode="numeric"
        maxLength={length}
        minLength={unit === "day" ? 1 : length}
        required={required}
        defaultValue={defaultValue}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          onChange(e.target.value)
        }
      />
    </FormGroup>
  );
}

/** Month, day, and year inputs, stored in the form as one YYYY-MM-DD value. */
export function DateFields({
  id,
  name,
  optionalDay = false,
  optionalMonth = false,
  optionalYear = false,
}: DateFieldsProps) {
  const { t } = useTranslation("date");
  const options = t("options", { returnObjects: true });
  const form = useFormContext();

  const [yearVal = "", monthVal = "", dayVal = ""] =
    form?.getValues(id)?.split("-") || [];
  const [monthState, setMonthState] = useState(monthVal);
  const [dayState, setDayState] = useState(dayVal);
  const [yearState, setYearState] = useState(yearVal);

  interface RenderValueProps {
    month?: string | null;
    day?: string | null;
    year?: string | null;
  }

  const renderValue = useCallback(
    ({
      month = null,
      day = null,
      year = null,
    }: RenderValueProps): string | null =>
      month && day && year ? `${year}-${month}-${day.padStart(2, "0")}` : null,
    [],
  );

  function updateValue({
    month = null,
    day = null,
    year = null,
  }: {
    month?: string | null;
    day?: string | null;
    year?: string | null;
  } = {}): void {
    if (month) setMonthState(month);
    if (day) setDayState(day);
    if (year) setYearState(year);
    form?.setValue(
      id,
      renderValue({
        month: month ?? monthState,
        day: day ?? dayState,
        year: year ?? yearState,
      }),
    );
  }

  useEffect(() => {
    form?.setValue(
      id,
      renderValue({ month: monthState, day: dayState, year: yearState }),
    );
    return () => {
      form?.setValue(id, null);
    };
  }, [form, id, renderValue, monthState, dayState, yearState]);

  return (
    <DateInputGroup id={`${id}Date`}>
      <FormGroup className="usa-form-group--month usa-form-group--select">
        <SelectField
          id={`${id}Month`}
          label={[name, t("month")].join(" ")}
          options={options}
          required={!optionalMonth}
          showValuesInLabels
          onChange={(e: ChangeEvent<HTMLInputElement>) =>
            updateValue({ month: e.target.value })
          }
          defaultValue={monthState}
        />
      </FormGroup>
      <DatePart
        id={`${id}Day`}
        label={[name, t("day")].join(" ")}
        unit="day"
        length={2}
        required={!optionalDay}
        defaultValue={dayState}
        onChange={(day) => updateValue({ day })}
      />
      <DatePart
        id={`${id}Year`}
        label={[name, t("year")].join(" ")}
        unit="year"
        length={4}
        required={!optionalYear}
        defaultValue={yearState}
        onChange={(year) => updateValue({ year })}
      />
    </DateInputGroup>
  );
}

export default DateFields;
