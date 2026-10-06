// SAMPLE ONLY, not for merge. Drafted from Figma "PA Compact Parts Library",
// page "DRAFT SAMPLE: FLOW-02", frame FLOW-02/SCR-02 (High), using the parts crosswalk.
// Rebuilt 2026-10-01: each check sits under the evidence it checks. Words follow
// design/samples/flow-02-copy-deck.md (checked with plain-copy).
// Not wired to the API; strings are not yet in i18n.
import {
  Alert,
  Breadcrumb,
  BreadcrumbBar,
  BreadcrumbLink,
  Link,
  Button,
  Checkbox,
  DatePicker,
  Fieldset,
  Label,
  Radio,
  Table,
  Tag,
  Textarea,
} from "@trussworks/react-uswds";
import { ReactNode, useState } from "react";

export interface CaseRecord {
  paName: string;
  received: string;
  receivedIso: string;
  day: number;
  waitingSince?: string;
  details: [string, string][];
  basis: [string, string][];
  proofLabel: string;
  license: { field: string; pa: string; state: string }[];
  investigationStatement: string;
  signedOn: string;
  openInvestigations: string;
}

function KeyValueTable({ rows }: { rows: [string, string][] }) {
  return (
    <Table bordered fullWidth>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}>
            <th scope="row">{k}</th>
            <td>{v}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="margin-top-5">
      <h2>{title}</h2>
      {children}
    </section>
  );
}

export function SqlCaseView({ record }: { record: CaseRecord }) {
  const [basisOk, setBasisOk] = useState(false);
  const [licenseOk, setLicenseOk] = useState(false);
  const [cbcDate, setCbcDate] = useState<string | undefined>();
  const [investigationOk, setInvestigationOk] = useState(false);
  const [decision, setDecision] = useState<"eligible" | "not-eligible" | null>(null);

  const differences = record.license.filter((r) => r.pa !== r.state);
  // FLOW-02 guardrail: no decision until the license is confirmed and the
  // background check date is entered.
  // Focus preference: after a note is sent, the decision waits for the PA.
  const waiting = !!record.waitingSince;
  const canDecide = licenseOk && !!cbcDate && decision !== null && !waiting;
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="grid-container padding-y-4">
      <BreadcrumbBar>
        <Breadcrumb>
          <BreadcrumbLink href="/">Home</BreadcrumbLink>
        </Breadcrumb>
        <Breadcrumb>
          <BreadcrumbLink href="/applications">Applications to review</BreadcrumbLink>
        </Breadcrumb>
        <Breadcrumb current>{record.paName}</Breadcrumb>
      </BreadcrumbBar>

      {waiting && (
        <Alert type="warning" headingLevel="h2" heading="Waiting for the PA">
          {`You sent a note on ${record.waitingSince}. You can decide when they reply.`}
        </Alert>
      )}
      <h1>{record.paName}</h1>
      <Tag>{waiting ? "Waiting for the PA" : "Ready to review"}</Tag> <Tag>{`Received ${record.received}`}</Tag>{" "}
      <Tag>{`Day ${record.day} of 60`}</Tag>

      <Section title="What the PA told us">
        <KeyValueTable rows={record.details} />
      </Section>

      <Section title="1. Is [your state] the PA’s home state?">
        <KeyValueTable rows={record.basis} />
        <Link href="#proof">{record.proofLabel}</Link>
        <Checkbox
          id="basisOk"
          name="basisOk"
          label="This matches our records"
          labelDescription="Not sure? Send the PA a note below."
          checked={basisOk}
          onChange={(e) => setBasisOk(e.target.checked)}
        />
      </Section>

      <Section title="2. Does the license match your records?">
        <Table bordered fullWidth>
          <thead>
            <tr>
              <th scope="col"><span className="usa-sr-only">Field</span></th>
              <th scope="col">What the PA entered</th>
              <th scope="col">Your records</th>
            </tr>
          </thead>
          <tbody>
            {record.license.map((r) => (
              <tr key={r.field}>
                <th scope="row">{r.field}</th>
                <td>{r.pa}</td>
                <td>
                  {r.state}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
        {differences.length > 0 && (
          <Alert type="warning" headingLevel="h3" slim>
            {`The ${differences.map((d) => d.field.toLowerCase()).join(" and ")} ${differences.length > 1 ? "don’t" : "doesn’t"} match. Check which is right before you confirm.`}
          </Alert>
        )}
        <Checkbox
          id="licenseOk"
          name="licenseOk"
          label="The license matches and has no restrictions"
          checked={licenseOk}
          onChange={(e) => setLicenseOk(e.target.checked)}
        />
      </Section>

      <Section title="3. Has the background check been done?">
        <Label htmlFor="cbcDate" id="cbcDateLabel">
          Date your state’s background check was finished
        </Label>
        <span className="usa-hint" id="cbcDateHint">
          Must be within 60 days of the received date. Don’t enter or upload the results.
        </span>
        <DatePicker
          id="cbcDate"
          name="cbcDate"
          aria-labelledby="cbcDateLabel"
          aria-describedby="cbcDateHint"
          minDate={record.receivedIso}
          maxDate={today}
          onChange={(v) => setCbcDate(v || undefined)}
        />
      </Section>

      <Section title="4. Is there an open investigation the PA didn’t mention?">
        <KeyValueTable
          rows={[
            [`What the PA signed (${record.signedOn})`, `“${record.investigationStatement}”`],
            ["Open investigations in your records", record.openInvestigations],
          ]}
        />
        <Checkbox
          id="investigationOk"
          name="investigationOk"
          label="I checked our investigation records and found no conflict"
          checked={investigationOk}
          onChange={(e) => setInvestigationOk(e.target.checked)}
        />
      </Section>

      <Section title="Need more from the PA? (optional)">
        <Label htmlFor="requestNote">Note to the PA</Label>
        <span className="usa-hint" id="requestNoteHint">
          The PA gets an email asking them to sign in and read it.
        </span>
        <Textarea id="requestNote" name="requestNote" aria-describedby="requestNoteHint" />
        <Button type="button" outline className="margin-top-2">
          Send note to the PA
        </Button>
      </Section>

      <Section title="5. Your decision">
        <Fieldset legend="Your decision" legendStyle="srOnly">
          <Radio id="eligible" name="decision" label="Eligible" checked={decision === "eligible"} onChange={() => setDecision("eligible")} />
          <Radio id="notEligible" name="decision" label="Not eligible" checked={decision === "not-eligible"} onChange={() => setDecision("not-eligible")} />
        </Fieldset>
        {decision === "not-eligible" && (
          <>
            <Label htmlFor="notEligibleReason">Reason the PA isn’t eligible</Label>
            <span className="usa-hint" id="notEligibleReasonHint">
              The PA will see this and how to appeal to your state. Don’t include criminal history details.
            </span>
            <Textarea id="notEligibleReason" name="notEligibleReason" aria-describedby="notEligibleReasonHint" />
          </>
        )}
        <Button type="button" disabled={!canDecide} aria-describedby="decideHint" className="margin-top-3">
          Record decision
        </Button>
        {!canDecide && (
          <p className="usa-hint" id="decideHint">
            {waiting
              ? "You can decide when the PA replies."
              : "Confirm the license and enter the background check date first."}
          </p>
        )}
      </Section>
    </div>
  );
}

export const sampleRecord: CaseRecord = {
  paName: "Sample PA A",
  received: "Sep 08, 2026",
  receivedIso: "2026-09-08",
  day: 23,
  details: [
    ["Date of birth", "Mar 14, 1988"],
    ["Home address", "12 Example Street, Sample City, [Your state]"],
    ["Email", "sample.pa@example.com"],
    ["NCCPA certification", "Current, #000000"],
  ],
  basis: [["The PA’s reason", "I live in this state"]],
  proofLabel: "View proof of address (PDF, uploaded Sep 08, 2026)",
  license: [
    { field: "License number", pa: "PA-12345", state: "PA-12345" },
    { field: "Status", pa: "Active", state: "Active" },
    { field: "Expiry date", pa: "Jun 30, 2027", state: "Jun 30, 2026" },
    { field: "Restrictions", pa: "None", state: "None" },
  ],
  investigationStatement: "I’m not aware of any pending investigation of my license",
  signedOn: "Sep 08, 2026",
  openInvestigations: "None found",
};

export const waitingRecord: CaseRecord = { ...sampleRecord, waitingSince: "Sep 20, 2026" };

export default SqlCaseView;
