import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";

import { useForm, useFormContext } from "react-hook-form";

import FormStep from "./FormStep";
import { expectNoAxeViolations } from "../tests/axe";

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
    expect(screen.getByText(/Required fields are marked/)).toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "Finish" })).toBeInTheDocument();
  });

  it("renders back button when onBack is provided", () => {
    render(
      <FormStep onBack={() => {}}>
        <p>Content</p>
      </FormStep>,
    );
    expect(screen.getByRole("button", { name: /Back/ })).toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: /Save and Continue/ }));
    expect(onSubmit).toHaveBeenCalled();
  });

  it("shows the submitting spinner even with no onSubmit handler", async () => {
    const user = userEvent.setup();
    render(
      <FormStep>
        <p>Content</p>
      </FormStep>,
    );
    await user.click(screen.getByRole("button", { name: /Save and Continue/ }));
    expect(
      screen.getByAltText("A spinner indicating the form is being submitted"),
    ).toBeInTheDocument();
  });

  it("shows no spinner on submit when noSpinner is set", async () => {
    const user = userEvent.setup();
    render(
      <FormStep noSpinner>
        <p>Content</p>
      </FormStep>,
    );
    await user.click(screen.getByRole("button", { name: /Save and Continue/ }));
    expect(
      screen.queryByAltText("A spinner indicating the form is being submitted"),
    ).not.toBeInTheDocument();
  });

  it("leaves the submit event's default to the handler when noPreventDefault is set", async () => {
    const user = userEvent.setup();
    let prevented: boolean | undefined;
    render(
      <FormStep
        noPreventDefault
        onSubmit={(event) => {
          prevented = event.defaultPrevented;
          // jsdom can't navigate; stop the native submission here instead.
          event.preventDefault();
        }}
      >
        <p>Content</p>
      </FormStep>,
    );
    await user.click(screen.getByRole("button", { name: /Save and Continue/ }));
    expect(prevented).toBe(false);
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

  it("provides the form to its children when given one", () => {
    function Reader() {
      return <p>{useFormContext().getValues("name") as string}</p>;
    }
    function WithForm() {
      const form = useForm({ defaultValues: { name: "Ada" } });
      return (
        <FormStep form={form}>
          <Reader />
        </FormStep>
      );
    }

    render(<WithForm />);

    expect(screen.getByText("Ada")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <FormStep title="Your details" onBack={vi.fn()}>
        <p>Step content</p>
      </FormStep>,
    );
    await expectNoAxeViolations(container);
  });
});
