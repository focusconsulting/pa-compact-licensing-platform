import { Metadata } from "next";

// The page itself is a client component, which cannot export metadata. The PA's
// name is known only once the page has loaded them, so the title names the page.
export const metadata: Metadata = { title: "A PA's Compact Privileges" };

/** Layout for a PA's public page; exists only to set the page title. */
export default function PractitionerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
