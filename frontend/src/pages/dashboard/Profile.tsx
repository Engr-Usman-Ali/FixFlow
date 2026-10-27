import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../../api/services";
import ConfirmDialog from "../../components/common/ConfirmDialog";
import PageHeader from "../../components/common/PageHeader";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { formatDateTime, passwordProblem } from "../../utils/format";

export default function Profile() {
  const { user, setUser, applySession, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [name, setName] = useState(user?.name ?? "");
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwError, setPwError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmOut, setConfirmOut] = useState(false);

  if (!user) return null;

  async function saveName(e: FormEvent) {
    e.preventDefault();
    try {
      setUser(await authApi.updateProfile(name));
      toast("Name updated");
    } catch (err) {
      toast((err as Error).message, "error");
    }
  }

  async function changePassword(e: FormEvent) {
    e.preventDefault();
    setPwError("");
    const problem = passwordProblem(pw.next);
    if (problem) return setPwError(problem);
    if (pw.next !== pw.confirm) return setPwError("The new passwords do not match.");
    setBusy(true);
    try {
      applySession(await authApi.changePassword(pw.current, pw.next));
      setPw({ current: "", next: "", confirm: "" });
      toast("Password changed. Other devices have been signed out.");
    } catch (err) {
      setPwError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="My profile" subtitle="Your account details and password." />
      <div className="two-col">
        <section className="card">
          <h3>Account</h3>
          <dl className="facts">
            <div><dt>Email</dt><dd>{user.email}</dd></div>
            <div><dt>Role</dt><dd>{user.role}</dd></div>
            <div><dt>Company</dt><dd>{user.organization.name}</dd></div>
            <div><dt>Member since</dt><dd>{formatDateTime(user.created_at)}</dd></div>
          </dl>
          <form onSubmit={saveName} className="stack-form">
            <label className="field"><span>Display name</span>
              <input required minLength={2} maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
            <button className="btn btn-secondary" disabled={name.trim() === user.name || name.trim().length < 2}>Save name</button>
          </form>
          <hr className="divider" />
          <h3>Permissions</h3>
          <p className="muted small">What your role lets you do. Ask your System Administrator if you need more.</p>
          <ul className="perm-list">{user.permissions.map((p) => <li key={p}><code>{p}</code></li>)}</ul>
        </section>

        <section className="card">
          <h3>Change password</h3>
          <form onSubmit={changePassword}>
            <label className="field"><span>Current password</span>
              <input type="password" required autoComplete="current-password" value={pw.current}
                onChange={(e) => setPw({ ...pw, current: e.target.value })} /></label>
            <label className="field"><span>New password</span>
              <input type="password" required autoComplete="new-password" value={pw.next}
                onChange={(e) => setPw({ ...pw, next: e.target.value })} />
              <small className="muted">At least 8 characters with uppercase, lowercase and a number.</small></label>
            <label className="field"><span>Repeat new password</span>
              <input type="password" required autoComplete="new-password" value={pw.confirm}
                onChange={(e) => setPw({ ...pw, confirm: e.target.value })} /></label>
            {pwError && <p className="field-error" role="alert">{pwError}</p>}
            <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
          </form>
          <hr className="divider" />
          <h3>Sessions</h3>
          <p className="muted small">Signing out ends your session on every device that uses this account.</p>
          <button className="btn btn-danger" onClick={() => setConfirmOut(true)}>Sign out everywhere</button>
        </section>
      </div>

      {confirmOut && (
        <ConfirmDialog
          title="Sign out everywhere?"
          message="You will be signed out on this and every other device, and will need your password to sign in again."
          confirmLabel="Sign out"
          danger
          onClose={() => setConfirmOut(false)}
          onConfirm={async () => { await logout(); navigate("/login", { replace: true }); }}
        />
      )}
    </>
  );
}
