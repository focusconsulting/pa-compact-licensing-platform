"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { CognitoUser, CognitoUserSession } from "amazon-cognito-identity-js";
import {
  answerTotp as cognitoAnswerTotp,
  completeNewPassword as cognitoCompleteNewPassword,
  getCurrentSession,
  signIn as cognitoSignIn,
  signOut as cognitoSignOut,
  SignInResult,
  verifyTotpSetup as cognitoVerifyTotpSetup,
} from "src/lib/auth";

interface AuthState {
  isLoading: boolean;
  idToken: string | null;
  email: string | null;
}

interface AuthContextValue extends AuthState {
  signIn: (email: string, password: string) => Promise<SignInResult>;
  completeNewPassword: (
    user: CognitoUser,
    newPassword: string,
    userAttributes: Record<string, string>,
  ) => Promise<SignInResult>;
  verifyTotpSetup: (user: CognitoUser, code: string) => Promise<void>;
  answerTotp: (user: CognitoUser, code: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function sessionToState(
  session: CognitoUserSession,
): Omit<AuthState, "isLoading"> {
  return {
    idToken: session.getIdToken().getJwtToken(),
    email: session.getIdToken().payload.email as string,
  };
}

/** Holds the signed-in user's session, restoring it on load, and exposes sign-in and sign-out. */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    idToken: null,
    email: null,
  });

  // On mount, attempt to restore session from tokens stored by the Cognito SDK
  useEffect(() => {
    getCurrentSession()
      .then((session) => {
        setState(
          session
            ? { isLoading: false, ...sessionToState(session) }
            : { isLoading: false, idToken: null, email: null },
        );
      })
      .catch(() => setState({ isLoading: false, idToken: null, email: null }));
  }, []);

  const signedIn = useCallback((session: CognitoUserSession): void => {
    setState({ isLoading: false, ...sessionToState(session) });
  }, []);

  const signIn = useCallback(
    async (email: string, password: string): Promise<SignInResult> => {
      const result = await cognitoSignIn(email, password);
      if (result.type === "success") signedIn(result.session);
      return result;
    },
    [signedIn],
  );

  const completeNewPassword = useCallback(
    async (
      user: CognitoUser,
      newPassword: string,
      userAttributes: Record<string, string>,
    ): Promise<SignInResult> => {
      const result = await cognitoCompleteNewPassword(
        user,
        newPassword,
        userAttributes,
      );
      if (result.type === "success") signedIn(result.session);
      return result;
    },
    [signedIn],
  );

  const verifyTotpSetup = useCallback(
    async (user: CognitoUser, code: string): Promise<void> => {
      signedIn(await cognitoVerifyTotpSetup(user, code));
    },
    [signedIn],
  );

  const answerTotp = useCallback(
    async (user: CognitoUser, code: string): Promise<void> => {
      signedIn(await cognitoAnswerTotp(user, code));
    },
    [signedIn],
  );

  const signOut = useCallback((): void => {
    cognitoSignOut();
    setState({ isLoading: false, idToken: null, email: null });
  }, []);

  // Memoised so consumers re-render only when the auth state changes.
  const value = useMemo(
    () => ({
      ...state,
      signIn,
      completeNewPassword,
      verifyTotpSetup,
      answerTotp,
      signOut,
    }),
    [state, signIn, completeNewPassword, verifyTotpSetup, answerTotp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** The current auth state and actions; must be used inside `AuthProvider`. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
