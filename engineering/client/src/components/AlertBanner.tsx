import { ReactNode } from "react";
import {
  Alert,
  AlertHeading,
  AlertText,
  type HeadingLevel,
} from "@trussworks/react-uswds";

export interface AlertBannerProps {
  type: "success" | "info" | "warning" | "error" | "emergency";
  heading?: ReactNode;
  /** Defaults to `h2`; pick the level that fits where the banner sits. */
  headingLevel?: HeadingLevel;
  /** One line, no heading, smaller padding (C4b). */
  slim?: boolean;
  children?: ReactNode;
}

/**
 * A page-level message, such as the result of an action. Errors are announced
 * at once (`role="alert"`); anything else waits its turn (`role="status"`).
 */
export default function AlertBanner({
  type,
  heading,
  headingLevel = "h2",
  slim = false,
  children,
}: AlertBannerProps) {
  const urgent = type === "error" || type === "emergency";
  return (
    <Alert
      type={type}
      slim={slim}
      role={urgent ? "alert" : "status"}
      className="margin-bottom-4"
    >
      {heading && <AlertHeading level={headingLevel}>{heading}</AlertHeading>}
      {children && <AlertText>{children}</AlertText>}
    </Alert>
  );
}
