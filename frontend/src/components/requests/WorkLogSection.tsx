// Diagnosis and repair log. Entries are append-only (FR-035).
import { useState } from "react";
import { requestApi } from "../../api/services";
import { useToast } from "../../context/ToastContext";
import type { RequestDetail } from "../../types";
import { formatDateTime } from "../../utils/format";

export default function WorkLogSection({ request, onChanged }: { request: RequestDetail; onChanged: () => void }) {
  const toast = useToast();
  const [diagnosis, setDiagnosis] = useState("");
  const [action, setAction] = useState("");
  const [materials, setMaterials] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setBusy(true);
    setError("");
    try {
      await requestApi.addWorkLog(request.id, {
        diagnosis: diagnosis || undefined,
        action_taken: action || undefined,
        materials_used: materials || undefined,
      });
      toast("Work log added");
      setDiagnosis("");
      setAction("");
      setMaterials("");
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h3>Work log</h3>
      {request.work_logs.length === 0 && <p className="muted">No work recorded yet.</p>}
      <ul className="log-list">
        {request.work_logs.map((log) => (
          <li key={log.id}>
            <div className="log-meta"><strong>{log.author.name}</strong><span className="muted small">{formatDateTime(log.created_at)}</span></div>
            {log.diagnosis && <p><em>Diagnosis:</em> {log.diagnosis}</p>}
            {log.action_taken && <p><em>Action:</em> {log.action_taken}</p>}
            {log.materials_used && <p><em>Materials:</em> {log.materials_used}</p>}
          </li>
        ))}
      </ul>

      {request.can_add_work_log && (
        <div className="log-form">
          <label className="field"><span>Diagnosis</span>
            <textarea rows={2} value={diagnosis} onChange={(e) => setDiagnosis(e.target.value)} /></label>
          <label className="field"><span>Action taken</span>
            <textarea rows={2} value={action} onChange={(e) => setAction(e.target.value)} /></label>
          <label className="field"><span>Materials or parts used</span>
            <input value={materials} onChange={(e) => setMaterials(e.target.value)} /></label>
          {error && <p className="field-error" role="alert">{error}</p>}
          <button className="btn btn-secondary" onClick={submit} disabled={busy}>{busy ? "Saving…" : "Add entry"}</button>
        </div>
      )}
    </section>
  );
}
