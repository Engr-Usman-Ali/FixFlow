// System Administrator: user access (FR-102). Every change is audited and takes effect at the next sign-in.
import { KeyRound, Plus, Search, Unlock } from "lucide-react";
import { FormEvent, useState } from "react";
import { userApi } from "../../api/services";
import ConfirmDialog from "../../components/common/ConfirmDialog";
import Modal from "../../components/common/Modal";
import PageHeader from "../../components/common/PageHeader";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { useDebounce } from "../../hooks/useDebounce";
import { ROLES } from "../../types";
import type { Role, User } from "../../types";
import { formatDateTime, passwordProblem } from "../../utils/format";

type Pending = { user: User; kind: "role"; role: Role } | { user: User; kind: "active" };

export default function UsersPage() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<Role | "">("");
  const q = useDebounce(search, 300);
  const { data, loading, error, reload } = useAsync(() => userApi.list({ q, role: roleFilter }), [q, roleFilter]);

  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "Employee" as Role });
  const [formError, setFormError] = useState("");
  const [pending, setPending] = useState<Pending | null>(null);
  const [resetFor, setResetFor] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resetError, setResetError] = useState("");

  async function create(e: FormEvent) {
    e.preventDefault();
    const problem = passwordProblem(form.password);
    if (problem) return setFormError(problem);
    setFormError("");
    try {
      await userApi.create(form);
      toast(`${form.name} can now sign in as ${form.role}`);
      setAdding(false);
      setForm({ name: "", email: "", password: "", role: "Employee" });
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  async function applyPending() {
    if (!pending) return;
    if (pending.kind === "role") await userApi.update(pending.user.id, { role: pending.role });
    else await userApi.update(pending.user.id, { is_active: !pending.user.is_active });
    toast("User updated");
    reload();
  }

  async function resetPassword(e: FormEvent) {
    e.preventDefault();
    if (!resetFor) return;
    const problem = passwordProblem(newPassword);
    if (problem) return setResetError(problem);
    try {
      await userApi.resetPassword(resetFor.id, newPassword);
      toast(`Password reset for ${resetFor.name}. Share it with them privately.`);
      setResetFor(null);
      setNewPassword("");
      reload();
    } catch (err) {
      setResetError((err as Error).message);
    }
  }

  async function unlock(u: User) {
    try {
      await userApi.unlock(u.id);
      toast(`${u.name} is unlocked`);
      reload();
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }

  return (
    <>
      <PageHeader
        title="Users"
        subtitle="Control who can sign in to your company and what role they have."
        actions={<button className="btn btn-primary" onClick={() => { setFormError(""); setAdding(true); }}><Plus size={16} /> Add user</button>}
      />
      <div className="card filters-inline">
        <label className="search-field">
          <Search size={16} aria-hidden="true" />
          <input type="search" placeholder="Search by name or email" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search users" />
        </label>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as Role | "")} aria-label="Role">
          <option value="">All roles</option>
          {ROLES.map((r) => <option key={r}>{r}</option>)}
        </select>
      </div>

      {loading && !data ? <Loading /> : error || !data ? <ErrorState message={error ?? "Could not load users."} onRetry={reload} /> : data.length === 0 ? (
        <EmptyState title="No users match" text="Clear the search to see everyone." />
      ) : (
        <div className="card flush table-wrap">
          <table className="table">
            <thead><tr><th>Name</th><th>Role</th><th>Status</th><th>Last sign-in</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>
              {data.map((u) => {
                const isMe = u.id === me?.id;
                return (
                  <tr key={u.id} className={u.is_active ? "" : "row-muted"}>
                    <td>
                      <span className="row-title">{u.name}{isMe && <span className="muted small"> (you)</span>}</span>
                      <span className="muted small">{u.email}</span>
                    </td>
                    <td>
                      <select value={u.role} disabled={isMe} aria-label={`Role for ${u.name}`}
                        onChange={(e) => setPending({ user: u, kind: "role", role: e.target.value as Role })}>
                        {ROLES.map((r) => <option key={r}>{r}</option>)}
                      </select>
                    </td>
                    <td className="nowrap">
                      {u.is_active ? <span className="badge status-resolved">Active</span> : <span className="badge status-closed">Deactivated</span>}
                      {u.is_locked && <span className="badge status-rejected">Locked</span>}
                    </td>
                    <td className="nowrap small">{u.last_login_at ? formatDateTime(u.last_login_at) : <span className="muted">Never</span>}</td>
                    <td className="row-actions">
                      {u.is_locked && (
                        <button className="icon-btn" title="Unlock" aria-label={`Unlock ${u.name}`} onClick={() => unlock(u)}><Unlock size={17} /></button>
                      )}
                      <button className="icon-btn" title="Reset password" aria-label={`Reset password for ${u.name}`}
                        onClick={() => { setResetError(""); setNewPassword(""); setResetFor(u); }}><KeyRound size={17} /></button>
                      <button className="btn btn-secondary btn-small" disabled={isMe} onClick={() => setPending({ user: u, kind: "active" })}>
                        {u.is_active ? "Deactivate" : "Reactivate"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {adding && (
        <Modal title="Add user" onClose={() => setAdding(false)}>
          <form onSubmit={create} className="stack-form">
            <label className="field"><span>Full name</span>
              <input required minLength={2} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
            <label className="field"><span>Email</span>
              <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
            <label className="field"><span>Temporary password</span>
              <input required type="password" autoComplete="new-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              <small className="muted">At least 8 characters with uppercase, lowercase and a number. They can change it in My profile.</small></label>
            <label className="field"><span>Role</span>
              <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
                {ROLES.map((r) => <option key={r}>{r}</option>)}
              </select></label>
            {formError && <p className="field-error" role="alert">{formError}</p>}
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setAdding(false)}>Cancel</button>
              <button className="btn btn-primary">Create account</button>
            </div>
          </form>
        </Modal>
      )}

      {pending && (
        <ConfirmDialog
          title={pending.kind === "role" ? "Change role?" : pending.user.is_active ? "Deactivate user?" : "Reactivate user?"}
          message={
            pending.kind === "role"
              ? `${pending.user.name} will become ${pending.role}. They are signed out and get the new permissions at their next sign-in.`
              : pending.user.is_active
                ? `${pending.user.name} will be signed out and cannot sign in until reactivated. Their history stays.`
                : `${pending.user.name} will be able to sign in again.`
          }
          confirmLabel={pending.kind === "role" ? "Change role" : pending.user.is_active ? "Deactivate" : "Reactivate"}
          danger={pending.kind === "active" && pending.user.is_active}
          onConfirm={applyPending}
          onClose={() => { setPending(null); reload(); }}
        />
      )}

      {resetFor && (
        <Modal title={`Reset password · ${resetFor.name}`} onClose={() => setResetFor(null)}>
          <form onSubmit={resetPassword} className="stack-form">
            <p className="muted">This signs them out everywhere and unlocks the account.</p>
            <label className="field"><span>New temporary password</span>
              <input required type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></label>
            {resetError && <p className="field-error" role="alert">{resetError}</p>}
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setResetFor(null)}>Cancel</button>
              <button className="btn btn-primary">Reset password</button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
