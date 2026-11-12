import type { Application, Profile, State } from "src/lib/application";

export const APPLICATION_ID = "3d7e2a91-6b0c-4f58-a2e4-9c1b8f0d5e36";

/** A draft in Kansas with nothing entered past the state. */
export function application(overrides: Partial<Application> = {}): Application {
  return {
    id: APPLICATION_ID,
    kind: "initial",
    status: "draft",
    sql_state_code: "KS",
    claimed_license_number: null,
    claimed_license_expires_on: null,
    opened_at: null,
    request_note: null,
    withdrawn_at: null,
    sworn_at: null,
    attestations: [],
    documents: [],
    ...overrides,
  };
}

/** A PA who has registered and entered nothing else. */
export function profile(overrides: Partial<Profile> = {}): Profile {
  return {
    legal_first_name: "Jordan",
    legal_last_name: "Sample",
    date_of_birth: null,
    residence: null,
    nccpa_certification_number: null,
    other_names: [],
    ...overrides,
  };
}

export const STATES: State[] = [
  { code: "KS", name: "Kansas", is_member: true, is_live: true },
  { code: "OK", name: "Oklahoma", is_member: true, is_live: true },
  { code: "TX", name: "Texas", is_member: false, is_live: false },
];

/** `{ data }`, as every API success answers. */
export function ok(data: unknown, status = 200) {
  return Response.json({ data }, { status });
}

/** `{ code, details }`, as every API error answers. */
export function failure(code: string, status = 409, details: string[] = []) {
  return Response.json({ code, details }, { status });
}
