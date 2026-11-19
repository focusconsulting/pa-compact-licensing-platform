import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listMockUsers } from "src/lib/devSignIns";
import { expectNoAxeViolations } from "src/tests/axe";
import DevSignIns from "./DevSignIns";

vi.mock("src/lib/devSignIns");

beforeEach(() => {
  vi.clearAllMocks();
});

describe("DevSignIns", () => {
  it("lists the mock's users, and hands over the one chosen", async () => {
    vi.mocked(listMockUsers).mockResolvedValue([
      "avery.active@demo.example",
      "kansas.staff@demo.example",
    ]);
    const onPick = vi.fn();
    const { container } = render(<DevSignIns onPick={onPick} />);

    expect(
      screen.getByRole("heading", { level: 2, name: "Seeded users" }),
    ).toBeInTheDocument();
    await userEvent.click(
      await screen.findByRole("button", { name: "kansas.staff@demo.example" }),
    );

    expect(onPick).toHaveBeenCalledWith("kansas.staff@demo.example");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    await expectNoAxeViolations(container);
  });

  it("says so when the mock does not answer", async () => {
    vi.mocked(listMockUsers).mockRejectedValue(new Error("offline"));
    render(<DevSignIns onPick={vi.fn()} />);

    expect(
      await screen.findByText("The local Cognito mock did not list its users."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });

  it.each([
    ["answers", () => Promise.resolve(["avery.active@demo.example"])],
    ["fails", () => Promise.reject(new Error("offline"))],
  ])("ignores a mock that %s after the page has gone", async (_, answer) => {
    vi.mocked(listMockUsers).mockImplementation(answer);
    const { unmount, container } = render(<DevSignIns onPick={vi.fn()} />);
    unmount();

    await new Promise((resolve) => {
      setTimeout(resolve, 0);
    });

    expect(container).toBeEmptyDOMElement();
  });
});
