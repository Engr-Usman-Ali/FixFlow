import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import type { MaintenanceRequest } from "../../types";
import { formatDate } from "../../utils/format";
import { PriorityBadge, StatusBadge } from "../common/Badges";

/** Compact table used on the request lists and equipment history. */
export default function RequestTable({ items, linkable = true }: { items: MaintenanceRequest[]; linkable?: boolean }) {
  const go = (r: MaintenanceRequest, text: React.ReactNode, cls: string) =>
    linkable ? <Link to={`/app/requests/${r.id}`} className={cls}>{text}</Link> : <span className={cls}>{text}</span>;

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>ID</th><th>Request</th><th>Status</th><th>Priority</th><th>Technician</th><th>Created</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id}>
              <td className="nowrap">{go(r, r.ref, "link-strong")}</td>
              <td>
                {go(r, r.title, "row-title")}
                <span className="muted small">{r.category.name} · {r.location.name}{r.location_detail ? `, ${r.location_detail}` : ""}</span>
              </td>
              <td>
                <StatusBadge status={r.status} />
                {r.overdue && <span className="overdue-flag"><AlertTriangle size={13} /> Overdue</span>}
              </td>
              <td>
                <PriorityBadge priority={r.priority} />
                {!r.priority_confirmed && !["Closed", "Rejected", "Resolved"].includes(r.status) && (
                  <span className="muted small block">not confirmed</span>
                )}
              </td>
              <td>{r.technician?.name ?? <span className="muted">Unassigned</span>}</td>
              <td className="nowrap">{formatDate(r.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
