// Buttons for the status moves the current user may make, with a dialog for reasons/completion notes.
import { useState } from "react";
import { requestApi } from "../../api/services";
import { useToast } from "../../context/ToastContext";
import type { RequestDetail, Status } from "../../types";
import { actionLabel, needsReason } from "../../utils/format";
import Modal from "../common/Modal";

interface Props { request: RequestDetail; onChanged: () => void }

export default function StatusActions({ request, onChanged }: Props) {
  const toast = useToast();
  const [target, setTarget] = useState<Status | null>(null);
  const [reason, setReason] = useState("");
  const [completion, setCompletion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  if (request.allowed_transitions.length === 0) return null;

  const askReason = target ? needsReason(request.status, target) : false;
  const askCompletion = target === "Resolved";

  function close() {
    setTarget(null);
    setReason("");
    setCompletion("");
    setError("");
  }

  async function submit() {
    if (!target) return;
    setBusy(true);
    setError("");
    try {
      await requestApi.changeStatus(request.id, {
        status: target,
        reason: reason || undefined,
        completion_details: completion || undefined,
      });
      toast(`Status changed to ${target}`);
      close();
      window.dispatchEvent(new Event("fixflow:notifications-changed"));
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="action-row">
        {request.allowed_transitions.map((t) => (
          <button
            key={t}
            className={`btn ${t === "Rejected" ? "btn-danger" : t === "Resolved" || t === "Closed" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setTarget(t)}
          >
            {actionLabel(request.status, t)}
          </button>
        ))}
      </div>

      {target && (
        <Modal title={actionLabel(request.status, target)} onClose={close}>
          <p className="muted">{request.ref} · {request.title}</p>
          {askCompletion && (
            <label className="field">
              <span>Completion details</span>
              <textarea rows={4} value={completion} onChange={(e) => setCompletion(e.target.value)}
                placeholder="What was fixed, and how was it tested?" />
            </label>
          )}
          {askReason && (
            <label className="field">
              <span>Reason</span>
              <textarea rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Explain why." />
            </label>
          )}
          {!askReason && !askCompletion && <p>Change status from {request.status} to {target}?</p>}
          {error && <p className="field-error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button className="btn btn-ghost" onClick={close}>Cancel</button>
            <button className="btn btn-primary" onClick={submit} disabled={busy}>{busy ? "Saving…" : "Confirm"}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
