"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function Register() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: displayName, email, password }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Account creation failed");
      router.replace("/dashboard");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Account creation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="card auth-card">
        <div className="brand" style={{ marginBottom: 12 }}><span className="brand-mark">FI</span><span>Forex Intelligence</span></div>
        <h1>Create an account</h1>
        <p className="safety-note">New accounts start with viewer access. An administrator must be provisioned before registration is available.</p>
        <form className="mt5-form" onSubmit={submit}>
          <label>
            Name
            <input autoComplete="name" required maxLength={100} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </label>
          <label>
            Email
            <input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label>
            Password (12 characters minimum)
            <input type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error && <p className="error-text" role="alert">{error}</p>}
          <button className="primary-button" type="submit" disabled={busy}>
            {busy ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="account-link">Already registered? <Link href="/login">Sign in</Link></p>
      </section>
    </main>
  );
}
