import { Fieldset } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import TextField from "./TextField.jsx";

import "/src/styles/form.scss";

export interface NameFieldsProps {
  id?: string;
  className?: string;
  label: string;
}

function NameFields({ id, className, label }: NameFieldsProps) {
  const { t } = useTranslation(["common", "basic"]);

  return (
    <Fieldset legend={label} className={[className, "legend-lg"].join(" ")}>
      <TextField
        id={id ? id + "FirstName" : "firstName"}
        label={t("basic:fields.name.firstNameTitle")}
      />
      <TextField
        id={id ? id + "MiddleName" : "middleName"}
        label={t("basic:fields.name.middleNameTitle")}
        optional
      />
      <TextField
        id={id ? id + "LastName" : "lastName"}
        label={t("basic:fields.name.lastNameTitle")}
      />
    </Fieldset>
  );
}

export default NameFields;
