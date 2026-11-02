import { ReactNode } from "react";

export interface PageHeadingProps {
  title: ReactNode;
  /** The line under the heading, only where the wireframe draws one. */
  intro?: ReactNode;
}

/** The page's one `h1`, and its intro line when the design has one. */
export default function PageHeading({ title, intro }: PageHeadingProps) {
  return (
    <>
      <h1 className="margin-bottom-2">{title}</h1>
      {intro && <p className="usa-intro margin-top-0">{intro}</p>}
    </>
  );
}
