import { useRef } from "react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ModalToggleButton, type ModalRef } from "@trussworks/react-uswds";

import { expectNoAxeViolations } from "src/tests/axe";
import ConfirmModal from "./ConfirmModal";

// The modal's focus trap counts an element as visible only if it has layout, which jsdom never gives.
beforeAll(() => {
  vi.spyOn(Element.prototype, "getClientRects").mockReturnValue([
    {},
  ] as unknown as DOMRectList);
});

function Page({
  onConfirm,
  cancelLabel,
}: {
  onConfirm: () => void;
  cancelLabel?: string;
}) {
  const modalRef = useRef<ModalRef>(null);
  return (
    <>
      <ModalToggleButton modalRef={modalRef} opener>
        Open
      </ModalToggleButton>
      <ConfirmModal
        id="record-decision"
        modalRef={modalRef}
        heading="Record Sample State's decision"
        confirmLabel="Record decision"
        cancelLabel={cancelLabel}
        onConfirm={onConfirm}
      >
        Jordan Sample is eligible to participate in the compact.
      </ConfirmModal>
    </>
  );
}

const isOpen = () =>
  document.getElementById("record-decision")?.classList.contains("is-visible");

async function open(onConfirm = vi.fn(), cancelLabel?: string) {
  render(<Page onConfirm={onConfirm} cancelLabel={cancelLabel} />);
  await userEvent.click(screen.getByRole("button", { name: "Open" }));
  return onConfirm;
}

describe("ConfirmModal", () => {
  it("asks before the action, named by its heading and description", async () => {
    await open();

    expect(isOpen()).toBe(true);
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAccessibleName("Record Sample State's decision");
    expect(dialog).toHaveAccessibleDescription(
      "Jordan Sample is eligible to participate in the compact.",
    );
  });

  it("confirms, then closes", async () => {
    const onConfirm = await open();

    await userEvent.click(
      screen.getByRole("button", { name: "Record decision" }),
    );

    expect(onConfirm).toHaveBeenCalledOnce();
    expect(isOpen()).toBe(false);
  });

  it("goes back without confirming", async () => {
    const onConfirm = await open();

    await userEvent.click(screen.getByRole("button", { name: "Go back" }));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(isOpen()).toBe(false);
  });

  it("takes another label for going back", async () => {
    await open(vi.fn(), "Cancel");

    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("has no axe violations while open", async () => {
    await open();

    await expectNoAxeViolations(document.body);
  });
});
