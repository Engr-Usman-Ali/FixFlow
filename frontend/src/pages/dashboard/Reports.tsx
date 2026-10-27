import { Download, Printer } from "lucide-react";
import { useState } from "react";
import { reportApi } from "../../api/services";
import BarList from "../../components/common/BarList";
import PageHeader from "../../components/common/PageHeader";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import type { Summary } from "../../types";
import { downloadCsv } from "../../utils/format";

/** UC-04 / FR-080 to FR-085: management reports. Viewing changes nothing. */
export default function Reports() {
  const { user } = useAuth();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const { data, loading, error, reload } = useAsync(() => reportApi.summary(from || undefined, to || undefined), [from, to]);

  function exportCsv(s: Summary) {
    const rows: (string | number | null)[][] = [
      ["FixFlow report", user?.organization.name ?? ""],
      ["Period", `${from || "start"} to ${to || "today"}`],
      [],
      ["Metric", "Value"],
      ["Total", s.total], ["Pending", s.pending], ["In progress", s.in_progress],
      ["Resolved or closed", s.resolved], ["Rejected", s.rejected], ["Overdue", s.overdue],
      ["Average completion (hours)", s.avg_completion_hours],
      [],
      ["Status", "Requests"], ...Object.entries(s.by_status),
      [],
      ["Priority", "Requests"], ...Object.entries(s.by_priority),
      [],
      ["Category", "Requests"], ...Object.entries(s.by_category),
      [],
      ["Location", "Requests"], ...Object.entries(s.by_location),
      [],
      ["Technician", "Open", "Completed", "Average hours"],
      ...s.technician_workload.map((t) => [t.technician, t.open, t.completed, t.avg_hours]),
      [],
      ["Asset code", "Equipment", "Requests"],
      ...s.repeated_equipment.map((e) => [e.asset_code, e.name, e.requests]),
    ];
    downloadCsv(`fixflow-report-${new Date().toISOString().slice(0, 10)}.csv`, rows);
  }

  return (
    <>
      <PageHeader
        title="Reports"
        subtitle="Totals and trends across your company's maintenance requests."
        actions={
          <div className="date-filters">
            <label>From <input type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} /></label>
            <label>To <input type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} /></label>
            {data && <button className="btn btn-secondary" onClick={() => exportCsv(data)}><Download size={16} /> CSV</button>}
            <button className="btn btn-secondary no-print" onClick={() => window.print()}><Printer size={16} /> Print</button>
          </div>
        }
      />

      {loading && !data ? <Loading /> : error || !data ? (
        <ErrorState message={error ?? "The report could not be loaded."} onRetry={reload} />
      ) : data.total === 0 ? (
        <EmptyState title="No requests in this period" text="Change the dates to see results." />
      ) : (
        <>
          <div className="stat-grid">
            {([
              ["Total requests", data.total],
              ["Pending", data.pending],
              ["In progress", data.in_progress],
              ["Resolved or closed", data.resolved],
              ["Overdue", data.overdue],
              ["Avg. completion", data.avg_completion_hours === null ? "–" : `${data.avg_completion_hours} h`],
            ] as [string, number | string][]).map(([label, value]) => (
              <div key={label} className={`stat card ${label === "Overdue" && Number(value) > 0 ? "stat-danger" : ""}`}>
                <strong>{value}</strong><span>{label}</span>
              </div>
            ))}
          </div>

          <div className="two-col">
            <section className="card"><h3>By status</h3><BarList data={data.by_status} /></section>
            <section className="card"><h3>By priority</h3><BarList data={data.by_priority} /></section>
            <section className="card"><h3>By category</h3><BarList data={data.by_category} /></section>
            <section className="card"><h3>By location</h3><BarList data={data.by_location} /></section>
          </div>

          <div className="two-col">
            <section className="card">
              <h3>Technician workload</h3>
              {data.technician_workload.length === 0 ? <p className="muted">No technicians yet.</p> : (
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Technician</th><th>Open</th><th>Completed</th><th>Avg. repair time</th></tr></thead>
                    <tbody>
                      {data.technician_workload.map((t) => (
                        <tr key={t.technician_id}>
                          <td>{t.technician}</td><td>{t.open}</td><td>{t.completed}</td>
                          <td>{t.avg_hours === null ? <span className="muted">No data</span> : `${t.avg_hours} h`}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="card">
              <h3>Equipment with repeat repairs</h3>
              {data.repeated_equipment.length === 0 ? (
                <p className="muted">No equipment has two or more linked requests in this period.</p>
              ) : (
                <ul className="log-list">
                  {data.repeated_equipment.map((q) => (
                    <li key={q.equipment_id}><strong>{q.asset_code} · {q.name}</strong><span className="muted small">{q.requests} requests</span></li>
                  ))}
                </ul>
              )}
              <p className="muted small">
                Overdue rule: open work past its service target ({Object.entries(data.sla_hours).map(([p, h]) => `${p} ${h} h`).join(", ")}).
              </p>
            </section>
          </div>
        </>
      )}
    </>
  );
}
