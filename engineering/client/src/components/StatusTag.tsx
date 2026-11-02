import { Tag } from "@trussworks/react-uswds";
import type { ParseKeys } from "i18next";
import { useTranslation } from "react-i18next";

import "src/styles/status-tag.scss";
import {
  PILL,
  PILL_TONES,
  STATUS_TONES,
  type Pill,
  type StatusByKind,
  type StatusKind,
  type StatusTone,
  type StatusView,
} from "src/lib/status";

export type StatusTagProps = {
  [K in StatusKind]: {
    kind: K;
    status: StatusByKind[K];
    /** Defaults to `"public"`, so a missed prop never shows staff detail. */
    view?: StatusView;
  };
}[StatusKind];

// Widened for lookup: the props already tie each status to its kind, which TypeScript loses once destructured.
const TONES = STATUS_TONES as Record<StatusKind, Record<string, StatusTone>>;
const PILLS = PILL as Record<keyof typeof PILL, Record<string, Pill>>;

/**
 * A record's status as a USWDS tag in its tone. In the public view a privilege
 * or license shows the Active/Inactive pill; staff see the computed status.
 */
export default function StatusTag({
  kind,
  status,
  view = "public",
}: StatusTagProps) {
  const { t } = useTranslation("status");
  const pill =
    view === "public" && (kind === "privilege" || kind === "license")
      ? PILLS[kind][status]
      : null;

  return (
    <Tag
      className={`status-tag--${pill ? PILL_TONES[pill] : TONES[kind][status]}`}
    >
      {pill ? t(`pill.${pill}`) : t(`${kind}.${status}` as ParseKeys<"status">)}
    </Tag>
  );
}
