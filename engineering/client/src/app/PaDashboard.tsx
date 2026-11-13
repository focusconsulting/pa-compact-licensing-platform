"use client";

import {
  CardGroup,
  ModalRef,
  ModalToggleButton,
} from "@trussworks/react-uswds";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import AlertBanner from "src/components/AlertBanner";
import ConfirmModal from "src/components/ConfirmModal";
import DataTable from "src/components/DataTable";
import PageHeading from "src/components/PageHeading";
import PrivilegeCard from "src/components/PrivilegeCard";
import StatusTag from "src/components/StatusTag";
import {
  Dashboard,
  State,
  loadDashboard,
  loadStates,
  withdrawApplication,
} from "src/lib/application";
import { formatDate } from "src/lib/dates";

type Summary = Dashboard["applications"][number];
type Step = Summary["timeline"][number];
type License = NonNullable<Dashboard["qualifying_license"]>;

/** Withdraw, after the PA confirms in a modal (B-n3a). */
function WithdrawButton({
  state,
  onWithdraw,
}: {
  state: string;
  onWithdraw: () => Promise<void>;
}) {
  const { t } = useTranslation("application");
  const modalRef = useRef<ModalRef>(null);
  return (
    <>
      <ModalToggleButton modalRef={modalRef} opener outline>
        {t("dashboard.withdraw")}
      </ModalToggleButton>
      <ConfirmModal
        id="withdraw-application"
        modalRef={modalRef}
        heading={t("dashboard.withdrawHeading")}
        confirmLabel={t("dashboard.withdrawConfirm")}
        cancelLabel={t("dashboard.withdrawCancel")}
        onConfirm={() => {
          void onWithdraw();
        }}
      >
        {t("dashboard.withdrawBody", { state })}
      </ConfirmModal>
    </>
  );
}

interface HistoryProps {
  applications: Summary[];
  stateName: (code: string) => string;
}

/** Every step of every application the PA has sent, newest first (B-n1h). */
function History({ applications, stateName }: HistoryProps) {
  const { t } = useTranslation("application");
  const rows = applications
    .flatMap((application) =>
      application.timeline.map((step, index) => ({
        step,
        state: stateName(application.sql_state_code),
        key: `${application.id}-${index}`,
      })),
    )
    .sort((a, b) => b.step.at.localeCompare(a.step.at));
  if (rows.length === 0) return null;
  return (
    <>
      <h2>{t("dashboard.historyHeading")}</h2>
      <DataTable
        caption={t("dashboard.historyHeading")}
        rows={rows}
        rowKey={(row) => row.key}
        columns={[
          {
            key: "date",
            header: t("dashboard.historyDate"),
            cell: (row) => formatDate(row.step.at),
          },
          {
            key: "what",
            header: t("dashboard.historyWhat"),
            cell: (row) =>
              t(`dashboard.history.${row.step.kind}`, { state: row.state }),
          },
        ]}
      />
    </>
  );
}

interface ApplicationProps {
  application: Summary;
  state: string;
  onWithdraw: () => Promise<void>;
}

/** What the state asked for, and by when to resubmit (B-n4). */
function InfoRequested({ application, state, onWithdraw }: ApplicationProps) {
  const { t } = useTranslation("application");
  const asked = application.timeline.findLast(
    (step) => step.kind === "info_requested",
  ) as Step;
  return (
    <>
      <p>
        <StatusTag kind="application" status="info_requested" />{" "}
        {t("dashboard.askedOn", {
          state,
          date: formatDate(asked.at),
        })}
      </p>
      <p>
        {t("dashboard.resubmitBy", {
          state,
          date: formatDate(String(application.resubmit_by)),
        })}
      </p>
      <div className="bg-base-lightest border-1px border-base-lighter radius-md padding-2 margin-bottom-3">
        <h3 className="margin-top-0">
          {t("dashboard.noteHeading", { state })}
        </h3>
        <p className="margin-bottom-0">{asked.note}</p>
      </div>
      <Link href="/application" className="usa-button">
        {t("dashboard.update")}
      </Link>
      <div className="margin-top-2">
        <WithdrawButton state={state} onWithdraw={onWithdraw} />
      </div>
    </>
  );
}

/** The PA's application to join (B-n1 under review, B-n3b withdrawn, B-n2 not eligible, B-n4 information requested). */
function ApplicationSection({
  application,
  state,
  onWithdraw,
}: ApplicationProps) {
  const { t } = useTranslation("application");
  const date = (value?: string | null) => formatDate(String(value));
  const heading = (
    <>
      <h2>{t("dashboard.applicationHeading")}</h2>
      <p>
        {t("dashboard.stateLicense", {
          state,
          license: application.claimed_license_number,
        })}
      </p>
    </>
  );
  if (application.status === "info_requested") {
    return (
      <>
        {heading}
        <InfoRequested
          application={application}
          state={state}
          onWithdraw={onWithdraw}
        />
      </>
    );
  }
  let when: string;
  if (application.status === "submitted") {
    when = t("dashboard.sent", { state, date: date(application.opened_at) });
  } else if (application.status === "withdrawn") {
    when = t("dashboard.withdrawnOn", { date: date(application.withdrawn_at) });
  } else {
    when = t("dashboard.decidedOn", {
      state,
      date: date(application.decided_at),
    });
  }

  return (
    <>
      {heading}
      <p>
        <StatusTag kind="application" status={application.status} /> {when}
      </p>
      {application.status === "submitted" && (
        <>
          <p>{t("dashboard.reviewChecks", { state })}</p>
          <p>{t("dashboard.reviewEmail", { state })}</p>
          <WithdrawButton state={state} onWithdraw={onWithdraw} />
        </>
      )}
      {application.status === "withdrawn" && (
        <p>{t("dashboard.withdrawnText", { state })}</p>
      )}
      {application.status === "denied" && (
        <>
          <p>{t("dashboard.deniedAppeal", { state })}</p>
          <p>{t("dashboard.deniedAgain", { state })}</p>
        </>
      )}
    </>
  );
}

interface EligibleProps {
  dashboard: Dashboard;
  stateName: (code: string) => string;
}

/** An eligible PA (C8): their qualifying license and their privileges. */
function EligibleSection({ dashboard, stateName }: EligibleProps) {
  const { t } = useTranslation(["application", "status"]);
  const license = dashboard.qualifying_license as License;
  const state = stateName(license.state_code);

  return (
    <>
      <h2>{t("dashboard.licenseHeading")}</h2>
      <p>
        {t("dashboard.licenseLine", {
          state,
          license: license.license_number,
          status: t(
            `status:license.${license.status}` as "status:license.active",
          ),
          date: formatDate(String(license.expires_on)),
        })}
      </p>
      <p>
        <StatusTag kind="application" status="eligible" />{" "}
        {t("dashboard.verified", {
          state: stateName(String(license.verified_by_state)),
          date: formatDate(String(license.verified_at)),
        })}
      </p>
      <h2>{t("dashboard.privilegesHeading")}</h2>
      {dashboard.privileges.length === 0 ? (
        <p>{t("dashboard.noPrivileges")}</p>
      ) : (
        <CardGroup>
          {dashboard.privileges.map((privilege) => (
            <PrivilegeCard
              key={privilege.id}
              state={stateName(privilege.remote_state_code)}
              number={privilege.privilege_number}
              status={privilege.status as "active"}
              activeFrom={privilege.issued_at}
              expires={privilege.expires_on}
              headingLevel="h3"
            />
          ))}
        </CardGroup>
      )}
      {dashboard.primary_action.available && (
        <Link href="/privileges" className="usa-button">
          {t("dashboard.applyPrivileges")}
        </Link>
      )}
    </>
  );
}

/** The signed-in PA's dashboard, read from the API on each visit. */
export default function PaDashboard() {
  const { t } = useTranslation("application");
  const router = useRouter();
  const [loaded, setLoaded] = useState<{
    dashboard: Dashboard;
    states: State[];
  } | null>(null);
  const [version, setVersion] = useState(0);
  const [failed, setFailed] = useState(false);
  const [withdrew, setWithdrew] = useState(false);
  const [withdrawFailed, setWithdrawFailed] = useState(false);

  useEffect(() => {
    let current = true;
    Promise.all([loadDashboard(), loadStates()])
      .then(([dashboard, states]) => {
        if (current) setLoaded({ dashboard, states });
      })
      .catch(() => {
        if (current) setFailed(true);
      });
    return () => {
      current = false;
    };
  }, [version]);

  const applications = loaded?.dashboard.applications ?? [];
  const eligible = applications.find((a) => a.status === "eligible");
  const shown = eligible ?? applications[0];
  const toWizard = loaded !== null && (!shown || shown.status === "draft");

  useEffect(() => {
    if (toWizard) router.replace("/application");
  }, [toWizard, router]);

  const stateName = (code: string) =>
    loaded?.states.find((s) => s.code === code)?.name ?? code;

  async function withdraw(id: string) {
    setWithdrawFailed(false);
    try {
      await withdrawApplication(id);
      setWithdrew(true);
      setVersion((v) => v + 1);
    } catch {
      setWithdrawFailed(true);
    }
  }

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
            {withdrawFailed && (
              <AlertBanner type="error" heading={t("errors.heading")}>
                {t("errors.withdraw")}
              </AlertBanner>
            )}
            {withdrew && shown?.status === "withdrawn" && (
              <AlertBanner
                type="success"
                heading={t("dashboard.withdrawnHeading")}
              >
                {t("dashboard.withdrawnAlert", {
                  date: formatDate(String(shown.withdrawn_at)),
                  state: stateName(shown.sql_state_code),
                })}
              </AlertBanner>
            )}
            {loaded && shown && !toWizard && (
              <>
                <PageHeading title={t("dashboard.title")} />
                {eligible ? (
                  <EligibleSection
                    dashboard={loaded.dashboard}
                    stateName={stateName}
                  />
                ) : (
                  <>
                    <ApplicationSection
                      application={shown}
                      state={stateName(shown.sql_state_code)}
                      onWithdraw={() => withdraw(shown.id)}
                    />
                    <History
                      applications={applications}
                      stateName={stateName}
                    />
                  </>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
