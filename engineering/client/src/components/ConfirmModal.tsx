import { ReactNode, RefObject } from "react";
import { useTranslation } from "react-i18next";
import {
  ButtonGroup,
  Modal,
  ModalFooter,
  ModalHeading,
  ModalToggleButton,
  type ModalRef,
} from "@trussworks/react-uswds";

export interface ConfirmModalProps {
  id: string;
  /** Shared with the page's `ModalToggleButton opener`, which opens it. */
  modalRef: RefObject<ModalRef>;
  heading: ReactNode;
  /** What confirming will do. */
  children: ReactNode;
  confirmLabel: string;
  /** Defaults to "Go back", as C5 draws it. */
  cancelLabel?: string;
  onConfirm: () => void;
  isInitiallyOpen?: boolean;
}

/**
 * Asks before an action that can't be undone (C5). As drawn, it has no close
 * button: the user confirms or goes back.
 */
export default function ConfirmModal({
  id,
  modalRef,
  heading,
  children,
  confirmLabel,
  cancelLabel,
  onConfirm,
  isInitiallyOpen,
}: ConfirmModalProps) {
  const { t } = useTranslation("common");
  return (
    <Modal
      ref={modalRef}
      id={id}
      aria-labelledby={`${id}-heading`}
      aria-describedby={`${id}-description`}
      forceAction
      isInitiallyOpen={isInitiallyOpen}
    >
      <ModalHeading id={`${id}-heading`}>{heading}</ModalHeading>
      <div className="usa-prose">
        <p id={`${id}-description`}>{children}</p>
      </div>
      <ModalFooter>
        <ButtonGroup>
          <ModalToggleButton modalRef={modalRef} closer onClick={onConfirm}>
            {confirmLabel}
          </ModalToggleButton>
          <ModalToggleButton
            modalRef={modalRef}
            closer
            unstyled
            className="padding-105 text-center"
          >
            {cancelLabel ?? t("goBack")}
          </ModalToggleButton>
        </ButtonGroup>
      </ModalFooter>
    </Modal>
  );
}
