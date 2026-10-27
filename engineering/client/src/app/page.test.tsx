import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { CognitoUserSession } from "amazon-cognito-identity-js";

import { useAuth } from "src/contexts/AuthContext";
import { getCurrentSession } from "src/lib/auth";
import { expectNoAxeViolations } from "src/tests/axe";
import { answerFetch } from "src/tests/fetch";
import Home from "./page";

vi.mock("src/lib/auth");
vi.mock("src/contexts/AuthContext");
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const mockSignOut = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({
    isLoading: false,
    idToken: "valid-token",
    email: "user@example.com",
    signOut: mockSignOut,
    signIn: vi.fn(),
    completeNewPassword: vi.fn(),
  });
  vi.mocked(getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => "valid-token" }),
  } as CognitoUserSession);
});

const mockUser = {
  user_id: "8f14e45f-ceea-467f-a0e6-2b5c3d1a9e2b",
  email: "user@example.com",
  given_name: "Jane",
  family_name: "Doe",
  role: "admin",
  state_code: "CA",
  is_active: true,
};

function answerMe(overrides: Record<string, unknown>) {
  answerFetch({ data: { ...mockUser, ...overrides } });
}

function failMe(status: number) {
  answerFetch({ code: "FORBIDDEN", details: [] }, status);
}

describe("Home (Dashboard) page", () => {
  it("displays user data after successful fetch", async () => {
    answerMe({});

    render(<Home />);

    await waitFor(() =>
      expect(screen.getByText("user@example.com")).toBeInTheDocument(),
    );
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByText("CA")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("displays error message when fetch returns non-ok response", async () => {
    failMe(403);

    render(<Home />);

    await waitFor(() => expect(screen.getByText("403")).toBeInTheDocument());
  });

  it("displays error message when the session has expired", async () => {
    vi.mocked(getCurrentSession).mockResolvedValue(null);

    render(<Home />);

    await waitFor(() =>
      expect(screen.getByText("Not authenticated")).toBeInTheDocument(),
    );
  });

  it("calls signOut when sign-out button is clicked", async () => {
    const user = userEvent.setup();
    answerMe({ given_name: null, family_name: null });

    render(<Home />);

    await waitFor(() => screen.getByRole("button", { name: /Sign out/i }));
    await user.click(screen.getByRole("button", { name: /Sign out/i }));

    expect(mockSignOut).toHaveBeenCalled();
  });

  it("shows dash for name when given_name and family_name are null", async () => {
    answerMe({ given_name: null, family_name: null, state_code: null });

    render(<Home />);

    await waitFor(() => expect(screen.getByText("—")).toBeInTheDocument());
  });

  it("shows a generic error when the request fails with a non-Error value", async () => {
    vi.mocked(getCurrentSession).mockRejectedValue("offline");

    render(<Home />);

    await waitFor(() =>
      expect(screen.getByText("Failed to load user")).toBeInTheDocument(),
    );
  });

  it("shows an inactive user's status", async () => {
    answerMe({ is_active: false });

    render(<Home />);

    await waitFor(() =>
      expect(screen.getByText("Inactive")).toBeInTheDocument(),
    );
  });

  it("has no axe violations once the user loads", async () => {
    answerMe({});

    const { container } = render(<Home />);
    await screen.findByText("user@example.com");

    await expectNoAxeViolations(container);
  });

  it("has no axe violations when the user fails to load", async () => {
    failMe(403);

    const { container } = render(<Home />);
    await screen.findByText("403");

    await expectNoAxeViolations(container);
  });
});
