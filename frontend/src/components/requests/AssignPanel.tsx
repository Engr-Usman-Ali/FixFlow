// Manager panel: confirm priority (FR-021) and assign or reassign a technician (FR-022).
import { useState } from "react";
import { requestApi, userApi } from "../../api/services";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { PRIORITIES } from "../../types";
import type { Priority, RequestDetail } from "../../types";
import AiSuggestion from "./AiSuggestion";

export default function AssignPanel({ request, onChanged }: { request: RequestDetail; onChanged: () => void }) {
  const toast = useToast();
  const { data: technicians, loading } = useAsync(
    () => (request.can_assign ? userApi.technicians() : Promise.resolve([])),
    [request.can_assign],
  );
  const [techId, setTechId] = useState("");
  const [priority, setPriority] = useState<Priority>(request.priority);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const done = (message: string) => {
    toast(message);
    setTechId("");
    setNote("");
    window.dispatchEvent(new Event("fixflow:notifications-changed"));
    onChanged();
  };

  async function run(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError("");
    try {
      await action();
      done(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const assign = () => {
    if (!techId) return setError("Choose a technician.");
    run(() => requestApi.assign(request.id, { technician_id: Number(techId), priority, note: note || undefined }),
      request.technician ? "Technician reassigned" : "Technician assigned");
  };
  const confirmPriority = () => run(() => requestApi.setPriority(request.id, priority), `Priority confirmed as ${priority}`);
  const choices = (technicians ?? []).filter((t) => t.id !== request.technician?.id);

  return (
    <section className="card card-accent">
      <h3>{request.can_assign ? (request.technician ? "Review and reassign" : "Review and assign") : "Confirm priority"}</h3>
      <div className="form-grid">
        <label className="field">
          <span>Priority</span>
          <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
            {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
          </select>
          <small className="muted">
            {request.priority_confirmed ? `Confirmed as ${request.priority}.` : `Requested as ${request.priority}; not confirmed yet.`}
          </small>
        </label>
        {request.can_assign && (
          <label className="field">
            <span>Technician</span>
            <select value={techId} onChange={(e) => setTechId(e.target.value)} disabled={loading}>
              <option value="">{loading ? "Loading…" : choices.length ? "Select…" : "No other active technicians"}</option>
              {choices.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </label>
        )}
      </div>
      {request.can_assign && (
        <label className="field">
          <span>Note for the technician (optional)</span>
          <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
        </label>
      )}

      <AiSuggestion title={request.title} description={request.description} onApply={(s) => setPriority(s.priority)} />

      {error && <p className="field-error" role="alert">{error}</p>}
      <div className="action-row">
        {request.can_set_priority && (
          <button className="btn btn-secondary" onClick={confirmPriority} disabled={busy}>Confirm priority only</button>
        )}
        {request.can_assign && (
          <button className="btn btn-primary" onClick={assign} disabled={busy || !techId}>
            {busy ? "Saving…" : request.technician ? "Reassign" : "Assign technician"}
          </button>
        )}
      </div>
    </section>
  );
}
