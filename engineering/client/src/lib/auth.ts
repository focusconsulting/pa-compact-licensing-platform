import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
  CognitoUserSession,
} from "amazon-cognito-identity-js";

// Lazily initialized — CognitoUserPool accesses localStorage which is browser-only.
// Module-level initialization would throw during Next.js static pre-rendering.
let _userPool: CognitoUserPool | null = null;

function getUserPool(): CognitoUserPool {
  if (!_userPool) {
    _userPool = new CognitoUserPool({
      UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
      ClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
    });
  }
  return _userPool;
}

export type SignInResult =
  | { type: "success"; session: CognitoUserSession }
  | {
      type: "newPasswordRequired";
      user: CognitoUser;
      userAttributes: Record<string, string>;
    };

export function signIn(email: string, password: string): Promise<SignInResult> {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: getUserPool() });
    const authDetails = new AuthenticationDetails({
      Username: email,
      Password: password,
    });

    user.authenticateUser(authDetails, {
      onSuccess: (session) => resolve({ type: "success", session }),
      onFailure: reject,
      newPasswordRequired: (userAttributes) => {
        // Cognito rejects attempts to write back read-only attributes
        delete userAttributes.email_verified;
        delete userAttributes.email;
        resolve({ type: "newPasswordRequired", user, userAttributes });
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
