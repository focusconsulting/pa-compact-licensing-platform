import type { components } from "src/api/schema";

type Schemas = components["schemas"];

/** The status type the API documents for each kind of record a status tag shows. */
export interface StatusByKind {
  application: Schemas["ApplicationStatus"];
  privilegeRequest: Schemas["PrivilegeRequestStatus"];
  privilege: Schemas["PrivilegeComputedStatus"];
  license: Schemas["LicenseComputedStatus"];
}

export type StatusKind = keyof StatusByKind;

/** A status tag's colour family; `engineering/docs/design/tokens.md` maps each to USWDS colour tokens. */
export type StatusTone = "success" | "info" | "warning" | "error" | "neutral";

export type Pill = "active" | "inactive";

/** Staff see a privilege's or license's computed status; PAs and the public see the pill. */
export type StatusView = "staff" | "public";

/** The tone of each status shown as its own tag. Typed per value, so `tsc` fails when the API adds one without a tone. */
export const STATUS_TONES: {
  [K in StatusKind]: Record<StatusByKind[K], StatusTone>;
} = {
  application: {
    draft: "neutral",
    submitted: "info",
    info_requested: "warning",
    eligible: "success",
    denied: "error",
    withdrawn: "neutral",
    eligibility_withdrawn: "error",
    superseded: "neutral",
  },
  privilegeRequest: {
    pending_payment: "warning",
    submitted: "info",
    issued: "success",
    denied: "error",
    withdrawn: "neutral",
  },
  privilege: {
    active: "success",
    expired: "neutral",
    encumbered: "error",
    inactive: "neutral",
  },
  license: {
    active: "success",
    expired: "neutral",
    lapsed: "neutral",
    inactive: "neutral",
    terminated: "error",
    encumbered: "error",
  },
};

/**
 * The public card pill for each computed status. A privilege is active only when it is not expired,
 * not deactivated, and under no unlifted discipline; discipline shows as its own field.
 */
export const PILL: {
  privilege: Record<StatusByKind["privilege"], Pill>;
  license: Record<StatusByKind["license"], Pill>;
} = {
  privilege: {
    active: "active",
    expired: "inactive",
    encumbered: "inactive",
    inactive: "inactive",
  },
  license: {
    active: "active",
    expired: "inactive",
    lapsed: "inactive",
    inactive: "inactive",
    terminated: "inactive",
    encumbered: "inactive",
  },
};

export const PILL_TONES: Record<Pill, StatusTone> = {
  active: "success",
  inactive: "neutral",
};
