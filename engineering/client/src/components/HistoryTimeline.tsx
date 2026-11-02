import { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import DataTable from "src/components/DataTable";
import { formatDate } from "src/lib/dates";

export interface HistoryEvent {
  id: string;
  /** When it happened: an ISO date or timestamp. */
  on: string;
  what: ReactNode;
  by: ReactNode;
}

export interface HistoryTimelineProps {
  events: HistoryEvent[];
  /** The table's name for screen readers; the section heading shows it on screen. */
  caption?: string;
}

/**
 * What happened to a record, newest first, as C6b draws it. The one history for
 * applications, privileges, and the staff record.
 */
export default function HistoryTimeline({
  events,
  caption,
}: HistoryTimelineProps) {
  const { t } = useTranslation("common");
  const newestFirst = [...events].sort(
    (a, b) => Date.parse(b.on) - Date.parse(a.on),
  );
  return (
    <DataTable
      caption={caption ?? t("history.heading")}
      rowKey={(event) => event.id}
      rows={newestFirst}
      columns={[
        {
          key: "on",
          header: t("history.date"),
          cell: (event) => formatDate(event.on),
        },
        { key: "what", header: t("history.what"), cell: (event) => event.what },
        { key: "by", header: t("history.by"), cell: (event) => event.by },
      ]}
    />
  );
}
