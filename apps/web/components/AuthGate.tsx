"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

type AuthState = "checking" | "authenticated" | "unavailable";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [state, setState] = useState<AuthState>("checking");
  const [verifiedPath, setVerifiedPath] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (pathname === "/login" || pathname === "/register") return;

    let active = true;
    fetch("/api/v1/auth/me", { cache: "no-store" })
      .then((response) => {
        if (!active) return;
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) throw new Error("Unable to verify your sign-in");
        setState("authenticated");
        setVerifiedPath(pathname);
      })
      .catch(() => {
        if (active) setState("unavailable");
      });

    return () => {
      active = false;
    };
  }, [attempt, pathname, router]);

  if (pathname === "/login" || pathname === "/register" || (state === "authenticated" && verifiedPath === pathname)) return children;
  if (state === "unavailable" && verifiedPath === pathname) {
    return (
      <main className="auth-screen">
        <section className="card auth-card">
          <h1>Sign-in service unavailable</h1>
          <p className="error-text">Could not verify your session. Check that the API is running, then retry.</p>
          <button className="primary-button" onClick={() => setAttempt((value) => value + 1)}>Retry</button>
        </section>
      </main>
    );
  }
  return <main className="auth-screen"><p>Checking your session…</p></main>;
}
