import { describe, it, expect, vi, beforeEach } from "vitest";
import type { CognitoUserSession } from "amazon-cognito-identity-js";

vi.mock("src/lib/auth");

import * as authLib from "src/lib/auth";
import { authFetch } from "./api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  vi.clearAllMocks();
});

describe("authFetch", () => {
  it("throws when not authenticated", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);

    await expect(authFetch("/api/test")).rejects.toThrow("Not authenticated");
  });

  it("calls fetch with Authorization header when authenticated", async () => {
    const mockSession = {
      getIdToken: () => ({ getJwtToken: () => "my-token" }),
    } as CognitoUserSession;
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(mockSession);
    mockFetch.mockResolvedValue(new Response());

    await authFetch("/api/test");

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/test",
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer my-token" }),
      }),
    );
  });

  it("merges caller-provided headers with the auth header", async () => {
    const mockSession = {
      getIdToken: () => ({ getJwtToken: () => "token-abc" }),
    } as CognitoUserSession;
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(mockSession);
    mockFetch.mockResolvedValue(new Response());

    await authFetch("/api/test", {
      headers: { "Content-Type": "application/json" },
    });

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/test",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-abc",
          "Content-Type": "application/json",
        }),
      }),
    );
  });

  it("passes through fetch options", async () => {
    const mockSession = {
      getIdToken: () => ({ getJwtToken: () => "token" }),
    } as CognitoUserSession;
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(mockSession);
    mockFetch.mockResolvedValue(new Response());

    await authFetch("/api/data", { method: "POST", body: '{"key":"val"}' });

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/data",
      expect.objectContaining({ method: "POST", body: '{"key":"val"}' }),
    );
  });
});
