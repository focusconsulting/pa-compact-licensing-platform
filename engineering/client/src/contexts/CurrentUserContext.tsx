"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

import type { components } from "src/api/schema";
import { useAuth } from "src/contexts/AuthContext";
import { api } from "src/lib/api";

export type CurrentUser = components["schemas"]["CurrentUser"];

interface CurrentUserValue {
  user: CurrentUser | null;
  error: string | null;
}

export const CurrentUserContext = createContext<CurrentUserValue>({
  user: null,
  error: null,
});

/** Loads the signed-in user from `/api/me` once per session, for the shell and every page. */
export function CurrentUserProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const { idToken } = useAuth();
  const [value, setValue] = useState<CurrentUserValue>({
    user: null,
    error: null,
  });

  useEffect(() => {
    setValue({ user: null, error: null });
    if (!idToken) return undefined;
    let current = true;
    api
      .GET("/api/me")
      .then(({ data, response }) => {
        if (!data) throw new Error(`${response.status}`);
        if (current) setValue({ user: data.data, error: null });
      })
      .catch((e: unknown) => {
        if (current)
          setValue({
            user: null,
            error: e instanceof Error ? e.message : "Failed to load user",
          });
      });
    return () => {
      current = false;
    };
  }, [idToken]);

  return (
    <CurrentUserContext.Provider value={value}>
      {children}
    </CurrentUserContext.Provider>
  );
}

/** The signed-in user, or the error loading them; both null while loading or signed out. */
export function useCurrentUser(): CurrentUserValue {
  return useContext(CurrentUserContext);
}
