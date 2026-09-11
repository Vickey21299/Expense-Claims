// ReportChart.jsx — Lightweight CSS-driven chart component for Finance Reports.

export function CategoryBarChart({ data = [] }) {
  if (!data.length) return <div className="text-muted text-xs p-4">No data available.</div>;

  const maxTotal = Math.max(...data.map((d) => d.total || 0), 1);

  const colors = [
    "bg-indigo-500",
    "bg-emerald-500",
    "bg-purple-500",
    "bg-amber-500",
    "bg-blue-500",
    "bg-teal-500",
    "bg-rose-500",
  ];

  return (
    <div className="report-chart space-y-3">
      {data.map((item, idx) => {
        const pct = Math.round((item.total / maxTotal) * 100);
        const colorClass = colors[idx % colors.length];

        return (
          <div key={item.category} className="report-chart__row">
            <div className="flex justify-between text-xs mb-1">
              <span className="font-medium text-slate-700">{item.category}</span>
              <span className="font-mono text-slate-600">
                ₹{item.total?.toLocaleString()} ({item.count} claims)
              </span>
            </div>
            <div className="report-chart__bar-bg">
              <div
                className={`report-chart__bar-fill ${colorClass}`}
                style={{ width: `${Math.max(pct, 4)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function EmployeeSpendTable({ data = [] }) {
  if (!data.length) return <div className="text-muted text-xs p-4">No employee spend data.</div>;

  return (
    <div className="table-responsive">
      <table className="table">
        <thead>
          <tr>
            <th>Employee</th>
            <th>Claims</th>
            <th>Total Claimed</th>
            <th>Approved / Paid</th>
            <th>Pending</th>
          </tr>
        </thead>
        <tbody>
          {data.map((emp) => (
            <tr key={emp.name}>
              <td className="font-medium">{emp.name}</td>
              <td>{emp.count}</td>
              <td className="font-mono font-semibold">₹{emp.total?.toLocaleString()}</td>
              <td className="font-mono text-emerald-600 font-medium">₹{emp.approved?.toLocaleString()}</td>
              <td className="font-mono text-amber-600">₹{emp.pending?.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
