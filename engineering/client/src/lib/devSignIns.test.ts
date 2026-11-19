import { describe, expect, it, vi } from "vitest";

import { answerFetch } from "src/tests/fetch";
import { listMockUsers } from "./devSignIns";

describe("listMockUsers", () => {
  it("asks the Cognito mock for the pool's users, and returns their emails in order", async () => {
    vi.stubEnv("NEXT_PUBLIC_COGNITO_ENDPOINT_URL", "http://cognito.test");
    vi.stubEnv("NEXT_PUBLIC_COGNITO_USER_POOL_ID", "local_licensing");
    const fetchSpy = answerFetch({
      Users: [
        { Username: "sam.submitted@demo.example" },
        { Username: "avery.active@demo.example" },
      ],
    });

    const emails = await listMockUsers();

    expect(emails).toEqual([
      "avery.active@demo.example",
      "sam.submitted@demo.example",
    ]);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://cognito.test/");
    expect(init.headers).toMatchObject({
      "X-Amz-Target": "AWSCognitoIdentityProviderService.ListUsers",
    });
    expect(init.body).toBe('{"UserPoolId":"local_licensing"}');
    vi.unstubAllEnvs();
  });

  it("fails when the endpoint refuses, as deployed Cognito would", async () => {
    answerFetch({ __type: "NotAuthorizedException" }, 400);

    await expect(listMockUsers()).rejects.toThrow("400");
  });
});
