import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
  CognitoUserSession,
  IAuthenticationCallback,
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

/** Shown as the account's name in an authenticator app. */
const TOTP_ISSUER = "PA Compact Data System";

export type SignInResult =
  | { type: "success"; session: CognitoUserSession }
  | {
      type: "newPasswordRequired";
      user: CognitoUser;
      userAttributes: Record<string, string>;
    }
  | { type: "totpSetupRequired"; user: CognitoUser; secret: string }
  | { type: "totpRequired"; user: CognitoUser };

/** Resolves a sign-in step with the session, or with the next challenge Cognito sets. */
function challengeCallbacks(
  user: CognitoUser,
  resolve: (result: SignInResult) => void,
  reject: (err: unknown) => void,
): IAuthenticationCallback {
  return {
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
    mfaSetup: () =>
      user.associateSoftwareToken({
        associateSecretCode: (secret) =>
          resolve({ type: "totpSetupRequired", user, secret }),
        onFailure: reject,
      }),
    totpRequired: () => resolve({ type: "totpRequired", user }),
  };
}

/**
 * Signs in with Cognito, using SRP unless `NEXT_PUBLIC_COGNITO_AUTH_FLOW` names
 * another flow (cognito-local has no SRP; ADR-0010). Resolves with the session,
 * or with the challenge to answer next: a new password for a user an admin
 * created, enrolling an authenticator app, or a code from it.
 */
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

    user.authenticateUser(
      authDetails,
      challengeCallbacks(user, resolve, reject),
    );
  });
}

/** Answers a new-password challenge; a user yet to enrol TOTP is then asked to. */
export function completeNewPassword(
  user: CognitoUser,
  newPassword: string,
  userAttributes: Record<string, string>,
): Promise<SignInResult> {
  return new Promise((resolve, reject) => {
    user.completeNewPasswordChallenge(
      newPassword,
      userAttributes,
      challengeCallbacks(user, resolve, reject),
    );
  });
}

/** Confirms enrolment with the first code from the authenticator app, finishing sign-in. */
export function verifyTotpSetup(
  user: CognitoUser,
  code: string,
): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    user.verifySoftwareToken(code, "Authenticator app", {
      onSuccess: resolve,
      onFailure: reject,
    });
  });
}

/** Answers a TOTP challenge with the code from the authenticator app. */
export function answerTotp(
  user: CognitoUser,
  code: string,
): Promise<CognitoUserSession> {
  return new Promise((resolve, reject) => {
    user.sendMFACode(
      code,
      { onSuccess: resolve, onFailure: reject },
      "SOFTWARE_TOKEN_MFA",
    );
  });
}

/** The `otpauth://` URI an authenticator app enrols from (Key URI Format). */
export function totpUri(email: string, secret: string): string {
  const label = encodeURIComponent(`${TOTP_ISSUER}:${email}`);
  const issuer = encodeURIComponent(TOTP_ISSUER);
  return `otpauth://totp/${label}?secret=${secret}&issuer=${issuer}`;
}

/** Signs the current user out on this device, clearing the stored session. */
export function signOut(): void {
  getUserPool().getCurrentUser()?.signOut();
}

/** The stored session if it is still valid (refreshing it if needed), otherwise null. */
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
