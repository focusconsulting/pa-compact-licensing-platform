"use client";

import ProtectedRoute from "src/components/ProtectedRoute";
import { useCurrentUser } from "src/contexts/CurrentUserContext";
import { portalFor } from "src/lib/navigation";
import PaDashboard from "./PaDashboard";

function Dashboard() {
  const { user, error } = useCurrentUser();

  if (user && portalFor(user.permissions) === "pa") return <PaDashboard />;

  return (
    <div className="usa-section">
      <div className="grid-container">
        <h1>Dashboard</h1>
        {error && <p className="text-red">{error}</p>}
        {user && (
          <table className="usa-table usa-table--borderless">
            <tbody>
              <tr>
                <th scope="row">Name</th>
                <td>
                  {[user.given_name, user.family_name]
                    .filter(Boolean)
                    .join(" ") || "—"}
                </td>
              </tr>
              <tr>
                <th scope="row">Email</th>
                <td>{user.email}</td>
              </tr>
              <tr>
                <th scope="row">Role</th>
                <td>{user.role}</td>
              </tr>
              {user.state_code && (
                <tr>
                  <th scope="row">State</th>
                  <td>{user.state_code}</td>
                </tr>
              )}
              <tr>
                <th scope="row">Status</th>
                <td>{user.is_active ? "Active" : "Inactive"}</td>
              </tr>
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

/** The signed-in user's dashboard; signed-out visitors are sent to sign in. */
export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Dashboard />
    </ProtectedRoute>
  );
}
