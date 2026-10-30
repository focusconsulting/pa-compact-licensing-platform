import { useRef } from "react";
import type { Meta, StoryObj } from "@storybook/nextjs";
import { ModalToggleButton, type ModalRef } from "@trussworks/react-uswds";

import ConfirmModal from "./ConfirmModal";

const meta: Meta<typeof ConfirmModal> = {
  title: "Components/ConfirmModal",
  component: ConfirmModal,
  parameters: { layout: "fullscreen" },
};

export default meta;
type Story = StoryObj<typeof ConfirmModal>;

function RecordDecision({ isInitiallyOpen }: { isInitiallyOpen?: boolean }) {
  const modalRef = useRef<ModalRef>(null);
  return (
    <div className="padding-2">
      <ModalToggleButton modalRef={modalRef} opener>
        Record decision
      </ModalToggleButton>
      <ConfirmModal
        id="record-decision"
        modalRef={modalRef}
        heading="Record Sample State's decision"
        confirmLabel="Record decision"
        onConfirm={() => {}}
        isInitiallyOpen={isInitiallyOpen}
      >
        Jordan Sample is eligible to participate in the compact, and Sample
        State will serve as their state of qualifying license.
      </ConfirmModal>
    </div>
  );
}

/** C5, as drawn. */
export const Open: Story = { render: () => <RecordDecision isInitiallyOpen /> };

export const Closed: Story = { render: () => <RecordDecision /> };
