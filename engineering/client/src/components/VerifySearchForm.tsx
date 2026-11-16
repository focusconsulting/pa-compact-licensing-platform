"use client";

import { Button, Fieldset, Form, Radio } from "@trussworks/react-uswds";
import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { TextField } from "src/components/TextField";
import type { Search } from "src/lib/verification";

interface Values {
  first_name: string;
  last_name: string;
  privilege_number: string;
}

export interface VerifySearchFormProps {
  /** The search to show filled in, as on a page of its results. */
  search?: Search | null;
  onSearch: (search: Search) => void;
}

/**
 * Public verification's search (V1, V1n): both names, or a privilege number.
 * The browser stops an empty or malformed search; the API decides what matches.
 */
export default function VerifySearchForm({
  search = null,
  onSearch,
}: VerifySearchFormProps) {
  const { t } = useTranslation("verify");
  const [byNumber, setByNumber] = useState(
    search !== null && "privilege_number" in search,
  );
  // The other search's fields leave the form with their inputs, so they are never required.
  const form = useForm<Values>({
    shouldUnregister: true,
    defaultValues: { ...search },
  });

  const submit = (values: Values) =>
    onSearch(
      byNumber
        ? { privilege_number: values.privilege_number.trim() }
        : {
            first_name: values.first_name.trim(),
            last_name: values.last_name.trim(),
          },
    );

  return (
    <FormProvider {...form}>
      <Form onSubmit={form.handleSubmit(submit)} large>
        <p className="text-base">{t("required")}</p>
        <Fieldset legend={t("form.legend")}>
          <Radio
            id="search-by-name"
            name="search-by"
            label={t("form.byName")}
            checked={!byNumber}
            onChange={() => setByNumber(false)}
          />
          <Radio
            id="search-by-number"
            name="search-by"
            label={t("form.byNumber")}
            checked={byNumber}
            onChange={() => setByNumber(true)}
          />
        </Fieldset>
        {byNumber ? (
          <TextField
            id="privilege_number"
            label={t("form.number")}
            hint={t("form.numberHint")}
            pattern="\s*[Pp][Aa]-[A-Za-z]{2}-[0-9]{6,}\s*"
          />
        ) : (
          <>
            <TextField
              id="first_name"
              label={t("form.firstName")}
              hint={t("form.nameHint")}
              pattern=".*\S.*"
              maxLength={100}
            />
            <TextField
              id="last_name"
              label={t("form.lastName")}
              pattern=".*\S.*"
              maxLength={100}
            />
          </>
        )}
        <Button type="submit">{t("form.search")}</Button>
      </Form>
    </FormProvider>
  );
}
