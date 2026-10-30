import { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, type HeadingLevel } from "@trussworks/react-uswds";

import RecordCard from "src/components/RecordCard";
import StatusTag from "src/components/StatusTag";
import { formatDate } from "src/lib/dates";
import type { StatusByKind, StatusView } from "src/lib/status";

export interface PrivilegeCardProps {
  state: string;
  number: string;
  status: StatusByKind["privilege"];
  /** ISO dates. */
  activeFrom: string;
  expires: string;
  /** Staff see the computed status; defaults to the public pill. */
  view?: StatusView;
  discipline?: string;
  detailsHref?: string;
  actions?: ReactNode;
  headingLevel?: HeadingLevel;
}

/**
 * A compact privilege, after CompactConnect's PrivilegeCard (crosswalk §3.3).
 * The status's FLOW-06 qualifier follows its tag; a past expiry is red.
 */
export default function PrivilegeCard({
  state,
  number,
  status,
  activeFrom,
  expires,
  view,
  discipline,
  detailsHref,
  actions,
  headingLevel = "h3",
}: PrivilegeCardProps) {
  const { t } = useTranslation(["common", "status"]);
  const qualifier =
    status === "encumbered" ? null : (
      <span
        className={`margin-left-1 ${status === "expired" ? "text-error-dark" : ""}`}
      >
        {t(`status:privilegeQualifier.${status}`, {
          date: formatDate(expires),
        })}
      </span>
    );
  return (
    <RecordCard
      heading={state}
      headingLevel={headingLevel}
      status={
        <>
          <StatusTag kind="privilege" status={status} view={view} />
          {qualifier}
        </>
      }
      fields={[
        [t("card.activeFrom"), formatDate(activeFrom)],
        [t("card.privilegeNumber"), number],
        [t("card.discipline"), discipline],
      ]}
      actions={actions}
      footer={
        detailsHref && (
          <Link
            href={detailsHref}
            aria-label={`${t("card.viewDetails")} ${t("card.about", { record: state })}`}
          >
            {t("card.viewDetails")}
          </Link>
        )
      }
    />
  );
}
