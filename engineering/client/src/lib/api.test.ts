import { describe, it, expect, vi, beforeEach } from "vitest";
import type { CognitoUserSession } from "amazon-cognito-identity-js";

import * as authLib from "src/lib/auth";
import { answerFetch } from "src/tests/fetch";
import { api, authFetch } from "./api";

vi.mock("src/lib/auth");

function signInWith(token: string) {
  vi.mocked(authLib.getCurrentSession).mockResolvedValue({
    getIdToken: () => ({ getJwtToken: () => token }),
  } as CognitoUserSession);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("api", () => {
  it("returns the API's body for /api/me", async () => {
    signInWith("my-token");
    answerFetch({ data: { email: "pat.morgan@example.com" } });

    const { data } = await api.GET("/api/me");

    expect(data?.data.email).toBe("pat.morgan@example.com");
  });

  it("sends the session's ID token to the API's base URL", async () => {
    signInWith("my-token");
    const fetchSpy = answerFetch({});

    await api.GET("/api/me");

    const [request] = fetchSpy.mock.calls[0] as [Request];
    expect(request.url).toBe("http://api.test/api/me");
    expect(request.headers.get("Authorization")).toBe("Bearer my-token");
  });

  it("throws when not authenticated", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);

    await expect(api.GET("/api/me")).rejects.toThrow("Not authenticated");
  });
});

describe("authFetch", () => {
  it("throws when not authenticated", async () => {
    vi.mocked(authLib.getCurrentSession).mockResolvedValue(null);

    await expect(authFetch("/api/test")).rejects.toThrow("Not authenticated");
  });

  it("sends the token with the caller's headers, method, and body", async () => {
    signInWith("token-abc");
    const fetchSpy = answerFetch({});

    await authFetch("/api/data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: '{"key":"val"}',
    });

    expect(fetchSpy).toHaveBeenCalledWith("http://api.test/api/data", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer token-abc",
      },
      body: '{"key":"val"}',
    });
  });
});

describe("without NEXT_PUBLIC_API_BASE_URL", () => {
  it("calls the page's own origin", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", undefined);
    vi.resetModules();
    const fetchSpy = answerFetch({});
    const { authFetch: relativeFetch } = await import("./api");
    signInWith("token");

    await relativeFetch("/api/test");

    expect(fetchSpy).toHaveBeenCalledWith("/api/test", expect.anything());
    vi.unstubAllEnvs();
  });
});
