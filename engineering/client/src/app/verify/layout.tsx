import { Metadata } from "next";

// The page itself is a client component, which cannot export metadata.
export const metadata: Metadata = { title: "Look up a Compact Privilege" };

/** Layout for public verification; exists only to set the page title. */
export default function VerifyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
