import { Metadata } from "next";

// The page itself is a client component, which cannot export metadata.
export const metadata: Metadata = { title: "Dashboard" };

/** Layout for the dashboard; exists only to set the page title. */
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
