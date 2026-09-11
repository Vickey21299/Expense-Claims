// StaffLayout — main layout shell for all staff pages.
// Contains the fixed sidebar, top bar, and <Outlet /> for page content.

import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, FileText, PlusCircle, Receipt } from "lucide-react";
import { CURRENT_USER } from "../../data/mockClaims";
import RoleSwitcher from "../common/RoleSwitcher";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true, id: "nav-dashboard" },
  { to: "/claims", label: "My Claims", icon: FileText, end: false, id: "nav-my-claims" },
  { to: "/add-expense", label: "Add Expense", icon: PlusCircle, end: false, id: "nav-add-expense" },
];

export default function StaffLayout() {
  const navigate = useNavigate();

  return (
    <div className="staff-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar" aria-label="Staff navigation">
        <div className="sidebar__brand" onClick={() => navigate("/")} role="button" tabIndex={0}>
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
            {CURRENT_USER.name.charAt(0)}
          </div>
          <div className="sidebar__user-info">
            <p className="sidebar__user-name">{CURRENT_USER.name}</p>
            <p className="sidebar__user-role">Staff</p>
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
