"use client";

import { Button, Checkbox, Form } from "@trussworks/react-uswds";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { FormProvider, UseFormReturn, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import AlertBanner from "src/components/AlertBanner";
import PageHeading from "src/components/PageHeading";
import ProtectedRoute from "src/components/ProtectedRoute";
import StepIndicator from "src/components/StepIndicator";
import { TextField } from "src/components/TextField";
import {
  Application,
  ApplicationError,
  Attestation,
  acceptAttestation,
  accepted,
  loadApplications,
  loadAttestations,
  loadStates,
  loadUnattached,
  openApplication,
  submitApplication,
} from "src/lib/application";

const BACKGROUND_CHECK = "background_check";
const SWORN = "truthfulness";

type Values = Record<string, boolean | string>;
type ErrorKey = "save" | "stateNotLive" | "statementsChanged";

interface StatementProps {
  attestation: Attestation;
  form: UseFormReturn<Values>;
  label?: string;
}

/** One required checkbox, accepting an attestation. */
function Statement({ attestation, form, label }: StatementProps) {
  const { ref, name, onChange, onBlur } = form.register(attestation.code, {
    required: true,
  });
  return (
    <Checkbox
      id={`statement-${attestation.code}`}
      label={label ?? attestation.text}
      inputRef={ref}
      name={name}
      onChange={onChange}
      onBlur={onBlur}
    />
  );
}

interface StatementsFormProps {
  application: Application;
  attestations: Attestation[];
  stateName: string;
  onChanged: () => void;
}

/** Step 2 of the application (B6, or B6r to resubmit): each statement, the background check, and the sworn statement. */
function StatementsForm({
  application,
  attestations,
  stateName,
  onChanged,
}: StatementsFormProps) {
  const { t } = useTranslation("application");
  const router = useRouter();
  const form = useForm<Values>({
    defaultValues: Object.fromEntries(
      attestations.map((a) => [a.code, accepted(application, a)]),
    ),
  });
  const [error, setError] = useState<ErrorKey | null>(null);
  const statements = attestations.filter(
    (a) => a.code !== BACKGROUND_CHECK && a.code !== SWORN,
  );
  const backgroundCheck = attestations.find((a) => a.code === BACKGROUND_CHECK);
  const sworn = attestations.find((a) => a.code === SWORN);
  const resubmitting = application.status === "info_requested";

  async function submit(values: Values) {
    setError(null);
    try {
      await Promise.all(
        attestations
          .filter((attestation) => !accepted(application, attestation))
          .map((attestation) =>
            acceptAttestation(
              application.id,
              attestation.code,
              attestation.version,
            ),
          ),
      );
      const uploads = resubmitting ? await loadUnattached() : [];
      await submitApplication(
        application.id,
        String(values.swornName),
        uploads.map((d) => d.id),
      );
      router.push("/application/received");
    } catch (e) {
      const code = e instanceof ApplicationError ? e.code : null;
      if (code === "ATTESTATIONS_OUT_OF_DATE") {
        setError("statementsChanged");
        onChanged();
      } else {
        setError(code === "STATE_NOT_LIVE" ? "stateNotLive" : "save");
      }
    }
  }

  return (
    <FormProvider {...form}>
      <Form onSubmit={form.handleSubmit(submit)} large>
        <PageHeading title={t("statements.title")} />
        {resubmitting && <p>{t("statements.resubmitIntro")}</p>}
        {error && (
          <AlertBanner type="error" heading={t("errors.heading")}>
            {t(`errors.${error}`)}
          </AlertBanner>
        )}
        <p className="text-base">{t("required")}</p>
        <h2>{t("statements.heading")}</h2>
        {statements.map((attestation) => (
          <Statement
            key={attestation.code}
            attestation={attestation}
            form={form}
          />
        ))}
        {backgroundCheck && (
          <>
            <h2>{t("statements.backgroundHeading")}</h2>
            <p className="usa-intro">
              {t("statements.backgroundCheck", { state: stateName })}
            </p>
            <Statement
              attestation={backgroundCheck}
              form={form}
              label={t("statements.understand")}
            />
          </>
        )}
        {sworn && (
          <>
            <h2>{t("statements.swornHeading")}</h2>
            <Statement attestation={sworn} form={form} />
          </>
        )}
        <TextField id="swornName" label={t("statements.swornName")} />
        <div className="margin-top-4 display-flex flex-align-center">
          <Button type="submit">
            {t(resubmitting ? "statements.resubmit" : "statements.submit")}
          </Button>
          <Link href="/application" className="usa-link margin-left-3">
            {t("statements.back")}
          </Link>
        </div>
      </Form>
    </FormProvider>
  );
}

interface Loaded {
  application: Application;
  attestations: Attestation[];
  stateName: string;
}

function StatementsPage() {
  const { t } = useTranslation("application");
  const router = useRouter();
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [version, setVersion] = useState(0);
  const [failed, setFailed] = useState(false);

  const load = useCallback(
    () => Promise.all([loadApplications(), loadAttestations(), loadStates()]),
    [],
  );

  useEffect(() => {
    let current = true;
    load()
      .then(([applications, attestations, states]) => {
        const application = openApplication(applications);
        if (!application) {
          router.replace("/application");
          return;
        }
        const state = states.find((s) => s.code === application.sql_state_code);
        const stateName = state?.name ?? application.sql_state_code;
        if (current) setLoaded({ application, attestations, stateName });
      })
      .catch(() => {
        if (current) setFailed(true);
      });
    return () => {
      current = false;
    };
  }, [load, router, version]);

  return (
    <div className="usa-section">
      <div className="grid-container">
        <div className="grid-row">
          <div className="grid-col-12 desktop:grid-col-8">
            <StepIndicator
              steps={[t("steps.license"), t("steps.statements")]}
              current={1}
            />
            {failed && (
              <AlertBanner type="error" heading={t("errors.heading")}>
                {t("errors.load")}
              </AlertBanner>
            )}
            {loaded && (
              <StatementsForm
                key={version}
                application={loaded.application}
                attestations={loaded.attestations}
                stateName={loaded.stateName}
                onChanged={() => setVersion((v) => v + 1)}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** The second step of the participation application: statements and submit. */
export default function Page() {
  return (
    <ProtectedRoute>
      <StatementsPage />
    </ProtectedRoute>
  );
}
