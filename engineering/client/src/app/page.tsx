"use client";

import ProtectedRoute from "src/components/ProtectedRoute";
import { useCurrentUser } from "src/contexts/CurrentUserContext";

function Dashboard() {
  const { user, error } = useCurrentUser();

  return (
    <div className="usa-section">
      <div className="grid-container">
        <h1>Dashboard</h1>
        {error && <p className="text-red">{error}</p>}
        {user && (
          <table className="usa-table usa-table--borderless">
            <tbody>
              <tr>
                <th>Name</th>
                <td>
                  {[user.given_name, user.family_name]
                    .filter(Boolean)
                    .join(" ") || "—"}
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
      </div>
    </div>
  );
}

/** Home page: the signed-in user's dashboard; signed-out visitors are sent to sign in. */
export default function Home() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
