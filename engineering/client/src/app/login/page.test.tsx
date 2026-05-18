import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockPush = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));
vi.mock("src/contexts/AuthContext");

import { useAuth } from "src/contexts/AuthContext";
import LoginPage from "./page";

const mockSignIn = vi.fn();
const mockCompleteNewPassword = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useAuth).mockReturnValue({
    signIn: mockSignIn,
    completeNewPassword: mockCompleteNewPassword,
    signOut: vi.fn(),
    isLoading: false,
    idToken: null,
    email: null,
  } as ReturnType<typeof useAuth>);
});

describe("LoginPage", () => {
  it("renders the sign-in form", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { name: /Sign in/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign in/i })).toBeInTheDocument();
  });

  it("redirects to home after successful sign-in", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({ type: "success", session: {} });

    render(<LoginPage />);
    await user.type(screen.getByRole("textbox", { name: /Email address/i }), "test@example.com");
    await user.type(document.getElementById("password")!, "password123");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/"));
  });

  it("shows set-password form when newPasswordRequired", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: { phone_number: "+1234" },
    });

    render(<LoginPage />);
    await user.type(screen.getByRole("textbox", { name: /Email address/i }), "test@example.com");
    await user.type(document.getElementById("password")!, "password");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /Set a new password/i })).toBeInTheDocument(),
    );
  });

  it("shows error when sign-in fails", async () => {
    const user = userEvent.setup();
    mockSignIn.mockRejectedValue(new Error("Incorrect username or password"));

    render(<LoginPage />);
    await user.type(screen.getByRole("textbox", { name: /Email address/i }), "bad@example.com");
    await user.type(document.getElementById("password")!, "wrongpass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() =>
      expect(screen.getByText(/Incorrect username or password/i)).toBeInTheDocument(),
    );
  });

  it("shows error when new passwords do not match", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });

    render(<LoginPage />);
    await user.type(screen.getByRole("textbox", { name: /Email address/i }), "test@example.com");
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => screen.getByLabelText(/New password/));
    await user.type(screen.getByLabelText(/New password/), "NewPass123!");
    await user.type(screen.getByLabelText(/Confirm new password/), "DifferentPass!");
    await user.click(screen.getByRole("button", { name: /Set password/i }));

    expect(screen.getByText(/Passwords do not match/i)).toBeInTheDocument();
  });

  it("redirects to home after successful password change", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });
    mockCompleteNewPassword.mockResolvedValue(undefined);

    render(<LoginPage />);
    await user.type(screen.getByRole("textbox", { name: /Email address/i }), "test@example.com");
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => screen.getByLabelText(/New password/));
    await user.type(screen.getByLabelText(/New password/), "NewPass123!");
    await user.type(screen.getByLabelText(/Confirm new password/), "NewPass123!");
    await user.click(screen.getByRole("button", { name: /Set password/i }));

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/"));
  });

  it("shows error when password change fails", async () => {
    const user = userEvent.setup();
    mockSignIn.mockResolvedValue({
      type: "newPasswordRequired",
      user: {},
      userAttributes: {},
    });
    mockCompleteNewPassword.mockRejectedValue(new Error("Password policy not met"));

    render(<LoginPage />);
    await user.type(screen.getByRole("textbox", { name: /Email address/i }), "test@example.com");
    await user.type(document.getElementById("password")!, "pass");
    await user.click(screen.getByRole("button", { name: /Sign in/i }));

    await waitFor(() => screen.getByLabelText(/New password/));
    await user.type(screen.getByLabelText(/New password/), "NewPass123!");
    await user.type(screen.getByLabelText(/Confirm new password/), "NewPass123!");
    await user.click(screen.getByRole("button", { name: /Set password/i }));

    await waitFor(() =>
      expect(screen.getByText(/Password policy not met/i)).toBeInTheDocument(),
    );
  });
});
