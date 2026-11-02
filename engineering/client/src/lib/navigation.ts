import type { components } from "src/api/schema";

export type Permission = components["schemas"]["Permission"];

export type Portal = "pa" | "state" | "commission";

export interface NavItem {
  /** The label's key in the `shell` namespace's `nav`. */
  key:
    | "dashboard"
    | "application"
    | "home"
    | "applications"
    | "upload"
    | "uploads"
    | "practitioners"
    | "settings";
  href: string;
  /** Shown only when the user holds it in their own state. The route still checks. */
  permission?: Permission;
}

/** Each portal's nav, in the order the Figma headers draw it. The Commission's isn't drawn yet. */
export const NAV: Record<Portal, NavItem[]> = {
  pa: [
    { key: "dashboard", href: "/" },
    { key: "application", href: "/application" },
  ],
  state: [
    { key: "home", href: "/" },
    { key: "applications", href: "/applications", permission: "write" },
    { key: "upload", href: "/uploads/new", permission: "write" },
    { key: "uploads", href: "/uploads", permission: "write" },
    { key: "practitioners", href: "/practitioners" },
  ],
  commission: [
    { key: "home", href: "/" },
    { key: "practitioners", href: "/practitioners" },
    { key: "settings", href: "/settings", permission: "compact_admin" },
  ],
};

/** Which portal a user sees, from what they may do rather than their role (`roles-and-permissions.md`). */
export function portalFor(permissions: Permission[]): Portal | null {
  if (permissions.includes("manage_own_record")) return "pa";
  if (permissions.includes("compact_admin")) return "commission";
  if (permissions.includes("read_general")) return "state";
  return null;
}

/** The nav items a user may see. */
export function navFor(permissions: Permission[]): NavItem[] {
  const portal = portalFor(permissions);
  if (!portal) return [];
  return NAV[portal].filter(
    (item) => !item.permission || permissions.includes(item.permission),
  );
}
