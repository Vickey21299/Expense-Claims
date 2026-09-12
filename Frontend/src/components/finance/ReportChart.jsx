// ReportChart.jsx — Lightweight CSS-driven chart & table component for Finance Reports.
// Styled to match the Staff & Manager claims-table design system.

export function CategoryBarChart({ data = [] }) {
  if (!data.length) {
    return (
      <div className="empty-state">
        <p className="empty-state__text">No category spend data available.</p>
      </div>
    );
  }

  const maxTotal = Math.max(...data.map((d) => d.total || 0), 1);

  const PALETTE = [
    { bg: "#6366f1", gradient: "linear-gradient(90deg, #6366f1, #818cf8)" },
    { bg: "#10b981", gradient: "linear-gradient(90deg, #10b981, #34d399)" },
    { bg: "#8b5cf6", gradient: "linear-gradient(90deg, #8b5cf6, #a78bfa)" },
    { bg: "#f59e0b", gradient: "linear-gradient(90deg, #f59e0b, #fbbf24)" },
    { bg: "#3b82f6", gradient: "linear-gradient(90deg, #3b82f6, #60a5fa)" },
    { bg: "#14b8a6", gradient: "linear-gradient(90deg, #14b8a6, #2dd4bf)" },
    { bg: "#ec4899", gradient: "linear-gradient(90deg, #ec4899, #f472b6)" },
  ];

  return (
    <div className="report-chart">
      {data.map((item, idx) => {
        const pct = Math.round((item.total / maxTotal) * 100);
        const color = PALETTE[idx % PALETTE.length];

        return (
          <div key={item.category} className="report-chart__row">
            <div className="report-chart__header">
              <span className="report-chart__cat">
                <span className="report-chart__cat-dot" style={{ backgroundColor: color.bg }} />
                {item.category}
              </span>
              <span className="report-chart__val">
                ₹{item.total?.toLocaleString("en-IN")}
                <span className="report-chart__count">({item.count} {item.count === 1 ? "claim" : "claims"})</span>
              </span>
            </div>
            <div className="report-chart__bar-bg">
              <div
                className="report-chart__bar-fill"
                style={{ width: `${Math.max(pct, 4)}%`, background: color.gradient }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function EmployeeSpendTable({ data = [] }) {
  if (!data.length) {
    return (
      <div className="empty-state">
        <p className="empty-state__text">No employee spend data available.</p>
      </div>
    );
  }

  const maxTotal = Math.max(...data.map((d) => d.total || 0), 1);

  return (
    <div className="claim-table-wrap">
      <div className="table-container">
        <table className="claims-table" aria-label="Employee reimbursement breakdown">
          <thead>
            <tr>
              <th>Employee</th>
              <th className="text-center">Claims Count</th>
              <th className="text-right">Total Claimed</th>
              <th className="text-right">Disbursed (Paid)</th>
              <th className="text-right">Pending Review</th>
              <th className="text-right">Spend Share</th>
            </tr>
          </thead>
          <tbody>
            {data.map((emp) => {
              const sharePct = Math.round(((emp.total || 0) / maxTotal) * 100);
              const initials = emp.name
                ? emp.name
                    .split(" ")
                    .map((n) => n[0])
                    .join("")
                    .slice(0, 2)
                : "E";

              return (
                <tr key={emp.name} className="claims-table__row">
                  <td>
                    <div className="employee-row">
                      <div className="employee-avatar-sm" aria-hidden="true">
                        {initials}
                      </div>
                      <div className="claims-table__employee">
                        <span className="employee-name">{emp.name}</span>
                        <span className="claim-id">{emp.department || "Engineering"}</span>
                      </div>
                    </div>
                  </td>
                  <td className="text-center">
                    <span className="claims-table__category" style={{ fontWeight: 600 }}>
                      {emp.count} {emp.count === 1 ? "claim" : "claims"}
                    </span>
                  </td>
                  <td className="claims-table__amount text-right">
                    ₹{emp.total?.toLocaleString("en-IN")}
                  </td>
                  <td className="claims-table__amount text-right text-success">
                    ₹{emp.approved?.toLocaleString("en-IN")}
                  </td>
                  <td className="claims-table__amount text-right text-warning">
                    ₹{emp.pending?.toLocaleString("en-IN")}
                  </td>
                  <td>
                    <div className="spend-share-cell">
                      <div className="spend-share-bar">
                        <div
                          className="spend-share-fill"
                          style={{ width: `${Math.max(sharePct, 6)}%` }}
                        />
                      </div>
                      <span className="spend-share-bar__label">{sharePct}%</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
