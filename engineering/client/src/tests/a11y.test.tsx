import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import AddressFields from "src/components/AddressFields";
import Card from "src/components/Card";
import CountryField from "src/components/CountryField";
import { DateFields } from "src/components/DateFields";
import DatePickerField from "src/components/DatePickerField";
import DisplayField from "src/components/DisplayField";
import { FilePickerField } from "src/components/FilePickerField";
import FormStep from "src/components/FormStep";
import NameFields from "src/components/NameFields";
import { SelectField } from "src/components/SelectField";
import { TextField } from "src/components/TextField";
import { expectNoAxeViolations } from "./axe";
import { renderWithForm } from "./util";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("src/lib/api", () => ({
  authFetch: vi.fn().mockResolvedValue({
    ok: true,
    json: () =>
      Promise.resolve({
        user_id: "8f14e45f-ceea-467f-a0e6-2b5c3d1a9e2b",
        email: "pa@example.com",
        given_name: "Pat",
        family_name: "Assistant",
        role: "licensee",
        state_code: null,
        is_active: true,
      }),
  }),
}));
vi.mock("src/contexts/AuthContext", () => ({
  useAuth: () => ({
    isLoading: false,
    idToken: "signed-in",
    email: null,
    signIn: vi.fn(),
    completeNewPassword: vi.fn(),
    signOut: vi.fn(),
  }),
}));

// axe walks every node; the country select alone has ~200 options, which can
// take over Vitest's 5-second default on a CI runner.
describe("accessibility (axe, WCAG 2.1 A and AA)", { timeout: 30_000 }, () => {
  it.each([
    [
      "TextField",
      () => (
        <TextField id="first" label="First name" hint="As on your licence" />
      ),
    ],
    [
      "SelectField",
      () => (
        <SelectField id="pick" label="State" options={[["KS", "Kansas"]]} />
      ),
    ],
    ["CountryField", () => <CountryField id="country" label="Country" />],
    ["NameFields", () => <NameFields id="name" label="Legal name" />],
    [
      "AddressFields",
      () => (
        <AddressFields
          id="addr"
          label="Mailing address"
          hint="Where we send letters"
        />
      ),
    ],
    ["DateFields", () => <DateFields id="dob" name="Date of birth" />],
    [
      "DatePickerField",
      () => <DatePickerField id="start" label="Start date" />,
    ],
    [
      "FilePickerField",
      () => (
        <FilePickerField id="doc" label="Upload a document" hint="PDF only" />
      ),
    ],
    [
      "DisplayField",
      () => <DisplayField id="shown" label="Licence number" value="PA-123" />,
    ],
  ])("%s has no violations", async (_, renderUi) => {
    const { container } = renderWithForm(renderUi());
    await expectNoAxeViolations(container);
  });

  it("Card has no violations", async () => {
    const { container } = render(<Card>Content</Card>);
    await expectNoAxeViolations(container);
  });

  it("FormStep has no violations", async () => {
    const { container } = render(
      <FormStep title="Your details" onBack={vi.fn()}>
        <p>Step content</p>
      </FormStep>,
    );
    await expectNoAxeViolations(container);
  });

  it("the login page has no violations", async () => {
    const { default: LoginPage } = await import("src/app/login/page");
    const { container } = render(<LoginPage />);
    await expectNoAxeViolations(container);
  });

  it("the signed-in dashboard has no violations", async () => {
    const { default: Home } = await import("src/app/page");
    const { container } = render(<Home />);
    await screen.findByText("pa@example.com");
    await expectNoAxeViolations(container);
  });

  it("reports a real violation, so a passing run means something", async () => {
    const { container } = render(<input type="text" />);
    await expect(expectNoAxeViolations(container)).rejects.toThrow(/label/);
  });
});
