import { ReactNode, useId } from "react";
import { useTranslation } from "react-i18next";
import { Button, Tag } from "@trussworks/react-uswds";

import DataTable, { type Column } from "src/components/DataTable";
import EmptyState from "src/components/EmptyState";

export interface QueueListProps<T> {
  /** The group's name; its count follows it, as in C3's "Needs work (1)". */
  heading: string;
  /** The line under the heading, only where the wireframe draws one. */
  intro?: ReactNode;
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  /** When each record arrived (`YYYY-MM-DD`); adds the age column. */
  receivedOn?: (row: T) => string;
  /** Shown instead of the table when the group is empty. */
  empty: ReactNode;
  /** What the list is filtered by, shown as CompactConnect's "Viewing: … ×" chip. */
  filters?: string[];
  onClearFilters?: () => void;
}

const DAY = 24 * 60 * 60 * 1000;

/** Whole days from `date` to today, counted in calendar days. */
export function daysSince(date: string, today = new Date()): number {
  const from = Date.parse(`${date}T00:00:00Z`);
  const to = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.floor((to - from) / DAY);
}

/** One group of a work queue (C3): its heading and count, then its records or an empty state. */
export default function QueueList<T>({
  heading,
  intro,
  columns,
  rows,
  rowKey,
  receivedOn,
  empty,
  filters,
  onClearFilters,
}: QueueListProps<T>) {
  const { t } = useTranslation("common");
  const headingId = useId();
  const title = t("queue.heading", { heading, count: rows.length });
  const withAge: Column<T>[] = receivedOn
    ? [
        ...columns,
        {
          key: "age",
          header: t("queue.age"),
          cell: (row) => t("queue.days", { count: daysSince(receivedOn(row)) }),
        },
      ]
    : columns;

  return (
    <section aria-labelledby={headingId} className="margin-bottom-4">
      <h2 id={headingId}>{title}</h2>
      {intro && <p>{intro}</p>}
      {filters && filters.length > 0 && (
        <p className="display-flex flex-align-center">
          {t("queue.viewing")}
          <Tag className="margin-x-1">{filters.join(", ")}</Tag>
          <Button
            type="button"
            unstyled
            onClick={onClearFilters}
            aria-label={t("queue.clearFilters")}
          >
            ×
          </Button>
        </p>
      )}
      {rows.length > 0 ? (
        <DataTable
          columns={withAge}
          rows={rows}
          rowKey={rowKey}
          caption={title}
        />
      ) : (
        <EmptyState>{empty}</EmptyState>
      )}
    </section>
  );
}
