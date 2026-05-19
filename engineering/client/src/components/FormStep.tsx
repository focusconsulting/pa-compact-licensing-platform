import { Button, Form, RequiredMarker } from "@trussworks/react-uswds";
import { FormEvent, ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";

import "/src/styles/form.scss";
import { FieldValues, FormProvider, UseFormReturn } from "react-hook-form";
import loader from "../assets/loader.svg";

export interface FormStepProps<T extends FieldValues> {
  onSubmit?: (event: FormEvent) => Promise<void> | void;
  onBack?: (event: FormEvent) => Promise<void> | void;
  title?: ReactNode;
  children: ReactNode;
  form?: UseFormReturn<T>;
  submitTitle?: string;
  submitIcon?: ReactNode;
  noRequiredMarker?: true | false;
  noPreventDefault?: true | false;
  noSpinner?: true | false;
}

function FormStep<T extends FieldValues>({
  onSubmit,
  onBack,
  title,
  children,
  form,
  submitTitle,
  submitIcon,
  noRequiredMarker = false,
  noPreventDefault = false,
  noSpinner = false,
}: FormStepProps<T>) {
  const { t } = useTranslation(["common", "basic"]);
  const [submitting, setSubmitting] = useState(false);

  const submitWrapper = (event: FormEvent) => {
    if (!noSpinner) setSubmitting(true);
    if (!noPreventDefault) {
      event.preventDefault();
    }
    if (onSubmit) {
      void onSubmit(event);
    }
  };

  const requiredMarker = (
    <>
      <p className="margin-bottom-2 font-body-md required-text-subtitle">
        {t("common:requiredText")} (<RequiredMarker />
        ).
      </p>
    </>
  );

  const buttons = (
    <>
      <div className="button-container width-full border-top border-base-lighter margin-top-9 padding-top-3">
        {onBack && (
          <Button type="button" onClick={onBack} outline>
            {t("common:backTitle")}
          </Button>
        )}
        <Button type="submit" form="form">
          {submitIcon}
          {submitTitle ?? t("common:nextTitle")}
        </Button>
      </div>
    </>
  );

  const overlay = (
    <>
      <div className="width-full height-full overlay">
        <img
          src={loader}
          alt="A spinner indicating the form is being submitted"
        />
      </div>
    </>
  );

  return (
    // TODO: collapse these elements as possible
    <div className="maxw-desktop-lg radius-lg bg-white padding-top-15 padding-bottom-10 desktop:padding-x-4 padding-x-2 width-full center-contents position-relative">
      {submitting && overlay}
      <div className="maxw-desktop width-full desktop:padding-x-4 padding-x-2">
        <Form onSubmit={submitWrapper} id="form" className="maxw-full" large>
          {title && (
            <h1 className="margin-top-0 margin-bottom-3 text-semibold">
              {title}
            </h1>
          )}
          {!noRequiredMarker && requiredMarker}
          {form ? <FormProvider {...form}>{children}</FormProvider> : children}
          {buttons}
        </Form>
      </div>
    </div>
  );
}

export default FormStep;
