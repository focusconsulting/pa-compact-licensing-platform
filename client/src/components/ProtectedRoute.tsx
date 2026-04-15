"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "src/contexts/AuthContext";

export default function ProtectedRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoading, idToken } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !idToken) {
      router.push("/login");
    }
  }, [isLoading, idToken, router]);

  if (isLoading || !idToken) {
    return null;
  }

  return <>{children}</>;
}
