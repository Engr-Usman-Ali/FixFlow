import { LogOut } from "lucide-react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { GROUP_TITLES, NAV_ITEMS, NavItem } from "../../utils/navigation";
import Logo from "./Logo";

/** Permission-aware navigation: users only see links for areas they may use (FR-003). */
export default function Sidebar({ open, onNavigate }: { open: boolean; onNavigate: () => void }) {
  const { user, logout, can, canAny } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;

  const items = NAV_ITEMS.filter((item) => !item.anyOf || canAny(item.anyOf));
  const groups = (["work", "admin", "me"] as NavItem["group"][])
    .map((g) => ({ g, items: items.filter((i) => i.group === g) }))
    .filter((x) => x.items.length > 0);

  async function signOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`} aria-label="Main navigation">
      <div className="sidebar-top">
        <Logo to="/app" light />
        <span className="sidebar-org" title={user.organization.name}>{user.organization.name}</span>
      </div>

      <nav className="sidebar-nav">
        {groups.map(({ g, items: groupItems }) => (
          <div key={g} className="nav-group">
            <span className="nav-group-title">{GROUP_TITLES[g]}</span>
            {groupItems.map(({ label, to, icon: Icon, end }) => {
              const text = typeof label === "function" ? label(can) : label;
              return (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={onNavigate}
                  className={({ isActive }) => `nav-link ${isActive ? "nav-link-active" : ""}`}
                >
                  <Icon size={18} />
                  {text}
                </NavLink>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="sidebar-user">
        <div className="avatar" aria-hidden="true">{user.name.charAt(0)}</div>
        <div className="sidebar-user-text">
          <strong>{user.name}</strong>
          <span>{user.role}</span>
        </div>
        <button className="icon-btn icon-btn-light" onClick={signOut} aria-label="Sign out" title="Sign out">
          <LogOut size={18} />
        </button>
      </div>
    </aside>
  );
}
