import { Bell, Menu } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useUnreadCount } from "../../hooks/useUnreadCount";

export default function Topbar({ onMenu }: { onMenu: () => void }) {
  const { user } = useAuth();
  const unread = useUnreadCount();

  return (
    <header className="topbar">
      <button className="icon-btn menu-btn" onClick={onMenu} aria-label="Open menu"><Menu size={20} /></button>
      <span className="topbar-org">{user?.organization.name}</span>
      <div className="topbar-spacer" />
      <Link to="/app/notifications" className="icon-btn bell" aria-label={`Notifications, ${unread} unread`}>
        <Bell size={20} />
        {unread > 0 && <span className="bell-count">{unread > 9 ? "9+" : unread}</span>}
      </Link>
      <Link to="/app/profile" className="role-chip" title="My profile">{user?.role}</Link>
    </header>
  );
}
