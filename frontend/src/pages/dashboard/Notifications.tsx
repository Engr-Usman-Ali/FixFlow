import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { notificationApi } from "../../api/services";
import PageHeader from "../../components/common/PageHeader";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import { useAsync } from "../../hooks/useAsync";
import type { NotificationItem } from "../../types";
import { timeAgo } from "../../utils/format";

/** FR-063: the user's own notifications, unread clearly marked. */
export default function Notifications() {
  const navigate = useNavigate();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { data, loading, error, reload } = useAsync(() => notificationApi.list(unreadOnly), [unreadOnly]);
  const refreshBell = () => window.dispatchEvent(new Event("fixflow:notifications-changed"));

  async function open(n: NotificationItem) {
    if (!n.read_at) await notificationApi.markRead(n.id).catch(() => undefined);
    refreshBell();
    if (n.request_id) navigate(`/app/requests/${n.request_id}`);
    else reload();
  }

  async function markAll() {
    await notificationApi.markAllRead();
    refreshBell();
    reload();
  }

  if (loading && !data) return <Loading />;
  if (error || !data) return <ErrorState message={error ?? "Could not load notifications."} onRetry={reload} />;
  const hasUnread = data.some((n) => !n.read_at);

  return (
    <>
      <PageHeader
        title="Notifications"
        subtitle="Updates about requests you are involved in."
        actions={
          <>
            <label className="check">
              <input type="checkbox" checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} /> Unread only
            </label>
            <button className="btn btn-secondary" onClick={markAll} disabled={!hasUnread}>Mark all as read</button>
          </>
        }
      />
      {data.length === 0 ? (
        <EmptyState title="You are all caught up" text="Assignments, status changes and comments will appear here." />
      ) : (
        <ul className="card flush notif-list">
          {data.map((n) => (
            <li key={n.id}>
              <button className={`notif ${n.read_at ? "" : "notif-unread"}`} onClick={() => open(n)}>
                <span className="notif-dot" aria-hidden="true" />
                <span className="notif-text">
                  {!n.read_at && <span className="sr-only">Unread: </span>}
                  {n.message}
                </span>
                {!n.read_at && <span className="pill">New</span>}
                <span className="muted small nowrap">{timeAgo(n.created_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
