"use client";

import {
  Button,
  Fieldset,
  Form,
  ProcessList,
  ProcessListHeading,
  ProcessListItem,
} from "@trussworks/react-uswds";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import AlertBanner from "src/components/AlertBanner";
import { DateFields } from "src/components/DateFields";
import PageHeading from "src/components/PageHeading";
import ProtectedRoute from "src/components/ProtectedRoute";
import { SelectField } from "src/components/SelectField";
import StepIndicator from "src/components/StepIndicator";
import { TextField } from "src/components/TextField";
import {
  Application,
  ApplicationError,
  Profile,
  State,
  loadApplications,
  loadProfile,
  loadStates,
  openApplication,
  saveApplication,
  saveProfile,
  startApplication,
} from "src/lib/application";
import { formatDate } from "src/lib/dates";

interface StartValues {
  residenceLine1: string;
  residenceLine2: string;
  residenceCity: string;
  residenceRegion: string | null;
  residenceZip: string;
  sqlStateCode: string | null;
  licenseNumber: string;
  licenseExpires: string | null;
  dateOfBirth: string | null;
  otherFirstName: string;
  otherMiddleName: string;
  otherLastName: string;
  nccpa: string;
}

type ErrorKey = "load" | "save" | "stateNotLive" | "otherNameLastName";

interface Loaded {
  application?: Application;
  profile: Profile;
  states: State[];
}

const blankToNull = (value: string) => value.trim() || null;

function defaults({ application, profile }: Loaded): StartValues {
  const [other] = profile.other_names;
  return {
    residenceLine1: profile.residence?.line1 ?? "",
    residenceLine2: profile.residence?.line2 ?? "",
    residenceCity: profile.residence?.city ?? "",
    residenceRegion: profile.residence?.region ?? null,
    residenceZip: profile.residence?.postal_code ?? "",
    sqlStateCode: application?.sql_state_code ?? null,
    licenseNumber: application?.claimed_license_number ?? "",
    licenseExpires: application?.claimed_license_expires_on ?? null,
    dateOfBirth: profile.date_of_birth ?? null,
    otherFirstName: other?.first_name ?? "",
    otherMiddleName: other?.middle_name ?? "",
    otherLastName: other?.last_name ?? "",
    nccpa: profile.nccpa_certification_number ?? "",
  };
}

/** A detail the state verified: shown, not editable (PR1). */
function Fixed({ label, value }: { label: string; value: string }) {
  return (
    <div className="margin-top-3">
      <p className="text-bold margin-bottom-05">{label}</p>
      <p className="margin-top-0">{value}</p>
    </div>
  );
}

/** Step 1 of the application (B2): where the PA lives, their state of qualifying license, their license, and details. */
function LicenseAndDetails({ loaded }: { loaded: Loaded }) {
  const { t } = useTranslation(["application", "address", "basic", "status"]);
  const router = useRouter();
  const form = useForm<StartValues>({ defaultValues: defaults(loaded) });
  const [error, setError] = useState<ErrorKey | null>(null);
  const { application, profile, states } = loaded;
  const live = states.filter((s) => s.is_live);
  const draft = !application || application.status === "draft";
  const fixed = new Set(profile.verified_fields);

  async function save(values: StartValues) {
    setError(null);
    const other = {
      first_name: blankToNull(values.otherFirstName),
      middle_name: blankToNull(values.otherMiddleName),
      last_name: blankToNull(values.otherLastName),
    };
    if (
      !fixed.has("other_names") &&
      !other.last_name &&
      (other.first_name || other.middle_name)
    ) {
      setError("otherNameLastName");
      return;
    }
    try {
      await saveProfile({
        residence: {
          line1: values.residenceLine1,
          line2: blankToNull(values.residenceLine2),
          city: values.residenceCity,
          region: values.residenceRegion,
          postal_code: values.residenceZip,
          country_code: "US",
        },
        ...(fixed.has("date_of_birth")
          ? {}
          : { date_of_birth: values.dateOfBirth }),
        ...(fixed.has("nccpa_certification_number")
          ? {}
          : { nccpa_certification_number: values.nccpa }),
        ...(fixed.has("other_names")
          ? {}
          : {
              other_names: [
                ...(other.last_name
                  ? [{ ...other, last_name: other.last_name }]
                  : []),
                ...profile.other_names.slice(1),
              ],
            }),
      });
      const current =
        application ?? (await startApplication(values.sqlStateCode as string));
      const moved = draft && current.sql_state_code !== values.sqlStateCode;
      await saveApplication(current.id, {
        claimed_license_number: values.licenseNumber,
        claimed_license_expires_on: values.licenseExpires,
        ...(moved ? { sql_state_code: values.sqlStateCode } : {}),
      });
      router.push("/application/statements");
    } catch (e) {
      const notLive =
        e instanceof ApplicationError && e.code === "STATE_NOT_LIVE";
      setError(notLive ? "stateNotLive" : "save");
    }
  }

  return (
    <FormProvider {...form}>
      <Form onSubmit={form.handleSubmit(save)} large>
        <PageHeading title={t("start.title")} intro={t("start.intro")} />
        {application?.status === "info_requested" && (
          <AlertBanner
            type="warning"
            heading={t("status:application.info_requested")}
          >
            {application.request_note}
          </AlertBanner>
        )}
        {error && (
          <AlertBanner type="error" heading={t("errors.heading")}>
            {t(`errors.${error}`)}
          </AlertBanner>
        )}
        <p className="text-base">{t("required")}</p>
        <Fieldset legend={t("start.residence")} className="legend-lg">
          <span className="usa-hint">{t("start.residenceHint")}</span>
          <TextField
            id="residenceLine1"
            label={t("address:fields.address.address1Title")}
          />
          <TextField
            id="residenceLine2"
            label={t("address:fields.address.address2Title")}
            optional
          />
          <TextField
            id="residenceCity"
            label={t("address:fields.address.cityTitle")}
          />
          <SelectField
            id="residenceRegion"
            label={t("address:fields.address.stateTitle")}
            options={states.map((s) => [s.code, s.name])}
            required
          />
          <TextField
            id="residenceZip"
            label={t("address:fields.address.zipTitle")}
          />
        </Fieldset>
        {draft && (
          <>
            <h2>{t("start.sqlHeading")}</h2>
            <SelectField
              id="sqlStateCode"
              label={t("start.state")}
              hint={t("start.stateHint")}
              options={live.map((s) => [s.code, s.name])}
              required
            />
          </>
        )}
        <h2>{t("start.licenseHeading")}</h2>
        <TextField id="licenseNumber" label={t("start.licenseNumber")} />
        <Fieldset legend={t("start.licenseExpires")}>
          <DateFields id="licenseExpires" name="" />
        </Fieldset>
        {fixed.has("date_of_birth") ? (
          <Fixed
            label={t("start.dateOfBirth")}
            value={formatDate(String(profile.date_of_birth))}
          />
        ) : (
          <Fieldset legend={t("start.dateOfBirth")}>
            <DateFields id="dateOfBirth" name="" />
          </Fieldset>
        )}
        <h2>{t("start.detailsHeading")}</h2>
        {fixed.has("other_names") ? (
          profile.other_names.length > 0 && (
            <Fixed
              label={t("start.otherNames")}
              value={profile.other_names
                .map((n) =>
                  [n.first_name, n.middle_name, n.last_name, n.name_suffix]
                    .filter(Boolean)
                    .join(" "),
                )
                .join(", ")}
            />
          )
        ) : (
          <Fieldset legend={t("start.otherNames")}>
            <TextField
              id="otherFirstName"
              label={t("basic:fields.name.firstNameTitle")}
              optional
            />
            <TextField
              id="otherMiddleName"
              label={t("basic:fields.name.middleNameTitle")}
              optional
            />
            <TextField
              id="otherLastName"
              label={t("basic:fields.name.lastNameTitle")}
              optional
            />
          </Fieldset>
        )}
        {fixed.has("nccpa_certification_number") ? (
          <Fixed
            label={t("start.nccpa")}
            value={String(profile.nccpa_certification_number)}
          />
        ) : (
          <TextField id="nccpa" label={t("start.nccpa")} />
        )}
        <Button type="submit" className="margin-top-4">
          {t("start.continue")}
        </Button>
      </Form>
    </FormProvider>
  );
}

/** Before step 1 (B1j): how joining works, and what to have ready. */
function Intro({ onStart }: { onStart: () => void }) {
  const { t } = useTranslation("application");
  const steps = ["step1", "step2", "step3", "step4"] as const;
  const ready = [
    "readyResidence",
    "readyLicense",
    "readyBirth",
    "readyNccpa",
  ] as const;
  return (
    <>
      <PageHeading title={t("intro.title")} />
      <h2>{t("intro.howHeading")}</h2>
      <ProcessList>
        {steps.map((step) => (
          <ProcessListItem key={step}>
            <ProcessListHeading type="p" className="font-sans-md text-normal">
              {t(`intro.${step}`)}
            </ProcessListHeading>
          </ProcessListItem>
        ))}
      </ProcessList>
      <p className="text-bold">{t("intro.haveReady")}</p>
      <ul className="usa-list">
        {ready.map((item) => (
          <li key={item}>{t(`intro.${item}`)}</li>
        ))}
      </ul>
      <Button type="button" onClick={onStart}>
        {t("intro.start")}
      </Button>
    </>
  );
}

function StartPage() {
  const { t } = useTranslation("application");
  const router = useRouter();
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [failed, setFailed] = useState(false);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    let current = true;
    Promise.all([loadApplications(), loadProfile(), loadStates()])
      .then(([applications, profile, states]) => {
        if (applications.some((a) => a.status === "eligible")) {
          router.replace("/");
          return;
        }
        const application = openApplication(applications);
        if (
          !application &&
          applications.some((a) => a.status === "submitted")
        ) {
          router.replace("/application/received");
          return;
        }
        if (current) setLoaded({ application, profile, states });
      })
      .catch(() => {
        if (current) setFailed(true);
      });
    return () => {
      current = false;
    };
  }, [router]);

  return (
    <div className="usa-section">
      <div className="grid-container">
        <div className="grid-row">
          <div className="grid-col-12 desktop:grid-col-8">
            {failed && (
              <AlertBanner type="error" heading={t("errors.heading")}>
                {t("errors.load")}
              </AlertBanner>
            )}
            {loaded && !loaded.application && !started && (
              <Intro onStart={() => setStarted(true)} />
            )}
            {loaded && (loaded.application || started) && (
              <>
                <StepIndicator
                  steps={[t("steps.license"), t("steps.statements")]}
                  current={0}
                />
                <LicenseAndDetails loaded={loaded} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** The first step of the participation application, for a signed-in PA. */
export default function Page() {
  return (
    <ProtectedRoute>
      <StartPage />
    </ProtectedRoute>
  );
}
