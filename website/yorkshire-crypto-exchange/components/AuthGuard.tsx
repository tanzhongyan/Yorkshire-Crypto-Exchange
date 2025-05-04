"use client";

import { useAuth } from "./AuthProvider";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getCookie } from "@/lib/cookies";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isInitializing } = useAuth();
  const router = useRouter();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    // Don't check until initialization is complete
    if (!isInitializing) {
      const storedToken = getCookie("jwt_token");
      if (!storedToken || !isAuthenticated) {
        router.replace("/login");
      } else {
        setChecking(false);
      }
    }
  }, [isAuthenticated, isInitializing, router]);

  // Return null during both internal checking and auth provider initialization
  if (isInitializing || checking) return null;

  return children;
}
