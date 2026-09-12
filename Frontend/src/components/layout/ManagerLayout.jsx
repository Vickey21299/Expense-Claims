// ManagerLayout — main layout shell for all manager pages.
// Mirrors StaffLayout structure but with Manager-specific navigation.

import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, Users, Receipt } from "lucide-react";
import { CURRENT_MANAGER } from "../../data/users";
import RoleSwitcher from "../common/RoleSwitcher";

const NAV_ITEMS = [
  { to: "/manager", label: "Dashboard", icon: LayoutDashboard, end: true, id: "nav-mgr-dashboard" },
  { to: "/manager/claims", label: "Team Claims", icon: Users, end: false, id: "nav-mgr-claims" },
];

export default function ManagerLayout() {
  const navigate = useNavigate();

  return (
    <div className="staff-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar" aria-label="Manager navigation">
        <div className="sidebar__brand" onClick={() => navigate("/manager")} role="button" tabIndex={0}>
          <div className="sidebar__brand-icon">
            <Receipt size={20} strokeWidth={2} />
          </div>
          <span className="sidebar__brand-name">ExpenseCo</span>
        </div>

        <nav className="sidebar__nav">
          <ul role="list">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  id={item.id}
                  className={({ isActive }) =>
                    `sidebar__nav-item ${isActive ? "sidebar__nav-item--active" : ""}`
                  }
                >
                  <item.icon size={18} strokeWidth={1.75} />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        <RoleSwitcher />

        <div className="sidebar__user">
          <div className="sidebar__avatar" aria-hidden="true">
            {CURRENT_MANAGER.name.charAt(0)}
          </div>
          <div className="sidebar__user-info">
            <p className="sidebar__user-name">{CURRENT_MANAGER.name}</p>
            <p className="sidebar__user-role">Manager</p>
          </div>
        </div>
      </aside>

      {/* ── Main content ── */}
      <div className="staff-main">
        <Outlet />
      </div>
    </div>
  );
}
