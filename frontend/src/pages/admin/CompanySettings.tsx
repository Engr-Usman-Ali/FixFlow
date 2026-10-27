// System Administrator: company configuration (SRS 2.3 "system configuration").
import { Copy, Pencil, Plus, RefreshCw } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { orgApi } from "../../api/services";
import ConfirmDialog from "../../components/common/ConfirmDialog";
import Modal from "../../components/common/Modal";
import PageHeader from "../../components/common/PageHeader";
import { ErrorState, Loading } from "../../components/common/States";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { PRIORITIES } from "../../types";
import type { Lookup, OrganizationSettings, Priority } from "../../types";

const TABS = [
  { key: "company", label: "Company" },
  { key: "categories", label: "Categories" },
  { key: "locations", label: "Locations" },
  { key: "sla", label: "Service targets" },
];

export default function CompanySettings() {
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.key === params.get("tab"))?.key ?? "company";

  return (
    <>
      <PageHeader title="Company settings" subtitle="Configuration used by everyone in your company." />
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={t.key === tab} className={`tab ${t.key === tab ? "tab-active" : ""}`}
            onClick={() => setParams(t.key === "company" ? {} : { tab: t.key })}>{t.label}</button>
        ))}
      </div>
      {tab === "company" && <CompanyTab />}
      {tab === "categories" && <LookupTab kind="category" />}
      {tab === "locations" && <LookupTab kind="location" />}
      {tab === "sla" && <SlaTab />}
    </>
  );
}

/* ---------------------------------------------------------------- company ---- */
function CompanyTab() {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => orgApi.get(), []);
  const [form, setForm] = useState<OrganizationSettings | null>(null);
  const [formError, setFormError] = useState("");
  const [confirmCode, setConfirmCode] = useState(false);

  useEffect(() => { if (data) setForm(data); }, [data]);

  if (loading && !data) return <Loading />;
  if (error || !data || !form) return <ErrorState message={error ?? "Could not load settings."} onRetry={reload} />;

  async function save(e: FormEvent) {
    e.preventDefault();
    setFormError("");
    try {
      const saved = await orgApi.update({
        name: form!.name, request_prefix: form!.request_prefix,
        allow_self_signup: form!.allow_self_signup, ai_enabled: form!.ai_enabled,
      });
      setForm(saved);
      toast("Settings saved. Names update for everyone at their next page load.");
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  return (
    <div className="two-col">
      <section className="card">
        <h3>Company profile</h3>
        <form onSubmit={save}>
          <label className="field"><span>Company name</span>
            <input required minLength={2} maxLength={120} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
          <label className="field"><span>Request ID prefix</span>
            <input required pattern="[A-Za-z]{2,6}" maxLength={6} value={form.request_prefix}
              onChange={(e) => setForm({ ...form, request_prefix: e.target.value.toUpperCase() })} />
            <small className="muted">2 to 6 letters. Requests show as {form.request_prefix || "ABC"}-00042.</small></label>
          <label className="check toggle-row">
            <input type="checkbox" checked={form.allow_self_signup} onChange={(e) => setForm({ ...form, allow_self_signup: e.target.checked })} />
            <span><strong>Allow self sign-up</strong><br /><span className="muted small">Anyone with the join code can create an Employee account.</span></span>
          </label>
          <label className="check toggle-row">
            <input type="checkbox" checked={form.ai_enabled && form.ai_configured} disabled={!form.ai_configured}
              onChange={(e) => setForm({ ...form, ai_enabled: e.target.checked })} />
            <span><strong>AI suggestions (Google Gemini)</strong><br />
              <span className="muted small">
                {form.ai_configured
                  ? `Server key configured, model ${form.ai_model}. Only the title and description are sent; people always decide.`
                  : "Not available: the server has no GEMINI_API_KEY in its .env file."}
              </span></span>
          </label>
          {formError && <p className="field-error" role="alert">{formError}</p>}
          <button className="btn btn-primary">Save settings</button>
        </form>
      </section>

      <section className="card">
        <h3>Join code</h3>
        <p className="muted">Share this code with employees so they can sign up into {form.name}.</p>
        <div className="code-box">
          <strong className="mono big">{form.join_code}</strong>
          <button className="btn btn-secondary btn-small" onClick={() => navigator.clipboard?.writeText(form.join_code).then(() => toast("Code copied"))}>
            <Copy size={14} /> Copy
          </button>
          <button className="btn btn-secondary btn-small" onClick={() => setConfirmCode(true)}><RefreshCw size={14} /> New code</button>
        </div>
        {!form.allow_self_signup && <p className="muted small">Self sign-up is off, so the code cannot be used right now.</p>}
      </section>

      {confirmCode && (
        <ConfirmDialog
          title="Create a new join code?"
          message="The current code stops working straight away. People who already joined are not affected."
          confirmLabel="Create new code"
          onClose={() => setConfirmCode(false)}
          onConfirm={async () => { setForm(await orgApi.regenerateJoinCode()); toast("New join code created"); }}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------- categories & locations ---- */
function LookupTab({ kind }: { kind: "category" | "location" }) {
  const toast = useToast();
  const api = kind === "category"
    ? { list: () => orgApi.categories(true), create: orgApi.createCategory, update: orgApi.updateCategory }
    : { list: () => orgApi.locations(true), create: orgApi.createLocation, update: orgApi.updateLocation };
  const { data, loading, error, reload } = useAsync(api.list, [kind]);
  const [newName, setNewName] = useState("");
  const [editing, setEditing] = useState<Lookup | null>(null);
  const [formError, setFormError] = useState("");
  const plural = kind === "category" ? "categories" : "locations";

  async function add(e: FormEvent) {
    e.preventDefault();
    setFormError("");
    try {
      await api.create(newName.trim());
      toast(`Added "${newName.trim()}"`);
      setNewName("");
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  async function save(item: Lookup) {
    setFormError("");
    try {
      await api.update(item.id, { name: item.name.trim(), is_active: item.is_active });
      toast("Saved");
      setEditing(null);
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? `Could not load ${plural}.`} onRetry={reload} />;

  return (
    <section className="card">
      <p className="muted">
        {kind === "category"
          ? "Categories group requests and equipment, and are offered to the AI. Retired categories stay on old records but cannot be chosen for new ones."
          : "Places where problems happen. Requests and equipment pick one of these; people can add an exact spot as free text."}
      </p>
      <form className="inline-form" onSubmit={add}>
        <input required minLength={2} maxLength={160} placeholder={`New ${kind} name`} value={newName} onChange={(e) => setNewName(e.target.value)} aria-label={`New ${kind}`} />
        <button className="btn btn-primary"><Plus size={16} /> Add</button>
      </form>
      {formError && !editing && <p className="field-error" role="alert">{formError}</p>}
      <ul className="lookup-list">
        {data.map((item) => (
          <li key={item.id} className={item.is_active ? "" : "row-muted"}>
            <span>{item.name}{!item.is_active && <span className="muted small"> · retired</span>}</span>
            <span className="row-actions">
              <button className="icon-btn" aria-label={`Rename ${item.name}`} onClick={() => { setFormError(""); setEditing({ ...item }); }}><Pencil size={16} /></button>
              <button className="btn btn-secondary btn-small" onClick={() => save({ ...item, is_active: !item.is_active })}>
                {item.is_active ? "Retire" : "Reactivate"}
              </button>
            </span>
          </li>
        ))}
      </ul>

      {editing && (
        <Modal title={`Rename ${kind}`} onClose={() => setEditing(null)}>
          <form className="stack-form" onSubmit={(e) => { e.preventDefault(); save(editing); }}>
            <label className="field"><span>Name</span>
              <input required minLength={2} maxLength={160} value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })} /></label>
            <p className="muted small">The new name shows on every request and equipment record that uses it.</p>
            {formError && <p className="field-error" role="alert">{formError}</p>}
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setEditing(null)}>Cancel</button>
              <button className="btn btn-primary">Save</button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  );
}

/* ---------------------------------------------------------- service targets ---- */
function SlaTab() {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => orgApi.sla(), []);
  const [hours, setHours] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (data) setHours(Object.fromEntries(data.map((d) => [d.priority, String(d.target_hours)])));
  }, [data]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setFormError("");
    const items = PRIORITIES.map((p) => ({ priority: p as Priority, target_hours: Number(hours[p]) }));
    if (items.some((i) => !Number.isInteger(i.target_hours) || i.target_hours < 1)) {
      return setFormError("Enter a whole number of hours (1 or more) for every priority.");
    }
    try {
      await orgApi.updateSla(items);
      toast("Service targets saved");
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "Could not load service targets."} onRetry={reload} />;

  return (
    <section className="card form-card">
      <p className="muted">
        Open work becomes <strong>overdue</strong> when it is older than the target for its priority (BR-010).
        Changes apply straight away to every open request.
      </p>
      <form onSubmit={save}>
        <div className="form-grid">
          {[...PRIORITIES].reverse().map((p) => (
            <label key={p} className="field"><span>{p} (hours)</span>
              <input type="number" min={1} max={8760} step={1} value={hours[p] ?? ""} onChange={(e) => setHours({ ...hours, [p]: e.target.value })} />
              <small className="muted">{hours[p] && Number(hours[p]) >= 24 ? `${(Number(hours[p]) / 24).toFixed(1)} days` : ""}</small>
            </label>
          ))}
        </div>
        {formError && <p className="field-error" role="alert">{formError}</p>}
        <button className="btn btn-primary">Save targets</button>
      </form>
    </section>
  );
}
