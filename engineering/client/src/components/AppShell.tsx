"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation } from "react-i18next";
import {
  Button,
  ExtendedNav,
  Footer,
  Header,
  Identifier,
  IdentifierIdentity,
  IdentifierLink,
  IdentifierLinkItem,
  IdentifierLinks,
  IdentifierMasthead,
  NavMenuButton,
  Title,
} from "@trussworks/react-uswds";

import { useAuth } from "src/contexts/AuthContext";
import {
  useCurrentUser,
  type CurrentUser,
} from "src/contexts/CurrentUserContext";
import { navFor, portalFor } from "src/lib/navigation";

/** Placeholders until the Commission gives the pages' addresses. */
export const FOOTER_LINKS = {
  about: "https://www.pacompact.org/",
  accessibility: "https://www.pacompact.org/",
  privacy: "https://www.pacompact.org/",
} as const;

function isCurrent(href: string, pathname: string): boolean {
  return pathname.startsWith(href);
}

function displayName(user: CurrentUser): string {
  return [user.given_name, user.family_name].filter(Boolean).join(" ");
}

/**
 * The frame around every page, as drawn in Figma's PROJECT components: skip
 * link, header with the user's nav, the page, and the footer. Signed out, the
 * header shows only the wordmark.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation("shell");
  const { signOut } = useAuth();
  const { user } = useCurrentUser();
  const pathname = usePathname();
  const [expanded, setExpanded] = useState(false);
  const toggle = () => setExpanded((open) => !open);
  const portal = user && portalFor(user.permissions);
  const name =
    user && portal === "state"
      ? t("staffName", { name: displayName(user), state: user.state_code })
      : user && displayName(user);

  return (
    // A column as tall as the window, with the page taking the slack, keeps the
    // footer at the bottom when the page is short.
    <div className="display-flex flex-column minh-viewport">
      <a className="usa-skipnav" href="#main-content">
        {t("skipLink")}
      </a>
      <Header extended showMobileOverlay={expanded}>
        <div className="usa-navbar">
          <Title>
            <Link href="/" className="display-inline-flex flex-align-center">
              <img
                src="/img/pa-compact-logo.png"
                alt={t("wordmark")}
                className="height-5 width-auto display-block"
              />
            </Link>
          </Title>
          {user && <NavMenuButton onClick={toggle} label={t("menu")} />}
        </div>
        {user && (
          <ExtendedNav
            aria-label={t("primaryNav")}
            mobileExpanded={expanded}
            onToggleMobileNav={toggle}
            primaryItems={navFor(user.permissions).map((item) => (
              <Link
                key={item.key}
                href={item.href}
                className={`usa-nav__link${isCurrent(item.href, pathname) ? " usa-current" : ""}`}
                aria-current={
                  isCurrent(item.href, pathname) ? "page" : undefined
                }
              >
                <span>{t(`nav.${item.key}`)}</span>
              </Link>
            ))}
            secondaryItems={[
              <span key="name">{name}</span>,
              <Button key="signOut" type="button" unstyled onClick={signOut}>
                {t("signOut")}
              </Button>,
            ]}
          />
        )}
      </Header>
      <main id="main-content" className="flex-1">
        {children}
      </main>
      <Footer
        size="slim"
        returnToTop={
          <div className="grid-container usa-footer__return-to-top">
            <a href="#top">{t("returnToTop")}</a>
          </div>
        }
        primary={null}
        secondary={
          <div className="grid-row grid-gap flex-align-center padding-y-2">
            <div className="grid-col-12 tablet:grid-col-4 margin-bottom-2 tablet:margin-bottom-0">
              <img
                src="/img/pa-compact-logo-stacked.png"
                alt={t("wordmark")}
                className="height-8 width-auto display-block"
              />
            </div>
            <div className="grid-col-12 tablet:grid-col-8">
              <p className="margin-0 font-body-sm">
                {t("footer.contactPrompt")}
                <a
                  className="usa-link"
                  href={`mailto:${t("footer.contactEmail")}`}
                >
                  {t("footer.contactEmail")}
                </a>
              </p>
            </div>
          </div>
        }
      />
      <Identifier>
        <IdentifierMasthead aria-label={t("identifier.label")}>
          <IdentifierIdentity domain={t("identifier.domain")}>
            {t("identifier.official")}
          </IdentifierIdentity>
        </IdentifierMasthead>
        <IdentifierLinks
          navProps={{ "aria-label": t("identifier.linksLabel") }}
        >
          {(["about", "accessibility", "privacy"] as const).map((key) => (
            <IdentifierLinkItem key={key}>
              <IdentifierLink
                href={FOOTER_LINKS[key]}
                className="usa-link--external"
              >
                {t(`identifier.${key}`)}
              </IdentifierLink>
            </IdentifierLinkItem>
          ))}
        </IdentifierLinks>
      </Identifier>
    </div>
  );
}
