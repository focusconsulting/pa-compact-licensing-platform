import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  CurrentUserContext,
  type CurrentUser,
} from "src/contexts/CurrentUserContext";
import type { Permission } from "src/lib/navigation";
import { expectNoAxeViolations } from "src/tests/axe";
import Home from "./page";

function renderHome(permissions?: Permission[]) {
  const user = permissions
    ? ({ given_name: "Jordan", permissions } as CurrentUser)
    : null;
  return render(
    <CurrentUserContext.Provider value={{ user, error: null }}>
      <Home />
    </CurrentUserContext.Provider>,
  );
}

/** Each card's heading and where its button leads, in order. */
const doors = () =>
  screen.getAllByRole("listitem").map((card) => {
    const link = within(card).getByRole("link");
    return [
      within(card).getByRole("heading", { level: 2 }).textContent,
      link.textContent,
      link.getAttribute("href"),
    ];
  });

describe("the front door", () => {
  it("offers a signed-out visitor both sign-ins and the lookup", async () => {
    const { container } = renderHome();

    expect(
      screen.getByRole("heading", { level: 1, name: "PA Compact" }),
    ).toBeInTheDocument();
    expect(doors()).toEqual([
      ["Physician assistants", "Sign in as a PA", "/login"],
      ["State and Commission staff", "Sign in as staff", "/login"],
      ["Look up a Compact Privilege", "Look up a PA", "/verify"],
    ]);
    await expectNoAxeViolations(container);
  });

  it("leads a signed-in PA to their dashboard from their own card", async () => {
    const { container } = renderHome(["manage_own_record"]);

    expect(doors()).toEqual([
      ["Physician assistants", "Go to your dashboard", "/dashboard"],
      ["State and Commission staff", "Sign in as staff", "/login"],
      ["Look up a Compact Privilege", "Look up a PA", "/verify"],
    ]);
    await expectNoAxeViolations(container);
  });

  it.each<[string, Permission[]]>([
    ["state staff", ["read_general", "write"]],
    ["Commission staff", ["read_general", "compact_admin"]],
  ])("leads signed-in %s to theirs from the staff card", (_, permissions) => {
    renderHome(permissions);

    expect(doors().map(([, , href]) => href)).toEqual([
      "/login",
      "/dashboard",
      "/verify",
    ]);
  });

  it("offers a signed-in user with no portal the same as a visitor", () => {
    renderHome([]);

    expect(doors().map(([, action]) => action)).toEqual([
      "Sign in as a PA",
      "Sign in as staff",
      "Look up a PA",
    ]);
  });
});
