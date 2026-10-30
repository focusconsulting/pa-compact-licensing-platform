import { describe, expect, it } from "vitest";

import { navFor, portalFor, type Permission } from "./navigation";

const keys = (permissions: Permission[]) =>
  navFor(permissions).map((item) => item.key);

describe("portalFor", () => {
  it.each<[Permission[], string | null]>([
    [["manage_own_record"], "pa"],
    [["read_general", "read_private", "compact_admin"], "commission"],
    [["read_general", "write"], "state"],
    [[], null],
  ])("%j is the %s portal", (permissions, portal) => {
    expect(portalFor(permissions)).toBe(portal);
  });
});

describe("navFor", () => {
  it("gives a PA the dashboard and the application", () => {
    expect(keys(["manage_own_record"])).toEqual(["dashboard", "application"]);
  });

  it("gives state staff who can write every state item", () => {
    expect(keys(["read_general", "write"])).toEqual([
      "home",
      "applications",
      "upload",
      "uploads",
      "practitioners",
    ]);
  });

  it("hides the items that need write from read-only state staff", () => {
    expect(keys(["read_general", "read_private"])).toEqual([
      "home",
      "practitioners",
    ]);
  });

  it("gives the Commission its items", () => {
    expect(keys(["read_general", "read_private", "compact_admin"])).toEqual([
      "home",
      "practitioners",
      "settings",
    ]);
  });

  it("gives a user with no portal nothing", () => {
    expect(keys([])).toEqual([]);
  });
});
