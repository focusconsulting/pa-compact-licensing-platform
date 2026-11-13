"use client";

import {
  Button,
  Fieldset,
  Form,
  Label,
  ProcessList,
  ProcessListHeading,
  ProcessListItem,
  Textarea,
} from "@trussworks/react-uswds";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FormProvider, useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";

import AlertBanner from "src/components/AlertBanner";
import { DateFields } from "src/components/DateFields";
import {
  FilePickerField,
  UploadedDocument,
} from "src/components/FilePickerField";
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
  loadUnattached,
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
  responseNote: string;
  document?: UploadedDocument;
}

type ErrorKey = "load" | "save" | "stateNotLive" | "otherNameLastName";

interface Loaded {
  application?: Application;
  profile: Profile;
  states: State[];
  /** While the state waits on information: the upload the PA already chose, if any. */
  upload?: UploadedDocument;
}

const blankToNull = (value: string) => value.trim() || null;

function defaults({ application, profile, upload }: Loaded): StartValues {
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
    responseNote: application?.response_note ?? "",
    document: upload,
  };
}

/** A detail shown, not editable: the NCCPA number the state verified, or the state of an application it has. */
function Fixed({ label, value }: { label: string; value: string }) {
  return (
    <div className="margin-top-3">
      <p className="text-bold margin-bottom-05">{label}</p>
      <p className="margin-top-0">{value}</p>
    </div>
  );
}

/** What the state asked for, when, and by when to resubmit (B14). */
function Request({
  application,
  state,
}: {
  application: Application;
  state: string;
}) {
  const { t } = useTranslation("application");
  return (
    <AlertBanner type="info" heading={t("update.alertHeading", { state })}>
      <span className="display-block">{application.request_note}</span>
      <span className="display-block margin-top-2">
        {t("update.askedOn", {
          asked: formatDate(String(application.requested_at)),
          due: formatDate(String(application.resubmit_by)),
        })}
      </span>
    </AlertBanner>
  );
}

/** Step 1 of the application: B2 for a draft, B14 when the state asked for more. */
function LicenseAndDetails({ loaded }: { loaded: Loaded }) {
  const { t } = useTranslation(["application", "address", "basic", "common"]);
  const router = useRouter();
  const form = useForm<StartValues>({ defaultValues: defaults(loaded) });
  const [error, setError] = useState<ErrorKey | null>(null);
  const { application, profile, states } = loaded;
  const live = states.filter((s) => s.is_live);
  const draft = !application || application.status === "draft";
  const asked = application?.status === "info_requested";
  const fixed = new Set(profile.verified_fields);
  const reply = form.register("responseNote");
  const state =
    states.find((s) => s.code === application?.sql_state_code)?.name ??
    String(application?.sql_state_code);

  async function save(values: StartValues) {
    setError(null);
    const other = {
      first_name: blankToNull(values.otherFirstName),
      middle_name: blankToNull(values.otherMiddleName),
      last_name: blankToNull(values.otherLastName),
    };
    if (!other.last_name && (other.first_name || other.middle_name)) {
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
        date_of_birth: values.dateOfBirth,
        ...(fixed.has("nccpa_certification_number")
          ? {}
          : { nccpa_certification_number: values.nccpa }),
        other_names: [
          ...(other.last_name
            ? [{ ...other, last_name: other.last_name }]
            : []),
          ...profile.other_names.slice(1),
        ],
      });
      const current =
        application ?? (await startApplication(values.sqlStateCode as string));
      const moved = draft && current.sql_state_code !== values.sqlStateCode;
      await saveApplication(current.id, {
        claimed_license_number: values.licenseNumber,
        claimed_license_expires_on: values.licenseExpires,
        ...(moved ? { sql_state_code: values.sqlStateCode } : {}),
        ...(asked ? { response_note: values.responseNote } : {}),
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
        {asked ? (
          <>
            <PageHeading title={t("update.title")} />
            <Request application={application} state={state} />
          </>
        ) : (
          <PageHeading title={t("start.title")} intro={t("start.intro")} />
        )}
        {error && (
          <AlertBanner type="error" heading={t("errors.heading")}>
            {t(`errors.${error}`)}
          </AlertBanner>
        )}
        <p className="text-base">{t("required")}</p>
        {asked && (
          <>
            <Label htmlFor="responseNote" hint={t("common:optionalText")}>
              {t("update.reply", { state })}
            </Label>
            <div className="usa-hint" id="responseNoteHint">
              {t("update.replyHint", { state })}
            </div>
            <Textarea
              id="responseNote"
              aria-describedby="responseNoteHint"
              maxLength={4000}
              inputRef={reply.ref}
              name={reply.name}
              onChange={reply.onChange}
              onBlur={reply.onBlur}
            />
            <FilePickerField
              id="document"
              label={t("update.upload")}
              kind="information_response"
              hint={t("update.uploadHint", { state })}
              optional
            />
          </>
        )}
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
        <h2>{t("start.sqlHeading")}</h2>
        {draft ? (
          <SelectField
            id="sqlStateCode"
            label={t("start.state")}
            hint={t("start.stateHint")}
            options={live.map((s) => [s.code, s.name])}
            required
          />
        ) : (
          <>
            <p>{state}</p>
            <p>{t("update.anotherState")}</p>
          </>
        )}
        <h2>{t("start.licenseHeading")}</h2>
        <TextField id="licenseNumber" label={t("start.licenseNumber")} />
        <Fieldset legend={t("start.licenseExpires")}>
          <DateFields id="licenseExpires" name="" />
        </Fieldset>
        <Fieldset legend={t("start.dateOfBirth")}>
          <DateFields id="dateOfBirth" name="" />
        </Fieldset>
        <h2>{t("start.detailsHeading")}</h2>
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
      .then(async ([applications, profile, states]) => {
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
        const [upload] =
          application?.status === "info_requested"
            ? await loadUnattached()
            : [];
        if (current) {
          setLoaded({
            application,
            profile,
            states,
            upload: upload && { id: upload.id, fileName: upload.file_name },
          });
        }
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
