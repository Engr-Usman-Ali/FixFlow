import { FormEvent, useState } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { passwordProblem } from "../../utils/format";
import AuthLayout from "./AuthLayout";

type Mode = "join" | "company";

export default function Register() {
  const { user, join, registerCompany } = useAuth();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const mode: Mode = params.get("mode") === "company" ? "company" : "join";
  const [form, setForm] = useState({ join_code: "", organization_name: "", request_prefix: "", name: "", email: "", password: "", confirm: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/app" replace />;
  const set = (field: keyof typeof form, value: string) => setForm((f) => ({ ...f, [field]: value }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const problem = passwordProblem(form.password);
    if (problem) return setError(problem);
    if (form.password !== form.confirm) return setError("The passwords do not match.");
    setBusy(true);
    try {
      const account = { name: form.name, email: form.email, password: form.password };
      if (mode === "join") await join({ ...account, join_code: form.join_code.trim() });
      else await registerCompany({ ...account, organization_name: form.organization_name, request_prefix: form.request_prefix || undefined });
      navigate("/app", { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title={mode === "join" ? "Join your company" : "Register a new company"}
      subtitle={mode === "join"
        ? "Use the join code from your administrator. You start as an Employee."
        : "Create a separate FixFlow workspace. You become its System Administrator."}
    >
      <div className="tabs tabs-compact" role="tablist">
        <button type="button" role="tab" aria-selected={mode === "join"} className={`tab ${mode === "join" ? "tab-active" : ""}`}
          onClick={() => { setError(""); setParams({}); }}>I have a join code</button>
        <button type="button" role="tab" aria-selected={mode === "company"} className={`tab ${mode === "company" ? "tab-active" : ""}`}
          onClick={() => { setError(""); setParams({ mode: "company" }); }}>New company</button>
      </div>

      <form onSubmit={submit} className="stack-form">
        {mode === "join" ? (
          <label className="field"><span>Company join code</span>
            <input required minLength={4} maxLength={16} className="mono" placeholder="e.g. 7KQ2-MX9P" value={form.join_code}
              onChange={(e) => set("join_code", e.target.value.toUpperCase())} /></label>
        ) : (
          <div className="form-grid">
            <label className="field"><span>Company name</span>
              <input required minLength={2} maxLength={120} value={form.organization_name} onChange={(e) => set("organization_name", e.target.value)} /></label>
            <label className="field"><span>Request ID prefix (optional)</span>
              <input pattern="[A-Za-z]{2,6}" maxLength={6} placeholder="e.g. ACME" value={form.request_prefix}
                onChange={(e) => set("request_prefix", e.target.value.toUpperCase())} /></label>
          </div>
        )}
        <label className="field"><span>Your full name</span>
          <input required minLength={2} maxLength={120} autoComplete="name" value={form.name} onChange={(e) => set("name", e.target.value)} /></label>
        <label className="field"><span>Work email</span>
          <input type="email" required autoComplete="email" value={form.email} onChange={(e) => set("email", e.target.value)} /></label>
        <div className="form-grid">
          <label className="field"><span>Password</span>
            <input type="password" required autoComplete="new-password" value={form.password} onChange={(e) => set("password", e.target.value)} /></label>
          <label className="field"><span>Repeat password</span>
            <input type="password" required autoComplete="new-password" value={form.confirm} onChange={(e) => set("confirm", e.target.value)} /></label>
        </div>
        <small className="muted block">At least 8 characters with an uppercase letter, a lowercase letter and a number.</small>
        {error && <p className="field-error" role="alert">{error}</p>}
        <button className="btn btn-primary btn-block" disabled={busy}>
          {busy ? "Creating…" : mode === "join" ? "Join company" : "Create company"}
        </button>
      </form>
      <p className="auth-switch">Already have an account? <Link to="/login" className="link-strong">Sign in</Link></p>
    </AuthLayout>
  );
}
