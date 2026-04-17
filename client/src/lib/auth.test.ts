import { describe, it, expect, vi, beforeEach } from "vitest";
import type { CognitoUserSession } from "amazon-cognito-identity-js";

const mockGetCurrentUser = vi.hoisted(() => vi.fn());
const mockAuthenticateUser = vi.hoisted(() => vi.fn());
const mockCompleteNewPasswordChallenge = vi.hoisted(() => vi.fn());

vi.mock("amazon-cognito-identity-js", () => ({
  CognitoUserPool: vi.fn().mockReturnValue({ getCurrentUser: mockGetCurrentUser }),
  CognitoUser: vi.fn().mockImplementation(() => ({
    authenticateUser: mockAuthenticateUser,
    completeNewPasswordChallenge: mockCompleteNewPasswordChallenge,
    signOut: vi.fn(),
  })),
  AuthenticationDetails: vi.fn(),
}));

import {
  signIn,
  completeNewPassword,
  signOut,
  getCurrentSession,
} from "./auth";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("signIn", () => {
  it("resolves with success on successful authentication", async () => {
    const mockSession = {} as CognitoUserSession;
    mockAuthenticateUser.mockImplementation((_: unknown, callbacks: Record<string, Function>) => {
      callbacks.onSuccess(mockSession);
    });

    const result = await signIn("test@example.com", "password");

    expect(result).toEqual({ type: "success", session: mockSession });
  });

  it("resolves with newPasswordRequired and strips read-only attributes", async () => {
    const rawAttrs = {
      phone_number: "+1234567890",
      email_verified: "true",
      email: "test@example.com",
    };
    mockAuthenticateUser.mockImplementation((_: unknown, callbacks: Record<string, Function>) => {
      callbacks.newPasswordRequired({ ...rawAttrs });
    });

    const result = await signIn("test@example.com", "password");

    expect(result.type).toBe("newPasswordRequired");
    const attrs = (result as { type: "newPasswordRequired"; userAttributes: Record<string, string> }).userAttributes;
    expect(attrs).not.toHaveProperty("email_verified");
    expect(attrs).not.toHaveProperty("email");
    expect(attrs.phone_number).toBe("+1234567890");
  });

  it("rejects when authentication fails", async () => {
    const error = new Error("Incorrect username or password");
    mockAuthenticateUser.mockImplementation((_: unknown, callbacks: Record<string, Function>) => {
      callbacks.onFailure(error);
    });

    await expect(signIn("test@example.com", "wrong")).rejects.toThrow(
      "Incorrect username or password",
    );
  });
});

describe("completeNewPassword", () => {
  it("resolves with session on success", async () => {
    const mockSession = {} as CognitoUserSession;
    const mockUser = {
      completeNewPasswordChallenge: vi.fn().mockImplementation(
        (_: unknown, __: unknown, callbacks: Record<string, Function>) => {
          callbacks.onSuccess(mockSession);
        },
      ),
    };

    const result = await completeNewPassword(mockUser as never, "NewPass123!", {});

    expect(result).toBe(mockSession);
  });

  it("rejects on failure", async () => {
    const error = new Error("Password does not conform to policy");
    const mockUser = {
      completeNewPasswordChallenge: vi.fn().mockImplementation(
        (_: unknown, __: unknown, callbacks: Record<string, Function>) => {
          callbacks.onFailure(error);
        },
      ),
    };

    await expect(completeNewPassword(mockUser as never, "weak", {})).rejects.toThrow(
      "Password does not conform to policy",
    );
  });
});

describe("signOut", () => {
  it("calls signOut on the current user", () => {
    const mockUserSignOut = vi.fn();
    mockGetCurrentUser.mockReturnValue({ signOut: mockUserSignOut });

    signOut();

    expect(mockUserSignOut).toHaveBeenCalled();
  });

  it("does nothing when there is no current user", () => {
    mockGetCurrentUser.mockReturnValue(null);

    expect(() => signOut()).not.toThrow();
  });
});

describe("getCurrentSession", () => {
  it("returns null when there is no current user", async () => {
    mockGetCurrentUser.mockReturnValue(null);

    const result = await getCurrentSession();

    expect(result).toBeNull();
  });

  it("returns a valid session", async () => {
    const mockSession = { isValid: () => true } as CognitoUserSession;
    mockGetCurrentUser.mockReturnValue({
      getSession: vi.fn().mockImplementation((cb: Function) => cb(null, mockSession)),
    });

    const result = await getCurrentSession();

    expect(result).toBe(mockSession);
  });

  it("returns null when the session is invalid", async () => {
    const mockSession = { isValid: () => false } as CognitoUserSession;
    mockGetCurrentUser.mockReturnValue({
      getSession: vi.fn().mockImplementation((cb: Function) => cb(null, mockSession)),
    });

    const result = await getCurrentSession();

    expect(result).toBeNull();
  });

  it("returns null when getSession returns an error", async () => {
    mockGetCurrentUser.mockReturnValue({
      getSession: vi.fn().mockImplementation((cb: Function) =>
        cb(new Error("Session expired"), null),
      ),
    });

    const result = await getCurrentSession();

    expect(result).toBeNull();
  });
});
