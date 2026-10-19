import { useTranslation } from "react-i18next";

import { SelectField } from "./SelectField";
import "src/styles/form.scss";

export interface CountryFieldProps {
  id: string;
  label?: string;
  required?: boolean;
  birthCountry?: boolean;
}

function CountryField({
  id,
  label,
  required,
  birthCountry = false,
}: CountryFieldProps) {
  const { t } = useTranslation("country");
  const options = t("countries", { returnObjects: true });
  if (birthCountry) {
    options.concat(t("birthCountries", { returnObjects: true })).sort();
  }

  return (
    <SelectField id={id} label={label} options={options} required={required} />
  );
}

export default CountryField;
