import type { components } from "src/api/schema";
import { api } from "src/lib/api";

export type Application = components["schemas"]["ApplicationOut"];
export type Attestation = components["schemas"]["AttestationOut"];
export type Profile = components["schemas"]["ProfileOut"];
export type ProfileUpdate = components["schemas"]["ProfileUpdate"];
export type ApplicationUpdate = components["schemas"]["ApplicationUpdate"];
export type State = components["schemas"]["StateOut"];
export type Dashboard = components["schemas"]["Dashboard"];

/** A failed call, with the API's error `code`, or the HTTP status when the body has none. */
export class ApplicationError extends Error {
  constructor(
    readonly code: string,
    readonly details: string[] = [],
  ) {
    super(code);
  }
}

interface Result<T> {
  data?: { data: T };
  error?: { code?: string; details?: string[] };
  response: Response;
}

async function unwrap<T>(call: Promise<Result<T>>): Promise<T> {
  const { data, error, response } = await call;
  if (!data) {
    throw new ApplicationError(
      error?.code ?? String(response.status),
      error?.details,
    );
  }
  return data.data;
}

/** The statuses in which the PA can still change their answers. */
const EDITABLE = new Set<Application["status"]>(["draft", "info_requested"]);

/** The application the wizard is working on, if there is one. */
export function openApplication(applications: Application[]) {
  return applications.find((a) => EDITABLE.has(a.status));
}

/** The signed-in PA's applications, newest first. */
export const loadApplications = () => unwrap(api.GET("/api/me/applications"));

/** The signed-in PA's profile. */
export const loadProfile = () => unwrap(api.GET("/api/me/profile"));

/** Saves profile fields; omitted fields keep their value. */
export const saveProfile = (body: ProfileUpdate) =>
  unwrap(api.PATCH("/api/me/profile", { body }));

/** Every state, with whether it takes applications. */
export const loadStates = () => unwrap(api.GET("/api/public/states"));

/** The current participation attestations, in the order to show them. */
export const loadAttestations = () =>
  unwrap(
    api.GET("/api/public/attestations", {
      params: { query: { applies_to: "participation" } },
    }),
  );

/** Starts a draft in a live state. */
export const startApplication = (sqlStateCode: string) =>
  unwrap(
    api.POST("/api/me/applications", {
      body: { sql_state_code: sqlStateCode },
    }),
  );

/** Saves a step's answers on a draft or an application waiting on information. */
export const saveApplication = (id: string, body: ApplicationUpdate) =>
  unwrap(
    api.PATCH("/api/me/applications/{application_id}", {
      params: { path: { application_id: id } },
      body,
    }),
  );

/** Records that the PA accepted this version of an attestation. */
export const acceptAttestation = (id: string, code: string, version: number) =>
  unwrap(
    api.POST("/api/me/applications/{application_id}/attestations", {
      params: { path: { application_id: id } },
      body: { code, version },
    }),
  );

/** Submits the application, or resubmits it, with the sworn statement. */
export const submitApplication = (id: string, swornName: string) =>
  unwrap(
    api.POST("/api/me/applications/{application_id}/submit", {
      params: { path: { application_id: id } },
      body: { sworn: true, sworn_name: swornName },
    }),
  );

/** Whether the application accepted this attestation at its current version. */
export function accepted(application: Application, attestation: Attestation) {
  return application.attestations.some(
    (a) => a.code === attestation.code && a.version === attestation.version,
  );
}

/** The signed-in PA's license, applications, privileges, and next step. */
export const loadDashboard = () => unwrap(api.GET("/api/me/dashboard"));

/** Withdraws an application the state has received and not decided. */
export const withdrawApplication = (id: string) =>
  unwrap(
    api.POST("/api/me/applications/{application_id}/withdraw", {
      params: { path: { application_id: id } },
    }),
  );
