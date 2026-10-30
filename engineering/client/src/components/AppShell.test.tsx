import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { useAuth } from "src/contexts/AuthContext";
import {
  useCurrentUser,
  type CurrentUser,
} from "src/contexts/CurrentUserContext";
import { expectNoAxeViolations } from "src/tests/axe";
import AppShell from "./AppShell";

vi.mock("src/contexts/AuthContext");
vi.mock("src/contexts/CurrentUserContext");
let pathname = "/";
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

const signOut = vi.fn();

const base: CurrentUser = {
  user_id: "8f14e45f-ceea-467f-a0e6-2b5c3d1a9e2b",
  email: "taylor@example.com",
  given_name: "Taylor",
  family_name: "Sample",
  role: "state_staff",
  state_code: "KS",
  is_active: true,
  permissions: ["read_general", "write"],
};

function as(user: Partial<CurrentUser> | null) {
  vi.mocked(useCurrentUser).mockReturnValue({
    user: user && { ...base, ...user },
    error: null,
  });
}

function renderShell() {
  return render(
    <AppShell>
      <h1>Page</h1>
    </AppShell>,
  );
}

const navLinks = () =>
  within(screen.getByRole("navigation", { name: "Primary navigation" }))
    .getAllByRole("link")
    .map((link) => link.textContent);

beforeEach(() => {
  vi.clearAllMocks();
  pathname = "/";
  vi.mocked(useAuth).mockReturnValue({
    isLoading: false,
    idToken: "token",
    email: "taylor@example.com",
    signOut,
    signIn: vi.fn(),
    completeNewPassword: vi.fn(),
  });
});

describe("AppShell", () => {
  it("shows only the wordmark while signed out", () => {
    as(null);

    renderShell();

    expect(screen.getByRole("link", { name: "PA Compact" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(
      screen.queryByRole("navigation", { name: "Primary navigation" }),
    ).toBeNull();
    expect(screen.queryByRole("button", { name: "Sign out" })).toBeNull();
  });

  it("puts the page in main, after a skip link to it", () => {
    as(null);

    renderShell();

    expect(
      screen.getByRole("link", { name: "Skip to main content" }),
    ).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
    expect(
      within(screen.getByRole("main")).getByRole("heading"),
    ).toHaveTextContent("Page");
  });

  it("gives a PA their nav and name", () => {
    as({
      role: "licensee",
      state_code: null,
      permissions: ["manage_own_record"],
    });

    renderShell();

    expect(navLinks()).toEqual(["Dashboard", "Application"]);
    expect(screen.getByText("Taylor Sample")).toBeInTheDocument();
  });

  it("gives state staff their nav, and their name with their state", () => {
    as({});

    renderShell();

    expect(navLinks()).toEqual([
      "Home",
      "Applications to review",
      "Upload license records",
      "Past uploads",
      "PA records",
    ]);
    expect(screen.getByText("Taylor Sample, KS")).toBeInTheDocument();
  });

  it("gives the Commission its nav", () => {
    as({
      role: "compact_admin",
      state_code: null,
      permissions: ["read_general", "read_private", "compact_admin"],
    });

    renderShell();

    expect(navLinks()).toEqual(["Home", "PA records", "Settings"]);
    expect(screen.getByText("Taylor Sample")).toBeInTheDocument();
  });

  it("marks the section the page is in as current", () => {
    pathname = "/applications/42";
    as({});

    renderShell();

    expect(
      screen.getByRole("link", { name: "Applications to review" }),
    ).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("signs out", async () => {
    as({});

    renderShell();
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));

    expect(signOut).toHaveBeenCalled();
  });

  it("opens and closes the nav on mobile", async () => {
    as({});

    renderShell();
    const nav = screen.getByRole("navigation", { name: "Primary navigation" });
    await userEvent.click(screen.getByRole("button", { name: "Menu" }));
    expect(nav).toHaveClass("is-visible");
    await userEvent.click(within(nav).getByRole("button", { name: /close/i }));

    expect(nav).not.toHaveClass("is-visible");
  });

  it("links the footer to the Commission's pages", () => {
    as(null);

    renderShell();

    expect(screen.getByRole("link", { name: "Return to top" })).toHaveAttribute(
      "href",
      "#top",
    );
    const links = within(
      screen.getByRole("navigation", { name: "Important links" }),
    ).getAllByRole("link");
    expect(links.map((link) => link.textContent)).toEqual([
      "About PA Compact Commission",
      "Accessibility support",
      "Privacy policy",
    ]);
    expect(
      screen.getByText("An official website of the PA Compact Commission"),
    ).toBeInTheDocument();
  });

  it.each([
    ["signed out", null],
    ["signed in", {}],
  ])("has no axe violations %s", async (_, user) => {
    as(user);

    const { container } = renderShell();

    await expectNoAxeViolations(container);
  });
});
