"use client";

import {
  Button,
  SummaryBox,
  SummaryBoxContent,
  SummaryBoxHeading,
} from "@trussworks/react-uswds";
import { useEffect, useState } from "react";

import { listMockUsers } from "src/lib/devSignIns";

export interface DevSignInsProps {
  onPick: (email: string) => void;
}

/**
 * Every user in the local Cognito mock, each a button that signs in as them.
 * For local development only: the sign-in page loads this module only in a
 * build that sets the mock's shared password (ADR-0020), so its strings stay
 * here, out of the i18n bundle every build ships.
 */
export default function DevSignIns({ onPick }: DevSignInsProps) {
  const [emails, setEmails] = useState<string[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let current = true;
    listMockUsers()
      .then((found) => {
        if (current) setEmails(found);
      })
      .catch(() => {
        if (current) setFailed(true);
      });
    return () => {
      current = false;
    };
  }, []);

  return (
    <SummaryBox className="margin-top-4">
      <SummaryBoxHeading headingLevel="h2">Seeded users</SummaryBoxHeading>
      <SummaryBoxContent>
        <p>
          Local development only. Choose a user from the local Cognito mock to
          sign in as them.
        </p>
        {failed && <p>The local Cognito mock did not list its users.</p>}
        {emails && (
          <ul className="usa-list usa-list--unstyled">
            {emails.map((email) => (
              <li key={email}>
                <Button type="button" unstyled onClick={() => onPick(email)}>
                  {email}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </SummaryBoxContent>
    </SummaryBox>
  );
}
