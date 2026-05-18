"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "src/components/ProtectedRoute";
import { useAuth } from "src/contexts/AuthContext";
import { authFetch } from "src/lib/api";
import { Button } from "@trussworks/react-uswds";

interface CurrentUser {
  id: number;
  email: string;
  given_name: string | null;
  family_name: string | null;
  role: string;
  state_code: string | null;
  is_active: boolean;
}

function Dashboard() {
  const { signOut } = useAuth();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch("/api/me")
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json() as Promise<CurrentUser>;
      })
      .then(setUser)
      .catch((e: unknown) =>
        setError(e instanceof Error ? e.message : "Failed to load user"),
      );
  }, []);

  return (
    <main className="usa-section">
      <div className="grid-container">
        <h2 className="usa-header--basic">Dashboard</h2>
        {error && <p className="text-red">{error}</p>}
        {user && (
          <table className="usa-table usa-table--borderless">
            <tbody>
              <tr>
                <th>Name</th>
                <td>
                  {[user.given_name, user.family_name].filter(Boolean).join(" ") || "—"}
                </td>
              </tr>
              <tr>
                <th>Email</th>
                <td>{user.email}</td>
              </tr>
              <tr>
                <th>Role</th>
                <td>{user.role}</td>
              </tr>
              {user.state_code && (
                <tr>
                  <th>State</th>
                  <td>{user.state_code}</td>
                </tr>
              )}
              <tr>
                <th>Status</th>
                <td>{user.is_active ? "Active" : "Inactive"}</td>
              </tr>
            </tbody>
          </table>
        )}
        <Button type="button" onClick={signOut}>
          Sign out
        </Button>
      </div>
    </main>
  );
}

export default function Home() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
