import { FileInput, FileInputRef, Label } from "@trussworks/react-uswds";
import { useTranslation } from "react-i18next";

import "/src/styles/form.scss";
import { useFormContext } from "react-hook-form";
import { ChangeEvent, useEffect, useRef, useState } from "react";

export interface FilePickerFieldProps {
  id: string;
  label: string;
  accept?: string;
  hint?: string;
  optional?: boolean;
  disabled?: boolean;
}

export function FilePickerField({
  id,
  label,
  accept,
  hint,
  optional = false,
  disabled = false,
}: FilePickerFieldProps) {
  const { t } = useTranslation("common");
  const form = useFormContext();
  const ref = useRef<FileInputRef | null>(null);
  const [, setLoaded] = useState(false);

  // TODO-maybe: more than just name
  const updateValue = (e: ChangeEvent<HTMLInputElement>) => {
    form?.setValue(id, e.target.files?.item(0)?.name);
  };

  // TODO: clean up this implementation
  useEffect(() => {
    function getFromFieldArray() {
      const [key, index, field] = id.split(".");
      return form?.formState?.defaultValues?.[key]?.[index]?.[field] as string;
    }
    const isFieldArray = id.split(".").length == 3;
    const data = isFieldArray
      ? getFromFieldArray()
      : (form?.formState?.defaultValues?.[id] as string);
    if (data) {
      ref.current!.files[0] = new File([], data);
      ref.current!.input!.required = false;
      form?.setValue(id, data);
      setLoaded(true);
    }
  }, [id, form, ref]);

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
      <FileInput
        id={id}
        name={id}
        accept={accept}
        required={!optional}
        disabled={disabled}
        onChange={updateValue}
        ref={ref}
      />
    </>
  );
}

export default FilePickerField;
