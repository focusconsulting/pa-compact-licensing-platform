import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import Card from "./Card";

describe("Card component", () => {
  it("renders children", () => {
    render(<Card>Card content</Card>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("applies default styling classes", () => {
    render(<Card>Content</Card>);
    const card = screen.getByText("Content");
    expect(card).toHaveClass("bg-white", "padding-4", "shadow-2", "radius-lg");
  });

  it("appends custom className", () => {
    render(<Card className="custom-class">Content</Card>);
    const card = screen.getByText("Content");
    expect(card).toHaveClass("custom-class");
    expect(card).toHaveClass("bg-white");
  });
});
