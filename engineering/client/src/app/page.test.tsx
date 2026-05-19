import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("src/lib/api");
vi.mock("src/contexts/AuthContext");
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

import { useAuth } from "src/contexts/AuthContext";
import { authFetch } from "src/lib/api";
import Home from "./page";

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
});

const mockUser = {
  id: 1,
  email: "user@example.com",
  given_name: "Jane",
  family_name: "Doe",
  role: "admin",
  state_code: "CA",
  is_active: true,
};

describe("Home (Dashboard) page", () => {
  it("displays user data after successful fetch", async () => {
    vi.mocked(authFetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockUser),
    } as Response);

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
    vi.mocked(authFetch).mockResolvedValue({
      ok: false,
      status: 403,
    } as Response);

    render(<Home />);

    await waitFor(() => expect(screen.getByText("403")).toBeInTheDocument());
  });

  it("displays error message when authFetch throws", async () => {
    vi.mocked(authFetch).mockRejectedValue(new Error("Not authenticated"));

    render(<Home />);

    await waitFor(() =>
      expect(screen.getByText("Not authenticated")).toBeInTheDocument(),
    );
  });

  it("calls signOut when sign-out button is clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(authFetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ...mockUser, given_name: null, family_name: null }),
    } as Response);

    render(<Home />);

    await waitFor(() => screen.getByRole("button", { name: /Sign out/i }));
    await user.click(screen.getByRole("button", { name: /Sign out/i }));

    expect(mockSignOut).toHaveBeenCalled();
  });

  it("shows dash for name when given_name and family_name are null", async () => {
    vi.mocked(authFetch).mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({ ...mockUser, given_name: null, family_name: null, state_code: null }),
    } as Response);

    render(<Home />);

    await waitFor(() => expect(screen.getByText("—")).toBeInTheDocument());
  });
});
