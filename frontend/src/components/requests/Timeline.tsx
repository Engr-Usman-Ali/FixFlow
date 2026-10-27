// Merges status changes and audit events into one chronological history (FR-044).
import type { RequestDetail } from "../../types";
import { formatDateTime } from "../../utils/format";

export default function Timeline({ request }: { request: RequestDetail }) {
  const events = [
    ...request.history.map((h) => ({
      key: `s${h.id}`,
      at: h.changed_at,
      text: h.old_status ? `${h.old_status} to ${h.new_status}` : `Submitted as ${h.new_status}`,
      who: h.changed_by.name,
      note: h.reason && h.old_status ? h.reason : null,
    })),
    ...request.audit.map((a) => ({ key: `a${a.id}`, at: a.created_at, text: a.detail, who: a.actor.name, note: null })),
  ].sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());

  return (
    <section className="card">
      <h3>History</h3>
      <ol className="timeline">
        {events.map((e) => (
          <li key={e.key}>
            <strong>{e.text}</strong>
            {e.note && <span className="small">Reason: {e.note}</span>}
            <span className="muted small">{e.who} · {formatDateTime(e.at)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
