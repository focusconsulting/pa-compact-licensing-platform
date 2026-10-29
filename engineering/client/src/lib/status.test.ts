import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, it, expect } from "vitest";

import status from "src/i18n/en/status.json";
import { PILL, PILL_TONES } from "./status";

// The API's committed document, which CI checks the generated types against.
const { components } = JSON.parse(
  readFileSync(path.resolve(__dirname, "../../../api/openapi.json"), "utf8"),
) as { components: { schemas: Record<string, { enum: string[] }> } };
const values = (schema: string): string[] => components.schemas[schema].enum;

// Labels each status needs: its own, and (privilege) a FLOW-06 qualifier, which `encumbered` lacks.
const EXPECTED: Record<keyof typeof status, string[]> = {
  application: values("ApplicationStatus"),
  privilegeRequest: values("PrivilegeRequestStatus"),
  privilege: values("PrivilegeComputedStatus"),
  privilegeQualifier: values("PrivilegeComputedStatus").filter(
    (value) => value !== "encumbered",
  ),
  license: values("LicenseComputedStatus"),
  pill: Object.keys(PILL_TONES),
};

describe.each(Object.entries(EXPECTED))("%s labels", (key, expected) => {
  it("cover every status the API documents, and nothing else", () => {
    expect(Object.keys(status[key as keyof typeof status]).sort()).toEqual(
      [...expected].sort(),
    );
  });
});

describe("the public pill", () => {
  it("is active only for an active privilege or license", () => {
    const active = Object.values(PILL).flatMap((pills) =>
      Object.entries(pills)
        .filter(([, pill]) => pill === "active")
        .map(([value]) => value),
    );

    expect(active).toEqual(["active", "active"]);
  });
});
