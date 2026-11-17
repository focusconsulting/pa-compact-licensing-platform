import { Pagination } from "@trussworks/react-uswds";
import type { TFunction } from "i18next";
import Link from "next/link";
import { useTranslation } from "react-i18next";

import DataTable, { type Column } from "src/components/DataTable";
import EmptyState from "src/components/EmptyState";
import {
  fullName,
  searchQuery,
  type HolderSummary,
  type ResultsPage,
  type Search,
} from "src/lib/verification";

type Translate = TFunction<"verify">;

/** Each PA's link carries the search, so their page can lead back to these results. */
function columnsFor(t: Translate, back: string): Column<HolderSummary>[] {
  return [
    {
      key: "name",
      header: t("results.name"),
      cell: (holder) => (
        <Link
          className="usa-link"
          href={`/verify/practitioner?id=${holder.id}&${back}`}
        >
          {fullName(holder)}
        </Link>
      ),
    },
    {
      key: "license",
      header: t("results.license"),
      cell: (holder) => holder.state_of_qualifying_license.name,
    },
    {
      key: "privileges",
      header: t("results.privileges"),
      cell: (holder) =>
        holder.privilege_states.map((state) => state.name).join(", "),
    },
  ];
}

export interface VerifyResultsProps {
  search: Search;
  holders: HolderSummary[];
  page: ResultsPage;
  onPage: (page: number) => void;
}

/**
 * The PAs a public search found (V2), each linked to their page, or what the
 * search needs when it found no one (V2e).
 */
export default function VerifyResults({
  search,
  holders,
  page,
  onPage,
}: VerifyResultsProps) {
  const { t } = useTranslation("verify");
  const pages = Math.ceil(page.total / page.size);

  return (
    <>
      <h2 className="margin-top-4">
        {t("results.heading", { count: page.total })}
      </h2>
      {holders.length === 0 ? (
        <EmptyState>
          {"privilege_number" in search
            ? t("results.noneByNumber", { number: search.privilege_number })
            : t("results.noneByName", {
                name: `${search.first_name} ${search.last_name}`,
              })}
        </EmptyState>
      ) : (
        <DataTable
          caption={t("results.caption")}
          columns={columnsFor(t, searchQuery(search, page.number))}
          rows={holders}
          rowKey={(holder) => holder.id}
        />
      )}
      {pages > 1 && (
        <Pagination
          aria-label={t("results.pages")}
          pathname="/verify"
          currentPage={page.number}
          totalPages={pages}
          onClickNext={() => onPage(page.number + 1)}
          onClickPrevious={() => onPage(page.number - 1)}
          onClickPageNumber={(_, number) => onPage(number)}
        />
      )}
    </>
  );
}
