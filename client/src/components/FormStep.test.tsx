import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import FormStep from "./FormStep";

describe("FormStep component", () => {
  it("renders children", () => {
    render(
      <FormStep>
        <p>Step content</p>
      </FormStep>,
    );
    expect(screen.getByText("Step content")).toBeInTheDocument();
  });

  it("renders title when provided", () => {
    render(
      <FormStep title="Step Title">
        <p>Content</p>
      </FormStep>,
    );
    expect(
      screen.getByRole("heading", { name: "Step Title" }),
    ).toBeInTheDocument();
  });

  it("renders required marker by default", () => {
    render(
      <FormStep>
        <p>Content</p>
      </FormStep>,
    );
    expect(
      screen.getByText(/Required fields are marked/),
    ).toBeInTheDocument();
  });

  it("hides required marker when noRequiredMarker is true", () => {
    render(
      <FormStep noRequiredMarker>
        <p>Content</p>
      </FormStep>,
    );
    expect(
      screen.queryByText(/Required fields are marked/),
    ).not.toBeInTheDocument();
  });

  it("renders submit button with default text", () => {
    render(
      <FormStep>
        <p>Content</p>
      </FormStep>,
    );
    expect(
      screen.getByRole("button", { name: /Save and Continue/ }),
    ).toBeInTheDocument();
  });

  it("renders submit button with custom title", () => {
    render(
      <FormStep submitTitle="Finish">
        <p>Content</p>
      </FormStep>,
    );
    expect(
      screen.getByRole("button", { name: "Finish" }),
    ).toBeInTheDocument();
  });

  it("renders back button when onBack is provided", () => {
    render(
      <FormStep onBack={() => {}}>
        <p>Content</p>
      </FormStep>,
    );
    expect(
      screen.getByRole("button", { name: /Back/ }),
    ).toBeInTheDocument();
  });

  it("does not render back button when onBack is not provided", () => {
    render(
      <FormStep>
        <p>Content</p>
      </FormStep>,
    );
    expect(
      screen.queryByRole("button", { name: /Back/ }),
    ).not.toBeInTheDocument();
  });

  it("calls onSubmit when form is submitted", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(
      <FormStep onSubmit={onSubmit}>
        <p>Content</p>
      </FormStep>,
    );
    await user.click(
      screen.getByRole("button", { name: /Save and Continue/ }),
    );
    expect(onSubmit).toHaveBeenCalled();
  });

  it("calls onBack when back button is clicked", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(
      <FormStep onBack={onBack}>
        <p>Content</p>
      </FormStep>,
    );
    await user.click(screen.getByRole("button", { name: /Back/ }));
    expect(onBack).toHaveBeenCalled();
  });
});
