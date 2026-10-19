import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const MockCognitoUserPool = vi.hoisted(() =>
  vi.fn().mockReturnValue({ getCurrentUser: () => null }),
);

vi.mock("amazon-cognito-identity-js", () => ({
  CognitoUserPool: MockCognitoUserPool,
  CognitoUser: vi.fn(),
  AuthenticationDetails: vi.fn(),
}));

describe("user pool endpoint", () => {
  beforeEach(() => {
    vi.resetModules();
    MockCognitoUserPool.mockClear();
    vi.stubEnv("NEXT_PUBLIC_COGNITO_USER_POOL_ID", "local_licensing");
    vi.stubEnv("NEXT_PUBLIC_COGNITO_CLIENT_ID", "licensing-local-client");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("calls the configured endpoint when one is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_COGNITO_ENDPOINT_URL", "http://localhost:9229");
    const { signOut } = await import("./auth");

    signOut();

    expect(MockCognitoUserPool).toHaveBeenCalledWith({
      UserPoolId: "local_licensing",
      ClientId: "licensing-local-client",
      endpoint: "http://localhost:9229",
    });
  });

  it("leaves the endpoint to the SDK's Cognito default when unset", async () => {
    vi.stubEnv("NEXT_PUBLIC_COGNITO_ENDPOINT_URL", "");
    const { signOut } = await import("./auth");

    signOut();

    expect(MockCognitoUserPool).toHaveBeenCalledWith(
      expect.objectContaining({ endpoint: undefined }),
    );
  });
});
