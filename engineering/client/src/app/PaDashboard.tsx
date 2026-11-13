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
type License = NonNullable<Dashboard["qualifying_license"]>;

/** Statuses the dashboard has no section for: the wizard shows them. */
const IN_WIZARD = new Set<Summary["status"]>(["draft", "info_requested"]);

interface ApplicationProps {
  application: Summary;
  state: string;
  onWithdraw: () => Promise<void>;
}

/** The PA's application to join (B-n1 under review, B-n3b withdrawn, B-n2 not eligible). */
function ApplicationSection({
  application,
  state,
  onWithdraw,
}: ApplicationProps) {
  const { t } = useTranslation("application");
  const modalRef = useRef<ModalRef>(null);
  const date = (value?: string | null) => formatDate(String(value));
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
      <h2>{t("dashboard.applicationHeading")}</h2>
      <p>
        {t("dashboard.stateLicense", {
          state,
          license: application.claimed_license_number,
        })}
      </p>
      <p>
        <StatusTag kind="application" status={application.status} /> {when}
      </p>
      {application.status === "submitted" && (
        <>
          <p>{t("dashboard.reviewChecks", { state })}</p>
          <p>{t("dashboard.reviewEmail", { state })}</p>
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
  const toWizard = loaded !== null && (!shown || IN_WIZARD.has(shown.status));

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
                  <ApplicationSection
                    application={shown}
                    state={stateName(shown.sql_state_code)}
                    onWithdraw={() => withdraw(shown.id)}
                  />
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
