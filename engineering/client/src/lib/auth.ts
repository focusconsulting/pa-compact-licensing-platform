import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
  CognitoUserSession,
} from "amazon-cognito-identity-js";

// Lazily initialized — CognitoUserPool accesses localStorage which is browser-only.
// Module-level initialization would throw during Next.js static pre-rendering.
let userPool: CognitoUserPool | null = null;

function getUserPool(): CognitoUserPool {
  if (!userPool) {
    userPool = new CognitoUserPool({
      UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
      ClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
      // Unset in AWS, so the SDK calls Cognito; the local stack points it at the Cognito mock.
      endpoint: process.env.NEXT_PUBLIC_COGNITO_ENDPOINT_URL || undefined,
    });
  }
  return userPool;
}

export type SignInResult =
  | { type: "success"; session: CognitoUserSession }
  | {
      type: "newPasswordRequired";
      user: CognitoUser;
      userAttributes: Record<string, string>;
    };

// SRP unless NEXT_PUBLIC_COGNITO_AUTH_FLOW names another flow: cognito-local has no SRP (ADR-0010).
export function signIn(email: string, password: string): Promise<SignInResult> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getUserPool() });
    user.setAuthenticationFlowType(
      process.env.NEXT_PUBLIC_COGNITO_AUTH_FLOW || "USER_SRP_AUTH",
    );
    const authDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    user.authenticateUser(authDetails, {
      onSuccess: (session) => resolve({ type: "success", session }),
      onFailure: reject,
      newPasswordRequired: (userAttributes) => {
        // Cognito rejects attempts to write back read-only attributes
        const {
          email_verified: readOnlyEmailVerified,
          email: readOnlyEmail,
          ...writable
        } = userAttributes as Record<string, string>;
        resolve({
          type: "newPasswordRequired",
          user,
          userAttributes: writable,
        });
      },
    });
  });
}

export function completeNewPassword(
  user: CognitoUser,
  newPassword: string,
  userAttributes: Record<string, string>,
): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    user.completeNewPasswordChallenge(newPassword, userAttributes, {
      onSuccess: resolve,
      onFailure: reject,
    });
  });
}

export function signOut(): void {
  getUserPool().getCurrentUser()?.signOut();
}

export function getCurrentSession(): Promise<CognitoUserSession | null> {
  return new Promise((resolve) => {
    const user = getUserPool().getCurrentUser();
    if (!user) {
      resolve(null);
      return;
    }
    user.getSession((err: Error | null, session: CognitoUserSession | null) => {
      if (err || !session?.isValid()) {
        resolve(null);
      } else {
        resolve(session);
      }
    });
  });
}
