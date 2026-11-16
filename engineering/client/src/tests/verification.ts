import type { Holder, HolderSummary } from "src/lib/verification";

export const HOLDER_ID = "5f0c2d6e-8a41-4b7c-9d13-6e2f4a8b1c90";

const KANSAS = { code: "KS", name: "Kansas" };
const OKLAHOMA = { code: "OK", name: "Oklahoma" };
const MISSOURI = { code: "MO", name: "Missouri" };

/** A search result: Jordan Sample, licensed in Kansas, with privileges in two states. */
export function summary(overrides: Partial<HolderSummary> = {}): HolderSummary {
  return {
    id: HOLDER_ID,
    first_name: "Jordan",
    last_name: "Sample",
    name_suffix: null,
    state_of_qualifying_license: KANSAS,
    privilege_states: [OKLAHOMA, MISSOURI],
    ...overrides,
  };
}

/** Jordan Sample's public record, with one privilege in each public status. */
export function holder(overrides: Partial<Holder> = {}): Holder {
  return {
    id: HOLDER_ID,
    first_name: "Jordan",
    last_name: "Sample",
    name_suffix: null,
    state_of_qualifying_license: KANSAS,
    privileges: [
      {
        state: OKLAHOMA,
        number: "PA-OK-000001",
        status: "active",
        issued_on: "2026-10-23",
        expires_on: "2027-06-30",
      },
      {
        state: MISSOURI,
        number: "PA-MO-000007",
        status: "expired",
        issued_on: "2025-08-04",
        expires_on: "2026-06-30",
      },
      {
        state: { code: "CO", name: "Colorado" },
        number: "PA-CO-000014",
        status: "inactive",
        issued_on: "2026-07-20",
        expires_on: "2028-06-30",
      },
    ],
    ...overrides,
  };
}

/** A page of results as the API returns it. */
export function found(holders: HolderSummary[], total = holders.length) {
  return Response.json({
    data: holders,
    page: { number: 1, size: 25, total },
  });
}
