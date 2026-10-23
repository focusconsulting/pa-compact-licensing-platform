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
  completeNewPassword as cognitoCompleteNewPassword,
  getCurrentSession,
  signIn as cognitoSignIn,
  signOut as cognitoSignOut,
  SignInResult,
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
  ) => Promise<void>;
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

  const signIn = useCallback(
    async (email: string, password: string): Promise<SignInResult> => {
      const result = await cognitoSignIn(email, password);
      if (result.type === "success") {
        setState({ isLoading: false, ...sessionToState(result.session) });
      }
      return result;
    },
    [],
  );

  const completeNewPassword = useCallback(
    async (
      user: CognitoUser,
      newPassword: string,
      userAttributes: Record<string, string>,
    ): Promise<void> => {
      const session = await cognitoCompleteNewPassword(
        user,
        newPassword,
        userAttributes,
      );
      setState({ isLoading: false, ...sessionToState(session) });
    },
    [],
  );

  const signOut = useCallback((): void => {
    cognitoSignOut();
    setState({ isLoading: false, idToken: null, email: null });
  }, []);

  // Memoised so consumers re-render only when the auth state changes.
  const value = useMemo(
    () => ({ ...state, signIn, completeNewPassword, signOut }),
    [state, signIn, completeNewPassword, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** The current auth state and actions; must be used inside `AuthProvider`. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
