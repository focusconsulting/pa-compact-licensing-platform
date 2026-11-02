import { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import type { HeadingLevel } from "@trussworks/react-uswds";

import RecordCard from "src/components/RecordCard";
import StatusTag from "src/components/StatusTag";
import { formatDate } from "src/lib/dates";
import type { StatusByKind, StatusView } from "src/lib/status";

export interface LicenseCardProps {
  state: string;
  number: string;
  status: StatusByKind["license"];
  /** ISO date. */
  expires: string;
  /** Staff see the computed status; defaults to the public pill. */
  view?: StatusView;
  discipline?: string;
  /** The free-text status line the state can write. */
  note?: string;
  actions?: ReactNode;
  headingLevel?: HeadingLevel;
}

/** A qualifying license, after CompactConnect's LicenseCard (crosswalk §4.3). */
export default function LicenseCard({
  state,
  number,
  status,
  expires,
  view,
  discipline,
  note,
  actions,
  headingLevel = "h3",
}: LicenseCardProps) {
  const { t } = useTranslation("common");
  return (
    <RecordCard
      heading={state}
      headingLevel={headingLevel}
      status={<StatusTag kind="license" status={status} view={view} />}
      fields={[
        [t("card.licenseNumber"), number],
        [t("card.expires"), formatDate(expires)],
        [t("card.discipline"), discipline],
      ]}
      note={note}
      actions={actions}
    />
  );
}
