"use client";

import { type FormEvent, useEffect, useState } from "react";

type Profile = { email: string; display_name: string | null; role: string };

export function AccountSettings() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    fetch("/api/v1/auth/profile", { cache: "no-store" })
      .then(async (response) => {
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail ?? "Could not load your profile");
        const current = result as Profile;
        setProfile(current);
        setEmail(current.email);
        setDisplayName(current.display_name ?? "");
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load your profile"));
  }, []);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      const response = await fetch("/api/v1/auth/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, display_name: displayName }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not update your profile");
      setProfile(result as Profile);
      setEmail(result.email);
      setDisplayName(result.display_name ?? "");
      setSuccess("Profile updated.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not update your profile");
    } finally {
      setBusy(false);
    }
  }

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      if (newPassword !== confirmPassword) throw new Error("New passwords do not match");
      const response = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not change your password");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess("Password changed successfully.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not change your password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card panel account-panel">
        <h2>Your profile</h2>
        <form className="account-form" onSubmit={saveProfile}>
          <label>
            Display name
            <input required maxLength={100} autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </label>
          <label>
            Email
            <input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <p className="account-role">Account role: <strong>{profile?.role ?? "…"}</strong></p>
          <button className="primary-button" type="submit" disabled={busy || !profile}>Save profile</button>
        </form>
      </section>
      <section className="card panel account-panel">
        <h2>Change password</h2>
        <form className="account-form" onSubmit={changePassword}>
          <label>
            Current password
            <input type="password" autoComplete="current-password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} />
          </label>
          <label>
            New password (12 characters minimum)
            <input type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          </label>
          <label>
            Confirm new password
            <input type="password" autoComplete="new-password" minLength={12} maxLength={128} required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
          </label>
          <button className="primary-button" type="submit" disabled={busy}>Update password</button>
        </form>
      </section>
      {error && <p className="error-text account-feedback" role="alert">{error}</p>}
      {success && <p className="success-text account-feedback" role="status">{success}</p>}
    </>
  );
}
