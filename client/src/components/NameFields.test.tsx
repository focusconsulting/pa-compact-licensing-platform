import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import NameFields from "./NameFields";
import { renderWithForm } from "../tests/util";

describe("NameFields component", () => {
  it("renders first, middle, and last name fields", () => {
    renderWithForm(<NameFields label="Legal Name" />);
    expect(screen.getByRole("textbox", { name: /First name/ })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Middle name/ })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /Last name/ })).toBeInTheDocument();
  });

  it("renders fieldset legend", () => {
    renderWithForm(<NameFields label="Legal Name" />);
    expect(
      screen.getByRole("group", { name: "Legal Name" }),
    ).toBeInTheDocument();
  });

  it("makes first and last name required, middle name optional", () => {
    renderWithForm(<NameFields label="Legal Name" />);
    expect(screen.getByRole("textbox", { name: /First name/ })).toBeRequired();
    expect(screen.getByRole("textbox", { name: /Last name/ })).toBeRequired();
    expect(screen.getByRole("textbox", { name: /Middle name/ })).not.toBeRequired();
  });

  it("uses id prefix for field ids when provided", () => {
    renderWithForm(<NameFields id="applicant" label="Legal Name" />);
    expect(screen.getByRole("textbox", { name: /First name/ })).toHaveAttribute(
      "id",
      "applicantFirstName",
    );
    expect(screen.getByRole("textbox", { name: /Last name/ })).toHaveAttribute(
      "id",
      "applicantLastName",
    );
  });

  it("uses default ids when no id prefix is provided", () => {
    renderWithForm(<NameFields label="Legal Name" />);
    expect(screen.getByRole("textbox", { name: /First name/ })).toHaveAttribute(
      "id",
      "firstName",
    );
    expect(screen.getByRole("textbox", { name: /Last name/ })).toHaveAttribute(
      "id",
      "lastName",
    );
  });

  it("renders three text inputs within the fieldset", () => {
    renderWithForm(<NameFields label="Legal Name" />);
    const fieldset = screen.getByRole("group", { name: "Legal Name" });
    const inputs = fieldset.querySelectorAll("input");
    expect(inputs).toHaveLength(3);
  });
});
