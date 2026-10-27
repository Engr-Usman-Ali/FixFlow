// FR-100, FR-101: who did what and when, for the whole company.
import { useState } from "react";
import { auditApi } from "../../api/services";
import PageHeader from "../../components/common/PageHeader";
import Pager from "../../components/common/Pager";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime } from "../../utils/format";

const ACTIONS = [
  { value: "", label: "All activity" },
  { value: "user.", label: "Users and sign-in" },
  { value: "settings.", label: "Company settings" },
  { value: "organization.", label: "Company registration" },
  { value: "request.", label: "Requests created" },
  { value: "assignment", label: "Assignments" },
  { value: "priority", label: "Priority changes" },
  { value: "equipment.", label: "Equipment" },
  { value: "ai.", label: "AI suggestions used" },
];

export default function AuditLog() {
  const [filters, setFilters] = useState({ action: "", date_from: "", date_to: "", page: 1 });
  const { data, loading, error, reload } = useAsync(() => auditApi.list(filters), [JSON.stringify(filters)]);
  const set = (patch: Partial<typeof filters>) => setFilters((f) => ({ ...f, page: 1, ...patch }));

  return (
    <>
      <PageHeader title="Audit log" subtitle="A permanent record of important actions in your company." />
      <div className="card filters-inline">
        <select value={filters.action} onChange={(e) => set({ action: e.target.value })} aria-label="Activity type">
          {ACTIONS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
        </select>
        <label className="date-field">From <input type="date" value={filters.date_from} onChange={(e) => set({ date_from: e.target.value })} /></label>
        <label className="date-field">To <input type="date" value={filters.date_to} onChange={(e) => set({ date_to: e.target.value })} /></label>
      </div>

      {loading && !data ? <Loading /> : error || !data ? <ErrorState message={error ?? "Could not load the audit log."} onRetry={reload} /> : data.items.length === 0 ? (
        <EmptyState title="No matching activity" text="Change the filters to see more." />
      ) : (
        <>
          <div className="card flush table-wrap">
            <table className="table">
              <thead><tr><th>When</th><th>Who</th><th>What</th><th>Type</th></tr></thead>
              <tbody>
                {data.items.map((e) => (
                  <tr key={e.id}>
                    <td className="nowrap small">{formatDateTime(e.created_at)}</td>
                    <td><span className="row-title">{e.actor.name}</span><span className="muted small">{e.actor.role}</span></td>
                    <td>
                      {e.detail}
                      {e.request_ref && <span className="muted small block">Request {e.request_ref}</span>}
                    </td>
                    <td><code className="small">{e.action}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager page={filters.page} total={data.total} pageSize={data.page_size} onPage={(page) => setFilters((f) => ({ ...f, page }))} />
        </>
      )}
    </>
  );
}
