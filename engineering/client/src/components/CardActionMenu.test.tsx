import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { expectNoAxeViolations } from "src/tests/axe";
import CardActionMenu from "./CardActionMenu";

function renderMenu() {
  const deactivate = vi.fn();
  const report = vi.fn();
  const view = render(
    <CardActionMenu
      record="Kansas privilege"
      actions={[
        { key: "deactivate", label: "Deactivate", onSelect: deactivate },
        { key: "report", label: "Report discipline", onSelect: report },
      ]}
    />,
  );
  const toggle = screen.getByRole("button", {
    name: "Actions for Kansas privilege",
  });
  return { ...view, toggle, deactivate, report };
}

describe("CardActionMenu", () => {
  it("starts closed", () => {
    const { toggle } = renderMenu();

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Deactivate" })).toBeNull();
  });

  it("opens to show its actions", async () => {
    const { toggle, container } = renderMenu();

    await userEvent.click(toggle);

    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getAllByRole("button").map((button) => button.textContent),
    ).toEqual(["Actions", "Deactivate", "Report discipline"]);
    await expectNoAxeViolations(container);
  });

  it("runs the action picked, then closes", async () => {
    const { toggle, report, deactivate } = renderMenu();

    await userEvent.click(toggle);
    await userEvent.click(
      screen.getByRole("button", { name: "Report discipline" }),
    );

    expect(report).toHaveBeenCalledOnce();
    expect(deactivate).not.toHaveBeenCalled();
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("closes on Escape, and only Escape", async () => {
    const { toggle } = renderMenu();

    await userEvent.click(toggle);
    await userEvent.keyboard("a");
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    await userEvent.keyboard("{Escape}");

    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
