import { ReactNode } from "react";
import {
  Card,
  CardBody,
  CardFooter,
  CardHeader,
  type HeadingLevel,
} from "@trussworks/react-uswds";

export interface RecordCardProps {
  /** The card's name: the state the license or privilege is in. */
  heading: string;
  headingLevel: HeadingLevel;
  /** The StatusTag, then its qualifier where there is one. */
  status: ReactNode;
  /** Label and value pairs, in order; a pair with no value is left out. */
  fields: [label: string, value: ReactNode][];
  /** A line the state wrote, shown under the fields. */
  note?: ReactNode;
  /** A CardActionMenu, for staff. */
  actions?: ReactNode;
  footer?: ReactNode;
}

/** The layout LicenseCard and PrivilegeCard share, after CompactConnect's cards. Render it in a `CardGroup`. */
export default function RecordCard({
  heading,
  headingLevel: Heading,
  status,
  fields,
  note,
  actions,
  footer,
}: RecordCardProps) {
  return (
    <Card gridLayout={{ tablet: { col: 6 } }}>
      <CardHeader className="display-flex flex-justify flex-align-start">
        <div>
          <Heading className="usa-card__heading">{heading}</Heading>
          <div className="margin-top-1">{status}</div>
        </div>
        {actions}
      </CardHeader>
      <CardBody>
        <dl className="margin-0">
          {fields
            .filter(([, value]) => value)
            .map(([label, value]) => (
              <div key={label} className="margin-bottom-1">
                <dt className="text-bold display-inline">{label}: </dt>
                <dd className="margin-0 display-inline">{value}</dd>
              </div>
            ))}
        </dl>
        {note && <p className="margin-bottom-0">{note}</p>}
      </CardBody>
      {footer && <CardFooter>{footer}</CardFooter>}
    </Card>
  );
}
