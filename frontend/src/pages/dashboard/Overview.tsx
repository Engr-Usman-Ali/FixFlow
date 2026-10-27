import { AlertTriangle, CheckCircle2, ClipboardList, Hourglass, Inbox, KeyRound, Lock, MapPin, Tags, Users, Wrench } from "lucide-react";
import { Link } from "react-router-dom";
import { orgApi, reportApi } from "../../api/services";
import BarList from "../../components/common/BarList";
import { StatusBadge } from "../../components/common/Badges";
import PageHeader from "../../components/common/PageHeader";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { formatDateTime, timeAgo } from "../../utils/format";
import { requestsLabel } from "../../utils/navigation";

export default function Overview() {
  const { user, can } = useAuth();
  if (!user) return null;
  return can("user.manage") || can("settings.manage") ? <AdminHome /> : <WorkHome />;
}

/* ------------------------------------------------ maintenance roles ---- */
function WorkHome() {
  const { user, can } = useAuth();
  const { data, loading, error, reload } = useAsync(() => reportApi.overview(), []);
  if (!user) return null;
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "Could not load the dashboard."} onRetry={reload} />;

  const greeting = can("request.view_all")
    ? `Here is the state of maintenance at ${user.organization.name}.`
    : can("request.view_assigned") ? "Here is the work assigned to you." : "Here is where your reported problems stand.";

  const stats = [
    { label: "Total requests", value: data.total, icon: ClipboardList },
    { label: "Still open", value: data.open, icon: Hourglass },
    { label: "Overdue", value: data.overdue, icon: AlertTriangle, danger: data.overdue > 0 },
    { label: "Resolved or closed", value: (data.by_status["Resolved"] ?? 0) + (data.by_status["Closed"] ?? 0), icon: CheckCircle2 },
  ];

  return (
    <>
      <PageHeader
        title={`Hello, ${user.name.split(" ")[0]}`}
        subtitle={greeting}
        actions={can("request.create") && <Link to="/app/requests/new" className="btn btn-primary">Report a problem</Link>}
      />

      <div className="stat-grid">
        {stats.map(({ label, value, icon: Icon, danger }) => (
          <div key={label} className={`stat card ${danger ? "stat-danger" : ""}`}>
            <Icon size={18} />
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>

      {can("request.review") && (
        <div className="two-col">
          <Link to="/app/queue" className="card stat-link">
            <Inbox size={20} /><div><strong>{data.awaiting_review}</strong><span>waiting for review</span></div>
          </Link>
          <Link to="/app/queue?tab=closure" className="card stat-link">
            <CheckCircle2 size={20} /><div><strong>{data.awaiting_closure}</strong><span>resolved, waiting to be closed</span></div>
          </Link>
        </div>
      )}

      <div className="two-col">
        <section className="card">
          <h3>Requests by status</h3>
          <BarList data={data.by_status} />
        </section>

        <section className="card">
          <div className="card-head">
            <h3>Latest activity</h3>
            <Link to="/app/requests" className="link-strong small">View {requestsLabel(can).toLowerCase()}</Link>
          </div>
          {data.recent.length === 0 ? (
            <EmptyState title="Nothing here yet" text="Requests will show up here." />
          ) : (
            <ul className="recent-list">
              {data.recent.map((r) => (
                <li key={r.id}>
                  <Link to={`/app/requests/${r.id}`}>
                    <span className="row-title">{r.title}</span>
                    <span className="muted small">{r.ref} · updated {timeAgo(r.updated_at)}</span>
                  </Link>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}

/* ------------------------------------------------ system administrator ---- */
function AdminHome() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useAsync(() => reportApi.adminOverview(), []);
  const org = useAsync(() => orgApi.get(), []);
  if (!user) return null;
  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "Could not load the dashboard."} onRetry={reload} />;

  const stats = [
    { label: "Active users", value: `${data.users_active} / ${data.users_total}`, icon: Users },
    { label: "Locked accounts", value: data.users_locked, icon: Lock, danger: data.users_locked > 0 },
    { label: "Active categories", value: data.categories_active, icon: Tags },
    { label: "Active locations", value: data.locations_active, icon: MapPin },
    { label: "Equipment records", value: data.equipment_total, icon: Wrench },
    { label: "Open requests", value: `${data.requests_open} / ${data.requests_total}`, icon: ClipboardList },
  ];

  return (
    <>
      <PageHeader
        title={`Hello, ${user.name.split(" ")[0]}`}
        subtitle={`You manage access and configuration for ${user.organization.name}.`}
        actions={<Link to="/app/users" className="btn btn-primary">Manage users</Link>}
      />
      <div className="stat-grid">
        {stats.map(({ label, value, icon: Icon, danger }) => (
          <div key={label} className={`stat card ${danger ? "stat-danger" : ""}`}>
            <Icon size={18} /><strong>{value}</strong><span>{label}</span>
          </div>
        ))}
      </div>

      <div className="two-col">
        <section className="card">
          <h3>Active people by role</h3>
          <BarList data={data.by_role} />
          {org.data && (
            <div className="code-box">
              <KeyRound size={18} />
              <div>
                <span className="muted small">Employees join with this company code</span>
                <strong className="mono">{org.data.join_code}</strong>
                <span className="muted small">{org.data.allow_self_signup ? "Self sign-up is on" : "Self sign-up is off"}</span>
              </div>
              <Link to="/app/settings" className="btn btn-small btn-secondary">Settings</Link>
            </div>
          )}
        </section>
        <section className="card">
          <div className="card-head">
            <h3>Recent activity</h3>
            <Link to="/app/audit" className="link-strong small">Open audit log</Link>
          </div>
          {data.recent_audit.length === 0 ? <p className="muted">No activity yet.</p> : (
            <ul className="log-list">
              {data.recent_audit.map((a) => (
                <li key={a.id}>
                  <span>{a.detail}</span>
                  <span className="muted small">{a.actor} · {formatDateTime(a.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}
