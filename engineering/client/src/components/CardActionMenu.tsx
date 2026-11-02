import { KeyboardEvent, useId, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@trussworks/react-uswds";

export interface CardAction {
  key: string;
  label: string;
  onSelect: () => void;
}

export interface CardActionMenuProps {
  /** What the card is, so each card's button has its own accessible name. */
  record: string;
  actions: CardAction[];
}

/**
 * The staff actions on a license or privilege card, such as Deactivate or
 * Report discipline (crosswalk §4.7). USWDS has no menu, so this is a
 * disclosure: a button that shows and hides a list of buttons.
 */
export default function CardActionMenu({
  record,
  actions,
}: CardActionMenuProps) {
  const { t } = useTranslation("common");
  const [open, setOpen] = useState(false);
  const listId = useId();

  const closeOnEscape = (event: KeyboardEvent) => {
    if (event.key === "Escape") setOpen(false);
  };

  return (
    // The keydown is the menu's Escape handling; the buttons inside are what take focus.
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions
    <div className="position-relative" onKeyDown={closeOnEscape}>
      <Button
        type="button"
        outline
        className="margin-right-0"
        aria-label={`${t("card.actions")} ${t("card.about", { record })}`}
        aria-expanded={open}
        aria-controls={listId}
        onClick={() => setOpen((shown) => !shown)}
      >
        {t("card.actions")}
      </Button>
      <ul
        id={listId}
        hidden={!open}
        className="usa-list--unstyled position-absolute right-0 z-top bg-white border-1px border-base-lighter shadow-2 padding-y-1 width-card"
      >
        {actions.map((action) => (
          <li key={action.key}>
            <Button
              type="button"
              unstyled
              className="padding-x-2 padding-y-1 width-full text-left"
              onClick={() => {
                setOpen(false);
                action.onSelect();
              }}
            >
              {action.label}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
