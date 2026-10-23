/**
 * @file Replaces `src/lib/auth` in Storybook (see `main.ts`): every story is
 * signed in, so pages render without Cognito. The API calls go to the
 * generated MSW mocks, which ignore the token.
 */
import type { CognitoUserSession } from "amazon-cognito-identity-js";
import type * as auth from "src/lib/auth";

const session = {
  isValid: () => true,
  getIdToken: () => ({
    getJwtToken: () => "storybook-token",
    payload: { email: "pat.morgan@example.com" },
  }),
} as unknown as CognitoUserSession;

export const getCurrentSession: typeof auth.getCurrentSession = () =>
  Promise.resolve(session);

export const signIn: typeof auth.signIn = () =>
  Promise.resolve({ type: "success", session } as const);

export const completeNewPassword: typeof auth.completeNewPassword = () =>
  Promise.resolve(session);

export const signOut: typeof auth.signOut = () => {};
