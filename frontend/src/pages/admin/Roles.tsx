// Read-only view of the RBAC matrix enforced by the API (SRS 7.1).
import { Check, Minus } from "lucide-react";
import { userApi } from "../../api/services";
import PageHeader from "../../components/common/PageHeader";
import { ErrorState, Loading } from "../../components/common/States";
import { useAsync } from "../../hooks/useAsync";

export default function RolesPage() {
  const roles = useAsync(() => userApi.roles(), []);
  const perms = useAsync(() => userApi.permissions(), []);

  if ((roles.loading && !roles.data) || (perms.loading && !perms.data)) return <Loading />;
  if (roles.error || perms.error || !roles.data || !perms.data) {
    return <ErrorState message={roles.error ?? perms.error ?? "Could not load roles."} onRetry={() => { roles.reload(); perms.reload(); }} />;
  }

  return (
    <>
      <PageHeader title="Roles & permissions" subtitle="What each role can do. The server checks these on every action." />
      <div className="role-cards">
        {roles.data.map((r) => (
          <article key={r.name} className="card">
            <h3>{r.name}</h3>
            <p className="muted small">{r.description}</p>
            <strong>{r.user_count}</strong> <span className="muted small">active {r.user_count === 1 ? "person" : "people"}</span>
          </article>
        ))}
      </div>

      <div className="card flush table-wrap">
        <table className="table matrix">
          <thead>
            <tr>
              <th>Permission</th>
              {roles.data.map((r) => <th key={r.name}>{r.name}</th>)}
            </tr>
          </thead>
          <tbody>
            {perms.data.map((p) => (
              <tr key={p.code}>
                <td><span className="row-title">{p.description}</span><code className="small">{p.code}</code></td>
                {roles.data!.map((r) => {
                  const has = r.permissions.includes(p.code);
                  return (
                    <td key={r.name} className="matrix-cell">
                      {has ? <Check size={18} className="yes" aria-label="Allowed" /> : <Minus size={16} className="no" aria-label="Not allowed" />}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="muted small">To give someone different powers, change their role on the Users page.</p>
    </>
  );
}
