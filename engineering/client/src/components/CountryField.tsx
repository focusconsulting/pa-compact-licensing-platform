import { useTranslation } from "react-i18next";

import { SelectField } from "./SelectField";
import "src/styles/form.scss";

export interface CountryFieldProps {
  id: string;
  label?: string;
  required?: boolean;
  birthCountry?: boolean;
}

/**
 * A select of countries. With `birthCountry`, also offers former countries
 * (such as Yugoslavia) that can appear as a place of birth.
 */
function CountryField({
  id,
  label,
  required,
  birthCountry = false,
}: CountryFieldProps) {
  const { t } = useTranslation("country");
  const countries = t("countries", { returnObjects: true });
  const options = birthCountry
    ? countries.concat(t("birthCountries", { returnObjects: true })).sort()
    : countries;

  return (
    <SelectField id={id} label={label} options={options} required={required} />
  );
}

export default CountryField;
