"use client";

import {
  ProcessList,
  ProcessListHeading,
  ProcessListItem,
} from "@trussworks/react-uswds";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AlertBanner from "src/components/AlertBanner";
import ProtectedRoute from "src/components/ProtectedRoute";
import { Application, loadApplications, loadStates } from "src/lib/application";
import { formatDate } from "src/lib/dates";

interface Received {
  application: Application;
  stateName: string;
}

/** After submitting (B9): the receipt, and what the state of qualifying license does next. */
function ReceivedPage() {
  const { t } = useTranslation("application");
  const router = useRouter();
  const [received, setReceived] = useState<Received | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let current = true;
    Promise.all([loadApplications(), loadStates()])
      .then(([applications, states]) => {
        const application = applications.find((a) => a.status === "submitted");
        if (!application) {
          router.replace("/application");
          return;
        }
        const state = states.find((s) => s.code === application.sql_state_code);
        if (current) {
          setReceived({
            application,
            stateName: state?.name ?? application.sql_state_code,
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

  const steps = ["next1", "next2", "next3", "next4"] as const;

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
            {received && (
              <>
                <AlertBanner
                  type="success"
                  heading={t("received.heading")}
                  headingLevel="h1"
                >
                  {t("received.applied", {
                    date: formatDate(String(received.application.opened_at)),
                    state: received.stateName,
                  })}
                </AlertBanner>
                <h2>{t("received.nextHeading")}</h2>
                <ProcessList>
                  {steps.map((step) => (
                    <ProcessListItem key={step}>
                      <ProcessListHeading
                        type="p"
                        className="font-sans-lg text-normal"
                      >
                        {t(`received.${step}`, { state: received.stateName })}
                      </ProcessListHeading>
                    </ProcessListItem>
                  ))}
                </ProcessList>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** The receipt a PA sees after submitting their participation application. */
export default function Page() {
  return (
    <ProtectedRoute>
      <ReceivedPage />
    </ProtectedRoute>
  );
}
