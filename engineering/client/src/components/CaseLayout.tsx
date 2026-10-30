import { ReactNode } from "react";
import Link, { type LinkProps } from "next/link";
import { useTranslation } from "react-i18next";
import {
  Breadcrumb,
  BreadcrumbBar,
  BreadcrumbLink,
} from "@trussworks/react-uswds";

export interface Crumb {
  label: string;
  href: string;
}

export interface CaseLayoutProps {
  /** The pages above this one; the record's own name ends the trail. */
  breadcrumbs: Crumb[];
  /** The record's name, as the page's `h1`. */
  title: string;
  /** The line under the name, where the design has one, such as C4's "Received …". */
  subtitle?: ReactNode;
  /** A summary box or alert banner above the sections (C6b, C6). */
  banner?: ReactNode;
  /** The record's `CaseSection`s, in page order. */
  children: ReactNode;
}

/** One record, read top to bottom, as C4 and C6b lay it out. */
export default function CaseLayout({
  breadcrumbs,
  title,
  subtitle,
  banner,
  children,
}: CaseLayoutProps) {
  const { t } = useTranslation("common");
  return (
    <>
      <BreadcrumbBar navProps={{ "aria-label": t("breadcrumbs") }}>
        {[
          ...breadcrumbs.map((crumb) => (
            <Breadcrumb key={crumb.href}>
              <BreadcrumbLink<LinkProps> asCustom={Link} href={crumb.href}>
                {crumb.label}
              </BreadcrumbLink>
            </Breadcrumb>
          )),
          <Breadcrumb key="current" current>
            {title}
          </Breadcrumb>,
        ]}
      </BreadcrumbBar>
      <h1 className="margin-top-0 margin-bottom-1">{title}</h1>
      {subtitle && <p className="margin-top-0 font-body-md">{subtitle}</p>}
      {banner}
      {children}
    </>
  );
}

export interface CaseSectionProps {
  heading: string;
  children: ReactNode;
}

/** One `h2` section of a record. */
export function CaseSection({ heading, children }: CaseSectionProps) {
  return (
    <section className="margin-top-4">
      <h2>{heading}</h2>
      {children}
    </section>
  );
}
