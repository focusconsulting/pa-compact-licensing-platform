import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const mockPush = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));
vi.mock("src/contexts/AuthContext");

import { useAuth } from "src/contexts/AuthContext";
import ProtectedRoute from "./ProtectedRoute";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ProtectedRoute", () => {
  it("renders null while loading", () => {
    vi.mocked(useAuth).mockReturnValue({
      isLoading: true,
      idToken: null,
      email: null,
    } as ReturnType<typeof useAuth>);

    const { container } = render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>,
    );

    expect(container.firstChild).toBeNull();
    expect(screen.queryByText("Protected content")).not.toBeInTheDocument();
  });

  it("renders null and redirects when not authenticated", async () => {
    vi.mocked(useAuth).mockReturnValue({
      isLoading: false,
      idToken: null,
      email: null,
    } as ReturnType<typeof useAuth>);

    const { container } = render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>,
    );

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/login"));
    expect(container.firstChild).toBeNull();
  });

  it("renders children when authenticated", () => {
    vi.mocked(useAuth).mockReturnValue({
      isLoading: false,
      idToken: "valid-token",
      email: "user@example.com",
    } as ReturnType<typeof useAuth>);

    render(
      <ProtectedRoute>
        <div>Protected content</div>
      </ProtectedRoute>,
    );

    expect(screen.getByText("Protected content")).toBeInTheDocument();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("does not redirect when loading even without token", async () => {
    vi.mocked(useAuth).mockReturnValue({
      isLoading: true,
      idToken: null,
      email: null,
    } as ReturnType<typeof useAuth>);

    render(
      <ProtectedRoute>
        <div>content</div>
      </ProtectedRoute>,
    );

    await new Promise((r) => setTimeout(r, 50));
    expect(mockPush).not.toHaveBeenCalled();
  });
});
