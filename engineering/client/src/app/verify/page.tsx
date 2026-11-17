"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AlertBanner from "src/components/AlertBanner";
import PageHeading from "src/components/PageHeading";
import VerifyResults from "src/components/VerifyResults";
import VerifySearchForm from "src/components/VerifySearchForm";
import {
  VerificationError,
  pageFrom,
  searchFrom,
  searchHolders,
  searchQuery,
} from "src/lib/verification";

type Found = Awaited<ReturnType<typeof searchHolders>>;

/** What the search in one address came to; `query` ties it to that address. */
type Outcome = { query: string } & (
  { found: Found } | { problem: "limited" | "load" }
);

/**
 * The search and, under it, its results (V1, V2). The search lives in the
 * address, so results survive a reload and Back from a PA's page.
 */
function Verify() {
  const { t } = useTranslation("verify");
  const router = useRouter();
  const params = useSearchParams();
  const query = params.toString();
  const [outcome, setOutcome] = useState<Outcome | null>(null);

  useEffect(() => {
    const asked = new URLSearchParams(query);
    const search = searchFrom(asked);
    if (!search) return undefined;
    let current = true;
    searchHolders(search, pageFrom(asked))
      .then((found) => {
        if (current) setOutcome({ query, found });
      })
      .catch((e: unknown) => {
        const limited = e instanceof VerificationError && e.status === 429;
        if (current)
          setOutcome({ query, problem: limited ? "limited" : "load" });
      });
    return () => {
      current = false;
    };
  }, [query]);

  const search = searchFrom(params);
  // An outcome for an earlier address is not this search's answer.
  const shown = outcome?.query === query ? outcome : null;

  return (
    <div className="usa-section">
      <div className="grid-container">
        <div className="grid-row">
          <div className="grid-col-12 desktop:grid-col-8">
            {shown && "problem" in shown && shown.problem === "limited" && (
              <AlertBanner type="warning" heading={t("errors.limitedHeading")}>
                {t("errors.limited")}
              </AlertBanner>
            )}
            {shown && "problem" in shown && shown.problem === "load" && (
              <AlertBanner type="error" heading={t("errors.heading")}>
                {t("errors.load")}
              </AlertBanner>
            )}
            <PageHeading title={t("title")} intro={t("intro")} />
            <VerifySearchForm
              key={query}
              search={search}
              onSearch={(next) => router.push(`/verify?${searchQuery(next)}`)}
            />
            {search && shown && "found" in shown && (
              <VerifyResults
                search={search}
                holders={shown.found.data}
                page={shown.found.page}
                onPage={(page) =>
                  router.push(`/verify?${searchQuery(search, page)}`)
                }
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Public verification: anyone looks up a PA's compact privileges, with no account (FLOW-08). */
export default function Page() {
  // A static export needs the boundary around anything that reads the address's query.
  return (
    <Suspense>
      <Verify />
    </Suspense>
  );
}
