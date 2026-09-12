// FinanceLayout — sidebar layout shell for all Finance pages.
// Mirrors ManagerLayout pattern.

import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LayoutDashboard, ShieldCheck, CreditCard, BarChart3, Receipt } from "lucide-react";
import { CURRENT_FINANCE } from "../../data/users";
import RoleSwitcher from "../common/RoleSwitcher";

const NAV_ITEMS = [
  { to: "/finance", label: "Dashboard", icon: LayoutDashboard, end: true, id: "nav-fin-dashboard" },
  { to: "/finance/verification", label: "Verification Queue", icon: ShieldCheck, end: false, id: "nav-fin-verification" },
  { to: "/finance/payments", label: "Payments", icon: CreditCard, end: false, id: "nav-fin-payments" },
  { to: "/finance/reports", label: "Reports", icon: BarChart3, end: false, id: "nav-fin-reports" },
];

export default function FinanceLayout() {
  const navigate = useNavigate();

  return (
    <div className="staff-layout">
      {/* ── Sidebar ── */}
      <aside className="sidebar sidebar--finance" aria-label="Finance navigation">
        <div
          className="sidebar__brand"
          onClick={() => navigate("/finance")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && navigate("/finance")}
        >
          <div className="sidebar__brand-icon sidebar__brand-icon--finance">
            <Receipt size={20} strokeWidth={2} />
          </div>
          <span className="sidebar__brand-name">ExpenseCo</span>
        </div>

        <div className="sidebar__role-badge sidebar__role-badge--finance">Finance</div>

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
          <div className="sidebar__avatar sidebar__avatar--finance" aria-hidden="true">
            {CURRENT_FINANCE.name.charAt(0)}
          </div>
          <div className="sidebar__user-info">
            <p className="sidebar__user-name">{CURRENT_FINANCE.name}</p>
            <p className="sidebar__user-role">Finance Controller</p>
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
