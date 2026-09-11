// FinanceReports.jsx — Financial reporting page matching Manager CSS design system.

import { useState, useEffect } from "react";
import { BarChart3, TrendingUp, Users, AlertCircle } from "lucide-react";
import StatCard from "../../components/common/StatCard";
import { getFinanceReports } from "../../services/api";
import { CategoryBarChart, EmployeeSpendTable } from "../../components/finance/ReportChart";

function formatAmount(amount) {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function FinanceReports() {
  const [period, setPeriod] = useState("all");
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReport();
  }, [period]);

  async function loadReport() {
    try {
      setLoading(true);
      const data = await getFinanceReports({ period });
      setReportData(data);
    } catch (err) {
      console.error("Error loading financial reports", err);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Calculating analytics…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-header__title">Financial Reports & Analytics</h1>
          <p className="page-header__subtitle">
            Spend distribution across categories, employee reimbursement totals, and policy limit compliance.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <select
            id="report-period-select"
            className="form-select"
            style={{ width: "auto", padding: "6px 12px", fontSize: "13px" }}
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          >
            <option value="all">All Time</option>
            <option value="this_month">This Month</option>
            <option value="last_month">Last Month</option>
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="stat-grid">
        <StatCard
          label="Total Spend Claimed"
          value={formatAmount(reportData?.totalSpend)}
          icon={TrendingUp}
          colorClass="stat-card--teal"
        />
        <StatCard
          label="Disbursed (Paid)"
          value={formatAmount(reportData?.paidAmount)}
          icon={BarChart3}
          colorClass="stat-card--green"
        />
        <StatCard
          label="Pending Verification"
          value={formatAmount(reportData?.pendingAmount)}
          icon={Users}
          colorClass="stat-card--amber"
        />
        <StatCard
          label="Flagged Exceptions"
          value={formatAmount(reportData?.flaggedAmount)}
          icon={AlertCircle}
          colorClass="stat-card--purple"
        />
      </div>

      {/* Content grid */}
      <div className="detail-grid" style={{ marginTop: "24px" }}>
        {/* Left Column: Category Chart */}
        <div className="detail-col">
          <div className="card">
            <h2 className="card__title">Category Spend Breakdown</h2>
            <div style={{ marginTop: "16px" }}>
              <CategoryBarChart data={reportData?.categoryBreakdown || []} />
            </div>
          </div>
        </div>

        {/* Right Column: Policy Warning Card */}
        <div className="detail-col">
          <div className="card">
            <h2 className="card__title">Policy Compliance & Threshold Alerts</h2>
            <div style={{ marginTop: "12px", display: "flex", flexDirection: "column", gap: "12px" }}>
              <div className="alert-box alert-box--warning" style={{ fontSize: "13px" }}>
                <div>
                  <strong>Max Per-Claim Policy Limit (₹10,000)</strong>
                  <p style={{ margin: 0 }}>
                    All submitted claims strictly adhere to the ₹10,000 maximum per-claim limit rule.
                  </p>
                </div>
              </div>
              <div className="alert-box alert-box--info" style={{ fontSize: "13px" }}>
                <div>
                  <strong>Audit Requirement</strong>
                  <p style={{ margin: 0 }}>
                    Claims above ₹5,000 require complete GST invoice match prior to clearing.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Employee spend table */}
      <div className="card" style={{ marginTop: "24px" }}>
        <h2 className="card__title">Employee Reimbursement Breakdown</h2>
        <div style={{ marginTop: "16px" }}>
          <EmployeeSpendTable data={reportData?.employeeSpend || []} />
        </div>
      </div>
    </div>
  );
}
