import { DateInput, DateInputGroup, FormGroup } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import SelectField from "./SelectField.jsx";

import "/src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import { useCallback, useEffect, useState, ChangeEvent } from "react";

export interface DateFieldsProps {
  id: string;
  name?: string;
  optionalDay?: boolean;
  optionalMonth?: boolean;
  optionalYear?: boolean;
}

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

  interface renderValueProps {
    month?: string | null;
    day?: string | null;
    year?: string | null;
  }

  const renderValue = useCallback(
    ({
      month = null,
      day = null,
      year = null,
    }: renderValueProps): string | null => {
      return month && day && year
        ? `${year}-${month}-${day.padStart(2, "0")}`
        : null;
    },
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
    <DateInputGroup id={id + "Date"}>
      <FormGroup className="usa-form-group--month usa-form-group--select">
        <SelectField
          id={id + "Month"}
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
      <DateInput
        id={id + "Day"}
        label={[name, t("day")].join(" ")}
        unit="day"
        maxLength={2}
        minLength={1}
        // @ts-expect-error requiredMarker is not in the type definition but is used by USWDS DateInput
        requiredMarker={!optionalDay}
        required={!optionalDay}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          updateValue({ day: e.target.value })
        }
        defaultValue={dayState}
      />
      <DateInput
        id={id + "Year"}
        label={[name, t("year")].join(" ")}
        unit="year"
        maxLength={4}
        minLength={4}
        // @ts-expect-error requiredMarker is not in the type definition but is used by USWDS DateInput
        requiredMarker={!optionalYear}
        required={!optionalYear}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          updateValue({ year: e.target.value })
        }
        defaultValue={yearState}
      />
    </DateInputGroup>
  );
}

export default DateFields;
