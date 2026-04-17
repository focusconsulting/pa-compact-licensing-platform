import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import type { CognitoUserSession } from "amazon-cognito-identity-js";

vi.mock("src/lib/auth");

import * as authLib from "src/lib/auth";
import { AuthProvider, useAuth } from "./AuthContext";

function makeSession(token: string, email: string): CognitoUserSession {
  return {
    getIdToken: () => ({
      getJwtToken: () => token,
      payload: { email },
    }),
  } as unknown as CognitoUserSession;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AuthProvider", () => {
  it("starts in loading state", () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    expect(result.current.isLoading).toBe(true);
  });

  it("restores session from tokens on mount", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(
      makeSession("restored-token", "user@example.com"),
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.idToken).toBe("restored-token");
    expect(result.current.email).toBe("user@example.com");
  });

  it("sets null state when no session exists on mount", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.idToken).toBeNull();
    expect(result.current.email).toBeNull();
  });

  it("sets null state when getCurrentSession throws", async () => {
    vi.mocked(authLib.getCurrentSession).mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.idToken).toBeNull();
  });

  it("updates state after successful signIn", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);
    vi.mocked(authLib.signIn).mockResolvedValue({
      type: "success",
      session: makeSession("new-token", "user@example.com"),
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.signIn("user@example.com", "password");
    });

    expect(result.current.idToken).toBe("new-token");
    expect(result.current.email).toBe("user@example.com");
  });

  it("does not update state when signIn returns newPasswordRequired", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);
    vi.mocked(authLib.signIn).mockResolvedValue({
      type: "newPasswordRequired",
      user: {} as never,
      userAttributes: {},
    });

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.signIn("user@example.com", "password");
    });

    expect(result.current.idToken).toBeNull();
  });

  it("updates state after completeNewPassword", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);
    vi.mocked(authLib.completeNewPassword).mockResolvedValue(
      makeSession("final-token", "user@example.com"),
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.completeNewPassword({} as never, "NewPass123!", {});
    });

    expect(result.current.idToken).toBe("final-token");
  });

  it("clears state on signOut", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(
      makeSession("active-token", "user@example.com"),
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.idToken).toBe("active-token"));

    act(() => {
      result.current.signOut();
    });

    expect(result.current.idToken).toBeNull();
    expect(result.current.email).toBeNull();
  });
});

describe("useAuth", () => {
  it("throws when used outside AuthProvider", () => {
    expect(() => renderHook(() => useAuth())).toThrow(
      "useAuth must be used within AuthProvider",
    );
  });
});
