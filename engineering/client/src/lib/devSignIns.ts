/**
 * The users in the local Cognito mock, for the sign-in page's development-only
 * list (ADR-0020). Deployed Cognito refuses this call without AWS credentials,
 * and a build for a deployed environment does not include this module.
 */
export async function listMockUsers(): Promise<string[]> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_COGNITO_ENDPOINT_URL}/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.ListUsers",
      },
      body: JSON.stringify({
        UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
      }),
    },
  );
  if (!response.ok) throw new Error(`${response.status}`);
  const { Users } = (await response.json()) as {
    Users: { Username: string }[];
  };
  return Users.map((user) => user.Username).sort();
}
