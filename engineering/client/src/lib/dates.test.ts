import { describe, expect, it } from "vitest";

import { formatDate } from "./dates";

describe("formatDate", () => {
  it("writes a date as the designs do", () => {
    expect(formatDate("2026-10-20")).toBe("Oct 20, 2026");
  });

  it("keeps a date with no time on its calendar day", () => {
    expect(formatDate("2026-01-01")).toBe("Jan 1, 2026");
  });

  it("writes a timestamp's day", () => {
    expect(formatDate("2026-10-20T12:00:00Z")).toBe("Oct 20, 2026");
  });
});
