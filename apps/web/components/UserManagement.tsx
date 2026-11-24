"use client";

import { type FormEvent, type MouseEvent, useEffect, useRef, useState } from "react";
import { SearchableSelect } from "@/components/SearchableSelect";

type ManagedUser = {
  id: string;
  email: string;
  display_name: string | null;
  role: "administrator" | "viewer";
  is_active: boolean;
  created_at: string;
};

type UserDraft = {
  email: string;
  display_name: string;
  password: string;
  role: ManagedUser["role"];
};

type UserDialog =
  | { type: "create" }
  | { type: "view" | "edit" | "disable" | "enable" | "delete"; user: ManagedUser }
  | null;

const emptyDraft: UserDraft = { email: "", display_name: "", password: "", role: "viewer" };

function initials(user: ManagedUser): string {
  const name = user.display_name?.trim();
  return (name || user.email).split(/[\s@._-]+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function displayName(user: ManagedUser): string {
  return user.display_name?.trim() || user.email;
}

function formatCreatedAt(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function UserManagement() {
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [currentEmail, setCurrentEmail] = useState("");
  const [draft, setDraft] = useState<UserDraft>(emptyDraft);
  const [dialog, setDialog] = useState<UserDialog>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [success, setSuccess] = useState("");
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialogRef.current;
    if (!element) return;
    if (dialog && !element.open) element.showModal();
    if (!dialog && element.open) element.close();
  }, [dialog]);

  useEffect(() => {
    let active = true;
    Promise.all([
      fetch("/api/v1/auth/users", { cache: "no-store" }),
      fetch("/api/v1/auth/profile", { cache: "no-store" }),
    ])
      .then(async ([usersResponse, profileResponse]) => {
        const usersResult = await usersResponse.json();
        if (!usersResponse.ok) throw new Error(usersResult.detail ?? "Could not load user accounts");
        const profileResult = await profileResponse.json();
        if (!profileResponse.ok) throw new Error(profileResult.detail ?? "Could not verify administrator access");
        if (active) {
          setUsers(usersResult as ManagedUser[]);
          setCurrentEmail(String(profileResult.email).toLowerCase());
          setError("");
        }
      })
      .catch((cause) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load user accounts");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const filteredUsers = users.filter((user) => {
    const search = query.trim().toLowerCase();
    return !search || `${user.display_name ?? ""} ${user.email} ${user.role} ${user.is_active ? "active" : "disabled"}`.toLowerCase().includes(search);
  });
  const activeCount = users.filter((user) => user.is_active).length;
  const administratorCount = users.filter((user) => user.role === "administrator" && user.is_active).length;
  const disabledCount = users.length - activeCount;

  function openCreate() {
    setDraft(emptyDraft);
    setDialogError("");
    setDialog({ type: "create" });
  }

  function openEdit(user: ManagedUser) {
    setDraft({ email: user.email, display_name: user.display_name ?? "", password: "", role: user.role });
    setDialogError("");
    setDialog({ type: "edit", user });
  }

  function openFromMenu(event: MouseEvent<HTMLButtonElement>, nextDialog: NonNullable<UserDialog>) {
    event.currentTarget.closest("details")?.removeAttribute("open");
    setDialogError("");
    setDialog(nextDialog);
  }

  async function saveUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!dialog || (dialog.type !== "create" && dialog.type !== "edit")) return;
    setBusy(true);
    setDialogError("");
    setError("");
    setSuccess("");
    try {
      const creating = dialog.type === "create";
      const body: Record<string, string> = {
        email: draft.email,
        display_name: draft.display_name,
        role: draft.role,
      };
      if (creating || draft.password) body.password = draft.password;
      const response = await fetch(
        creating ? "/api/v1/auth/users" : `/api/v1/auth/users/${encodeURIComponent(dialog.user.id)}`,
        {
          method: creating ? "POST" : "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? `Could not ${creating ? "create" : "update"} this account`);
      if (creating) {
        setUsers((current) => [result as ManagedUser, ...current]);
        setSuccess(`Account created for ${result.email}. Share the temporary password securely.`);
      } else {
        setUsers((current) => current.map((user) => user.id === result.id ? result as ManagedUser : user));
        if (dialog.user.email.toLowerCase() === currentEmail) {
          setCurrentEmail(String(result.email).toLowerCase());
        }
        setSuccess(`Saved changes for ${result.email}.`);
      }
      setDialog(null);
    } catch (cause) {
      setDialogError(cause instanceof Error ? cause.message : "Could not save this account");
    } finally {
      setBusy(false);
    }
  }

  async function updateActive(user: ManagedUser, isActive: boolean) {
    setBusy(true);
    setDialogError("");
    try {
      const response = await fetch(`/api/v1/auth/users/${encodeURIComponent(user.id)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: isActive }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? "Could not update this account");
      setUsers((current) => current.map((entry) => entry.id === user.id ? result as ManagedUser : entry));
      setSuccess(`${result.email} is now ${result.is_active ? "active" : "disabled"}.`);
      setDialog(null);
    } catch (cause) {
      setDialogError(cause instanceof Error ? cause.message : "Could not update this account");
    } finally {
      setBusy(false);
    }
  }

  async function deleteUser(user: ManagedUser) {
    setBusy(true);
    setDialogError("");
    try {
      const response = await fetch(`/api/v1/auth/users/${encodeURIComponent(user.id)}`, { method: "DELETE" });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail ?? "Could not delete this account");
      }
      setUsers((current) => current.filter((entry) => entry.id !== user.id));
      setSuccess(`${user.email} was permanently deleted.`);
      setDialog(null);
    } catch (cause) {
      setDialogError(cause instanceof Error ? cause.message : "Could not delete this account");
    } finally {
      setBusy(false);
    }
  }

  const dialogUser = dialog && dialog.type !== "create" ? dialog.user : null;

  return (
    <section className="card users-page">
      <header className="users-page-header">
        <div>
          <span className="users-eyebrow">ADMINISTRATION</span>
          <h2>Users &amp; access</h2>
          <p>Manage account details, roles, and sign-in access.</p>
        </div>
        <button className="primary-button add-user-button" type="button" onClick={openCreate}>
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4v12M4 10h12" /></svg>
          Add user
        </button>
      </header>

      <div className="user-summary-grid" aria-label="User summary">
        <div className="user-summary-card"><span>Total accounts</span><strong>{loading ? "—" : users.length}</strong></div>
        <div className="user-summary-card"><span>Active</span><strong className="user-summary-positive">{loading ? "—" : activeCount}</strong></div>
        <div className="user-summary-card"><span>Administrators</span><strong>{loading ? "—" : administratorCount}</strong></div>
        <div className="user-summary-card"><span>Disabled</span><strong>{loading ? "—" : disabledCount}</strong></div>
      </div>

      <div className="user-list-toolbar">
        <div>
          <h3>All users</h3>
          <p>{loading ? "Loading accounts…" : `${filteredUsers.length} ${filteredUsers.length === 1 ? "account" : "accounts"}`}</p>
        </div>
        <label className="user-search">
          <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><path d="m13 13 4 4" /></svg>
          <input
            type="search"
            placeholder="Search users"
            aria-label="Search users"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
      </div>

      {error && <p className="error-text users-feedback" role="alert">{error}</p>}
      {success && <p className="success-text users-feedback" role="status">{success}</p>}

      <div className="user-table-wrap">
        <table className="user-table">
          <thead>
            <tr><th>Account</th><th>Role</th><th>Status</th><th>Created</th><th><span className="visually-hidden">Actions</span></th></tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => {
              const isCurrentUser = user.email.toLowerCase() === currentEmail;
              return (
                <tr key={user.id}>
                  <td data-label="Account">
                    <div className="user-account-cell">
                      <span className="user-avatar" aria-hidden="true">{initials(user)}</span>
                      <span className="user-account-text"><strong>{displayName(user)}{isCurrentUser && <small className="you-badge">YOU</small>}</strong><span>{user.email}</span></span>
                    </div>
                  </td>
                  <td data-label="Role"><span className={`user-role-badge ${user.role}`}>{user.role === "administrator" ? "Administrator" : "Viewer"}</span></td>
                  <td data-label="Status"><span className={`user-status-badge ${user.is_active ? "active" : "disabled"}`}><i />{user.is_active ? "Active" : "Disabled"}</span></td>
                  <td data-label="Created" className="user-created-date">{formatCreatedAt(user.created_at)}</td>
                  <td data-label="Actions" className="user-actions-cell">
                    <details className="user-action-menu">
                      <summary aria-label={`Actions for ${displayName(user)}`} title="Account actions">
                        <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="4" cy="10" r="1" /><circle cx="10" cy="10" r="1" /><circle cx="16" cy="10" r="1" /></svg>
                      </summary>
                      <div className="user-action-popover">
                        <button type="button" onClick={(event) => openFromMenu(event, { type: "view", user })}>View account</button>
                        {!isCurrentUser && (
                          <button
                            type="button"
                            onClick={(event) => {
                              event.currentTarget.closest("details")?.removeAttribute("open");
                              openEdit(user);
                            }}
                          >
                            Edit account
                          </button>
                        )}
                        {!isCurrentUser && (
                          <button
                            type="button"
                            onClick={(event) => openFromMenu(event, { type: user.is_active ? "disable" : "enable", user })}
                          >
                            {user.is_active ? "Disable access" : "Enable access"}
                          </button>
                        )}
                        {!isCurrentUser && <button className="destructive-action" type="button" onClick={(event) => openFromMenu(event, { type: "delete", user })}>Delete account</button>}
                      </div>
                    </details>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {!loading && filteredUsers.length === 0 && (
          <div className="users-empty-state">
            <span className="users-empty-icon">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20a6.5 6.5 0 0 1 13 0M17 8h5m-2.5-2.5v5" /></svg>
            </span>
            <strong>{query ? "No matching users" : "No users yet"}</strong>
            <span>{query ? "Try another name or email." : "Add a user to grant access to this workspace."}</span>
          </div>
        )}
      </div>
      <p className="users-footnote">Deleted accounts cannot be restored. Existing sessions may remain valid until they expire.</p>

      <dialog
        ref={dialogRef}
        className="user-modal"
        aria-labelledby="user-modal-title"
        onCancel={(event) => { event.preventDefault(); setDialog(null); }}
      >
        {dialog?.type === "create" && (
          <form onSubmit={saveUser}>
            <div className="user-modal-header">
              <span className="user-modal-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg></span>
              <div><h2 id="user-modal-title">Add a user</h2><p>Create a new account and choose its access level.</p></div>
              <button className="modal-close" type="button" aria-label="Close dialog" onClick={() => setDialog(null)}>×</button>
            </div>
            <UserFormFields draft={draft} setDraft={setDraft} creating />
            {dialogError && <p className="error-text" role="alert">{dialogError}</p>}
            <div className="user-modal-actions">
              <button className="secondary-button" type="button" onClick={() => setDialog(null)}>Cancel</button>
              <button className="primary-button" type="submit" disabled={busy}>{busy ? "Creating…" : "Create user"}</button>
            </div>
          </form>
        )}
        {dialog?.type === "edit" && dialogUser && (
          <form onSubmit={saveUser}>
            <div className="user-modal-header">
              <span className="user-modal-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m14 5 5 5M4 20l4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20Z" /></svg></span>
              <div><h2 id="user-modal-title">Edit account</h2><p>Update account details and access.</p></div>
              <button className="modal-close" type="button" aria-label="Close dialog" onClick={() => setDialog(null)}>×</button>
            </div>
            <UserFormFields draft={draft} setDraft={setDraft} />
            <p className="user-form-hint">Leave the password empty to keep the current password.</p>
            {dialogError && <p className="error-text" role="alert">{dialogError}</p>}
            <div className="user-modal-actions">
              <button className="secondary-button" type="button" onClick={() => setDialog(null)}>Cancel</button>
              <button className="primary-button" type="submit" disabled={busy}>{busy ? "Saving…" : "Save changes"}</button>
            </div>
          </form>
        )}
        {dialog?.type === "view" && dialogUser && (
          <div>
            <div className="user-modal-header">
              <span className="user-avatar large" aria-hidden="true">{initials(dialogUser)}</span>
              <div><h2 id="user-modal-title">{displayName(dialogUser)}</h2><p>{dialogUser.email}</p></div>
              <button className="modal-close" type="button" aria-label="Close dialog" onClick={() => setDialog(null)}>×</button>
            </div>
            <dl className="user-detail-list">
              <div><dt>Role</dt><dd>{dialogUser.role === "administrator" ? "Administrator" : "Viewer"}</dd></div>
              <div><dt>Account status</dt><dd>{dialogUser.is_active ? "Active" : "Disabled"}</dd></div>
              <div><dt>Created</dt><dd>{formatCreatedAt(dialogUser.created_at)}</dd></div>
            </dl>
            <div className="user-modal-actions"><button className="secondary-button" type="button" onClick={() => setDialog(null)}>Close</button></div>
          </div>
        )}
        {(dialog?.type === "disable" || dialog?.type === "enable") && dialogUser && (
          <div>
            <div className="user-modal-header">
              <span className="user-modal-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d={dialog.type === "disable" ? "M7 12h10" : "M12 7v10M7 12h10"} /></svg></span>
              <div><h2 id="user-modal-title">{dialog.type === "disable" ? "Disable account?" : "Enable account?"}</h2><p>{dialogUser.email}</p></div>
              <button className="modal-close" type="button" aria-label="Close dialog" onClick={() => setDialog(null)}>×</button>
            </div>
            <p className="user-modal-copy">{dialog.type === "disable" ? "This user will no longer be able to sign in. Existing sessions may remain valid until they expire." : "This user will be able to sign in again."}</p>
            {dialogError && <p className="error-text" role="alert">{dialogError}</p>}
            <div className="user-modal-actions">
              <button className="secondary-button" type="button" onClick={() => setDialog(null)}>Cancel</button>
              <button className={dialog.type === "disable" ? "danger-button" : "primary-button"} type="button" disabled={busy} onClick={() => updateActive(dialogUser, dialog.type === "enable")}>
                {busy ? "Updating…" : dialog.type === "disable" ? "Disable account" : "Enable account"}
              </button>
            </div>
          </div>
        )}
        {dialog?.type === "delete" && dialogUser && (
          <div>
            <div className="user-modal-header">
              <span className="user-modal-icon danger"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M10 11v6m4-6v6M6 7l1 14h10l1-14M9 7V4h6v3" /></svg></span>
              <div><h2 id="user-modal-title">Delete account?</h2><p>This permanently removes the user.</p></div>
              <button className="modal-close" type="button" aria-label="Close dialog" onClick={() => setDialog(null)}>×</button>
            </div>
            <p className="user-modal-copy">Delete <strong>{dialogUser.email}</strong>? This action cannot be undone.</p>
            {dialogError && <p className="error-text" role="alert">{dialogError}</p>}
            <div className="user-modal-actions">
              <button className="secondary-button" type="button" onClick={() => setDialog(null)}>Cancel</button>
              <button className="danger-button" type="button" disabled={busy} onClick={() => deleteUser(dialogUser)}>
                {busy ? "Deleting…" : "Delete account"}
              </button>
            </div>
          </div>
        )}
      </dialog>
    </section>
  );
}

function UserFormFields({ draft, setDraft, creating = false }: {
  draft: UserDraft;
  setDraft: (update: (current: UserDraft) => UserDraft) => void;
  creating?: boolean;
}) {
  return (
    <div className="user-modal-form">
      <label>
        Full name
        <input required maxLength={100} autoComplete="name" value={draft.display_name} onChange={(event) => setDraft((current) => ({ ...current, display_name: event.target.value }))} />
      </label>
      <label>
        Email address
        <input required type="email" autoComplete="email" value={draft.email} onChange={(event) => setDraft((current) => ({ ...current, email: event.target.value }))} />
      </label>
      <label>
        {creating ? "Temporary password" : "Reset password"}
        <input
          required={creating}
          type="password"
          autoComplete="new-password"
          minLength={12}
          maxLength={128}
          value={draft.password}
          placeholder={creating ? "At least 12 characters" : "Leave blank to keep current"}
          onChange={(event) => setDraft((current) => ({ ...current, password: event.target.value }))}
        />
      </label>
      <label>
        Access role
        <SearchableSelect
          value={draft.role}
          onChange={(value) => {
            if (value === "viewer" || value === "administrator") {
              setDraft((current) => ({ ...current, role: value }));
            }
          }}
          options={[
            { value: "viewer", label: "Viewer" },
            { value: "administrator", label: "Administrator" },
          ]}
          ariaLabel="Access role"
        />
      </label>
    </div>
  );
}
