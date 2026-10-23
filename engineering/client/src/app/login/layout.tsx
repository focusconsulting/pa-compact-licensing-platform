import { Metadata } from "next";

// The page itself is a client component, which cannot export metadata.
export const metadata: Metadata = { title: "Sign in" };

/** Layout for the sign-in route; exists only to set the page title. */
export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
