import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { equipmentApi, requestApi } from "../../api/services";
import PageHeader from "../../components/common/PageHeader";
import AiSuggestion from "../../components/requests/AiSuggestion";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { useLookups } from "../../hooks/useLookups";
import { PRIORITIES } from "../../types";
import type { Priority } from "../../types";

/** UC-01: submit a maintenance request (FR-010 to FR-014). */
export default function NewRequest() {
  const navigate = useNavigate();
  const toast = useToast();
  const { can } = useAuth();
  const { categories, locations, error: lookupError } = useLookups();
  const { data: equipment } = useAsync(
    () => (can("equipment.view") ? equipmentApi.list({ active_only: true }) : Promise.resolve([])),
    [],
  );

  const [form, setForm] = useState({
    title: "", description: "", category_id: "", location_id: "", location_detail: "",
    priority: "Medium" as Priority, equipment_id: "",
  });
  const [aiUsed, setAiUsed] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (field: keyof typeof form, value: string) => setForm((f) => ({ ...f, [field]: value }));

  /** Instant feedback in plain language; the API validates everything again (DR-002). */
  function validate() {
    const found: Record<string, string> = {};
    if (form.title.trim().length < 3) found.title = "Enter a title of at least 3 characters.";
    if (form.description.trim().length < 10) found.description = "Describe the problem in at least 10 characters.";
    if (!form.category_id) found.category_id = "Choose a category.";
    if (!form.location_id) found.location_id = "Choose where the problem is.";
    setErrors(found);
    return Object.keys(found).length === 0;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setServerError("");
    if (!validate()) return;
    setBusy(true);
    try {
      const created = await requestApi.create({
        title: form.title,
        description: form.description,
        category_id: Number(form.category_id),
        location_id: Number(form.location_id),
        location_detail: form.location_detail || undefined,
        priority: form.priority,
        equipment_id: form.equipment_id ? Number(form.equipment_id) : null,
        ai_suggestion_used: aiUsed,
      });
      toast(`Request ${created.ref} submitted. Status: ${created.status}.`);
      navigate(`/app/requests/${created.id}`);
    } catch (err) {
      setServerError((err as Error).message); // no false success (UC-01 alternative flow)
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Report a problem" subtitle="Tell us what is wrong and where. A manager will review it." />
      <form className="card form-card" onSubmit={submit} noValidate>
        <p className="muted small">Fields marked <span className="req">*</span> are required.</p>
        <label className="field">
          <span>Title <span className="req">*</span></span>
          <input value={form.title} onChange={(e) => set("title", e.target.value)} maxLength={200}
            placeholder="e.g. Conveyor belt 3 jams at start-up" aria-invalid={!!errors.title} />
          {errors.title && <small className="field-error">{errors.title}</small>}
        </label>

        <label className="field">
          <span>What is happening? <span className="req">*</span></span>
          <textarea rows={5} value={form.description} onChange={(e) => set("description", e.target.value)} maxLength={4000}
            placeholder="When did it start? What have you already tried?" aria-invalid={!!errors.description} />
          {errors.description && <small className="field-error">{errors.description}</small>}
        </label>

        <AiSuggestion
          title={form.title}
          description={form.description}
          onApply={(s) => {
            setForm((f) => ({ ...f, category_id: String(s.category_id), priority: s.priority }));
            setAiUsed(true);
          }}
        />

        <div className="form-grid">
          <label className="field">
            <span>Category <span className="req">*</span></span>
            <select value={form.category_id} onChange={(e) => set("category_id", e.target.value)} aria-invalid={!!errors.category_id}>
              <option value="">Select…</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            {errors.category_id && <small className="field-error">{errors.category_id}</small>}
          </label>
          <label className="field">
            <span>Urgency</span>
            <select value={form.priority} onChange={(e) => set("priority", e.target.value)}>
              {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
            </select>
            <small className="muted">A manager confirms the final priority.</small>
          </label>
          <label className="field">
            <span>Location <span className="req">*</span></span>
            <select value={form.location_id} onChange={(e) => set("location_id", e.target.value)} aria-invalid={!!errors.location_id}>
              <option value="">Select…</option>
              {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
            </select>
            {errors.location_id && <small className="field-error">{errors.location_id}</small>}
          </label>
          <label className="field">
            <span>Exact spot (optional)</span>
            <input value={form.location_detail} onChange={(e) => set("location_detail", e.target.value)} maxLength={160}
              placeholder="e.g. Room 4, near the window" />
          </label>
          <label className="field">
            <span>Equipment (optional)</span>
            <select value={form.equipment_id} onChange={(e) => set("equipment_id", e.target.value)}>
              <option value="">Not equipment related</option>
              {(equipment ?? []).map((q) => (
                <option key={q.id} value={q.id}>{q.asset_code} · {q.name}</option>
              ))}
            </select>
          </label>
        </div>

        {lookupError && <p className="field-error" role="alert">{lookupError}</p>}
        {serverError && <p className="field-error" role="alert">{serverError}</p>}
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Submitting…" : "Submit request"}</button>
        </div>
      </form>
    </>
  );
}
