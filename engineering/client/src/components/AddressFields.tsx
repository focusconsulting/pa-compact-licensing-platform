import { Fieldset } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import CountryField from "./CountryField.jsx";
import TextField from "./TextField.jsx";

import "/src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import { ChangeEvent, useState, useEffect } from "react";

export interface AddressFieldsProps {
  id: string;
  label: string;
  hint: string;
  className?: string;
}

// TODO: Controller might simplify the line1/line2 logic (see: https://github.com/orgs/react-hook-form/discussions/2363)
// TODO: add formgroup to all components
function AddressFields({ id, label, hint, className }: AddressFieldsProps) {
  const { t } = useTranslation(["common", "address"]);
  const form = useFormContext();

  const [line1Val = "", line2Val = ""] = form.getValues(id)?.split("\n") || [];
  const [line1State, setLine1State] = useState(line1Val);
  const [line2State, setLine2State] = useState(line2Val);

  function updateValue({
    line1 = null,
    line2 = null,
  }: { line1?: string | null; line2?: string | null } = {}): void {
    if (line1 != null) setLine1State(line1);
    if (line2 != null) setLine2State(line2);
    const val = [line1 ?? line1State, line2 ?? line2State].join("\n");
    if (val != "\n") form?.setValue(id, val);
  }

  useEffect(() => {
    const val = [line1State, line2State].join("\n");
    if (val != "\n") form?.setValue(id, val);
    return () => {
      form?.setValue(id, null);
    };
  }, [form, id, line1State, line2State]);

  return (
    <Fieldset legend={label} className={[className, "legend-lg"].join(" ")}>
      <span className="usa-hint" id="addressHint">
        {hint}
      </span>

      <CountryField
        id={id + "Country"}
        label={t("address:fields.address.countryTitle")}
      />
      <TextField
        value={line1State}
        id={id + "Line1"}
        label={t("address:fields.address.address1Title")}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          updateValue({ line1: e.target.value })
        }
      />
      <TextField
        value={line2State}
        id={id + "Line2"}
        label={t("address:fields.address.address2Title")}
        hint={t("address:fields.address.address2Subtitle")}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          updateValue({ line2: e.target.value })
        }
        optional
      />
      <TextField
        id={id + "City"}
        label={t("address:fields.address.cityTitle")}
        optional
      />
      <TextField
        id={id + "State"}
        label={t("address:fields.address.stateTitle")}
      />
      <TextField
        id={id + "Zip"}
        label={t("address:fields.address.zipTitle")}
        optional
      />
    </Fieldset>
  );
}

export default AddressFields;
