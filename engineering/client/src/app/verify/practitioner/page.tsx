"use client";

import { CardGroup } from "@trussworks/react-uswds";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import AlertBanner from "src/components/AlertBanner";
import PageHeading from "src/components/PageHeading";
import PrivilegeCard from "src/components/PrivilegeCard";
import {
  VerificationError,
  fullName,
  loadHolder,
  pageFrom,
  searchFrom,
  searchQuery,
  type Holder,
} from "src/lib/verification";

type Problem = "missing" | "limited" | "load";

/** The statuses that mean no such PA is listed: unknown, or not an id at all. */
const MISSING = new Set([404, 422]);

/** One PA's public record (V3, V3i): their name, state of qualifying license, and a card per privilege. */
function Practitioner() {
  const { t } = useTranslation("verify");
  const params = useSearchParams();
  const id = params.get("id");
  const [loaded, setLoaded] = useState<{
    id: string;
    holder?: Holder;
    problem?: Problem;
  } | null>(null);

  useEffect(() => {
    if (!id) return undefined;
    let current = true;
    loadHolder(id)
      .then((holder) => {
        if (current) setLoaded({ id, holder });
      })
      .catch((e: unknown) => {
        const status = e instanceof VerificationError ? e.status : 0;
        let problem: Problem = "load";
        if (status === 429) problem = "limited";
        if (MISSING.has(status)) problem = "missing";
        if (current) setLoaded({ id, problem });
      });
    return () => {
      current = false;
    };
  }, [id]);

  const search = searchFrom(params);
  const back = search ? (
    <Link
      className="usa-link"
      href={`/verify?${searchQuery(search, pageFrom(params))}`}
    >
      {t("holder.backToResults")}
    </Link>
  ) : (
    <Link className="usa-link" href="/verify">
      {t("holder.searchAgain")}
    </Link>
  );
  const shown = loaded?.id === id ? loaded : null;
  const problem = id ? shown?.problem : "missing";
  const holder = shown?.holder;

  return (
    <div className="usa-section">
      <div className="grid-container">
        <div className="grid-row">
          <div className="grid-col-12 desktop:grid-col-8">
            <p className="margin-top-0">{back}</p>
            {problem === "limited" && (
              <AlertBanner type="warning" heading={t("errors.limitedHeading")}>
                {t("errors.limited")}
              </AlertBanner>
            )}
            {problem === "load" && (
              <AlertBanner type="error" heading={t("errors.heading")}>
                {t("errors.load")}
              </AlertBanner>
            )}
            {problem === "missing" && (
              <>
                <PageHeading title={t("holder.missingTitle")} />
                <p>{t("holder.missing")}</p>
              </>
            )}
            {holder && (
              <>
                <PageHeading title={fullName(holder)} />
                <h2>{t("holder.license")}</h2>
                <p>{holder.state_of_qualifying_license.name}</p>
                <h2>{t("holder.privileges")}</h2>
                <CardGroup>
                  {holder.privileges.map((privilege) => (
                    <PrivilegeCard
                      key={privilege.number}
                      state={privilege.state.name}
                      number={privilege.number}
                      status={privilege.status}
                      activeFrom={privilege.issued_on}
                      expires={privilege.expires_on}
                      inactiveQualifier={false}
                    />
                  ))}
                </CardGroup>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** A PA's page in public verification, reached from a search result (FLOW-08). */
export default function Page() {
  // A static export needs the boundary around anything that reads the address's query.
  return (
    <Suspense>
      <Practitioner />
    </Suspense>
  );
}
