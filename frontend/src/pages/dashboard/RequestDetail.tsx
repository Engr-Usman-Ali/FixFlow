import { AlertTriangle, ArrowLeft, Clock } from "lucide-react";
import { useNavigate, useParams } from "react-router-dom";
import { requestApi } from "../../api/services";
import { PriorityBadge, StatusBadge } from "../../components/common/Badges";
import { ErrorState, Loading } from "../../components/common/States";
import AssignPanel from "../../components/requests/AssignPanel";
import CommentSection from "../../components/requests/CommentSection";
import StatusActions from "../../components/requests/StatusActions";
import Timeline from "../../components/requests/Timeline";
import WorkLogSection from "../../components/requests/WorkLogSection";
import { useAsync } from "../../hooks/useAsync";
import { dueLabel, formatDateTime } from "../../utils/format";

/** FR-015, FR-044: request details and full history for authorised users. */
export default function RequestDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: r, loading, error, reload } = useAsync(() => requestApi.get(id!), [id]);

  if (loading && !r) return <Loading />;
  if (error || !r) return <ErrorState message={error ?? "Request not found."} onRetry={reload} />;

  const finished = ["Resolved", "Closed", "Rejected"].includes(r.status);

  return (
    <>
      <button className="back-link" onClick={() => navigate(-1)}><ArrowLeft size={16} /> Back</button>

      <header className="detail-head">
        <div>
          <span className="muted">{r.ref}</span>
          <h1>{r.title}</h1>
          <div className="badge-row">
            <StatusBadge status={r.status} />
            <PriorityBadge priority={r.priority} />
            {!r.priority_confirmed && !finished && <span className="muted small">Priority not yet confirmed</span>}
            {r.overdue && <span className="overdue-flag"><AlertTriangle size={13} /> Overdue</span>}
            {!finished && r.due_at && !r.overdue && <span className="muted small"><Clock size={12} /> {dueLabel(r.due_at)}</span>}
          </div>
        </div>
        <StatusActions request={r} onChanged={reload} />
      </header>

      <div className="detail-grid">
        <div className="stack">
          <section className="card">
            <h3>Details</h3>
            <p className="prose">{r.description}</p>
            <dl className="facts">
              <div><dt>Category</dt><dd>{r.category.name}</dd></div>
              <div><dt>Location</dt><dd>{r.location.name}{r.location_detail ? ` · ${r.location_detail}` : ""}</dd></div>
              <div><dt>Equipment</dt><dd>{r.equipment ? `${r.equipment.asset_code} · ${r.equipment.name}` : "None"}</dd></div>
              <div><dt>Reported by</dt><dd>{r.creator.name}</dd></div>
              <div><dt>Technician</dt><dd>{r.technician?.name ?? "Not assigned"}</dd></div>
              <div><dt>Created</dt><dd>{formatDateTime(r.created_at)}</dd></div>
              {r.due_at && <div><dt>Service target</dt><dd>{formatDateTime(r.due_at)}</dd></div>}
              {r.resolved_at && <div><dt>Resolved</dt><dd>{formatDateTime(r.resolved_at)}</dd></div>}
              {r.closed_at && <div><dt>Closed</dt><dd>{formatDateTime(r.closed_at)}{r.closed_by ? ` by ${r.closed_by.name}` : ""}</dd></div>}
            </dl>
            {r.completion_details && (
              <div className="callout">
                <strong>Completion details</strong>
                <p className="prose">{r.completion_details}</p>
              </div>
            )}
          </section>

          {(r.can_assign || r.can_set_priority) && (
            <AssignPanel key={`${r.technician?.id ?? "none"}-${r.priority}-${r.status}`} request={r} onChanged={reload} />
          )}
          <WorkLogSection request={r} onChanged={reload} />
          <CommentSection request={r} onChanged={reload} />
        </div>

        <div className="stack">
          <Timeline request={r} />
          {r.assignments.length > 0 && (
            <section className="card">
              <h3>Assignments</h3>
              <ul className="log-list">
                {r.assignments.map((a) => (
                  <li key={a.id}>
                    <strong>{a.technician.name}</strong>
                    <span className="muted small">
                      by {a.assigned_by.name} · {formatDateTime(a.assigned_at)}
                      {a.ended_at ? ` · ended ${formatDateTime(a.ended_at)}` : " · current"}
                    </span>
                    {a.reason && <span className="small">{a.reason}</span>}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </>
  );
}
