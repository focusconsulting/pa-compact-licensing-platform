"use client";

import {
  Card,
  CardBody,
  CardFooter,
  CardGroup,
  CardHeader,
} from "@trussworks/react-uswds";
import Link from "next/link";
import { useTranslation } from "react-i18next";

import PageHeading from "src/components/PageHeading";
import { useCurrentUser } from "src/contexts/CurrentUserContext";
import { portalFor, type Portal } from "src/lib/navigation";

const DOORS = ["pa", "staff", "lookup"] as const;
type Door = (typeof DOORS)[number];

/** The door a signed-in visitor came through; the lookup is nobody's own. */
function doorOf(portal: Portal | null): Door | null {
  if (portal === "pa") return "pa";
  return portal ? "staff" : null;
}

/**
 * The front door (V0, V0s): one card each for PAs, for staff, and for anyone
 * looking up a privilege. It is drawn signed out and never waits on the session
 * check; once a signed-in visitor is known, their own card leads to their dashboard.
 */
export default function Home() {
  const { t } = useTranslation("home");
  const { user } = useCurrentUser();
  const own = doorOf(user ? portalFor(user.permissions) : null);

  const hrefOf = (door: Door) => {
    if (door === "lookup") return "/verify";
    return door === own ? "/dashboard" : "/login";
  };

  return (
    <div className="usa-section">
      <div className="grid-container">
        <PageHeading title={t("title")} intro={t("intro")} />
        <CardGroup>
          {DOORS.map((door) => (
            <Card key={door} gridLayout={{ desktop: { col: 4 } }}>
              <CardHeader>
                <h2 className="usa-card__heading">{t(`${door}.title`)}</h2>
              </CardHeader>
              <CardBody>
                <p>{t(`${door}.text`)}</p>
              </CardBody>
              <CardFooter>
                <Link className="usa-button" href={hrefOf(door)}>
                  {door === own ? t("dashboard") : t(`${door}.action`)}
                </Link>
              </CardFooter>
            </Card>
          ))}
        </CardGroup>
      </div>
    </div>
  );
}
