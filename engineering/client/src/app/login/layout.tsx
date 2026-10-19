import { Metadata } from "next";

// The page itself is a client component, which cannot export metadata.
export const metadata: Metadata = { title: "Sign in" };

export default function LoginLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
