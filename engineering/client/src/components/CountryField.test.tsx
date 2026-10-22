import { describe, it, expect } from "vitest";
import { screen } from "@testing-library/react";

import CountryField from "./CountryField";
import { renderWithForm } from "../tests/util";
import { expectNoAxeViolations } from "../tests/axe";

describe("CountryField component", () => {
  it("renders a select element", () => {
    renderWithForm(<CountryField id="country" label="Country" />);
    expect(
      screen.getByRole("combobox", { name: /Country/ }),
    ).toBeInTheDocument();
  });

  it("renders country options from i18n", () => {
    renderWithForm(<CountryField id="country" label="Country" />);
    const select = screen.getByRole("combobox", { name: /Country/ });
    // The select should have options populated from the country translations
    expect(select.querySelectorAll("option").length).toBeGreaterThan(1);
  });

  it("is not required by default", () => {
    renderWithForm(<CountryField id="country" label="Country" />);
    expect(
      screen.getByRole("combobox", { name: /Country/ }),
    ).not.toBeRequired();
  });

  it("can be marked as required", () => {
    renderWithForm(<CountryField id="country" label="Country" required />);
    expect(screen.getByRole("combobox", { name: /Country/ })).toBeRequired();
  });

  it("renders with birthCountry flag without throwing", () => {
    expect(() =>
      renderWithForm(
        <CountryField id="country" label="Country" birthCountry />,
      ),
    ).not.toThrow();
  });

  // axe walks all ~200 country options, which can outlast Vitest's
  // 5-second default on a CI runner.
  it("has no axe violations", { timeout: 30_000 }, async () => {
    const { container } = renderWithForm(
      <CountryField id="country" label="Country" />,
    );
    await expectNoAxeViolations(container);
  });
});
