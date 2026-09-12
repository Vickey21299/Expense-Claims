// FinancePayments.jsx — Payment processing queue matching Manager CSS design.

import { useState, useEffect } from "react";
import { CreditCard, CheckCircle2, IndianRupee } from "lucide-react";
import StatCard from "../../components/common/StatCard";
import StatusBadge from "../../components/common/StatusBadge";
import { getFinanceClaims, payClaim } from "../../services/api";
import PaymentConfirmation from "../../components/finance/PaymentConfirmation";

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export default function FinancePayments() {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [activeTab, setActiveTab] = useState("READY"); // 'READY' | 'PAID'

  useEffect(() => {
    loadPaymentData();
  }, []);

  async function loadPaymentData() {
    try {
      setLoading(true);
      const data = await getFinanceClaims();
      setClaims(data);
    } catch (err) {
      console.error("Error loading payment data", err);
    } finally {
      setLoading(false);
    }
  }

  const readyToPay = claims.filter((c) => c.status === "READY_FOR_PAYMENT");
  const paidClaims = claims.filter((c) => c.status === "PAID");

  const totalReadyAmount = readyToPay.reduce((sum, c) => sum + (c.amount || 0), 0);
  const totalPaidAmount = paidClaims.reduce((sum, c) => sum + (c.amount || 0), 0);

  const handleOpenPaymentModal = (claim) => {
    setSelectedClaim(claim);
    setIsModalOpen(true);
  };

  const handleConfirmPayment = async (claimId) => {
    setProcessing(true);
    try {
      const updated = await payClaim(claimId);
      await loadPaymentData();
      return updated;
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading payments queue…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-header__title">Disbursement & Payments</h1>
          <p className="page-header__subtitle">
            Manage reimbursement payments, trigger disbursements, and view bank transfer references.
          </p>
        </div>
      </div>

      {/* Stats */}
      <div className="stat-grid">
        <StatCard
          label="Pending Disbursement"
          value={formatAmount(totalReadyAmount)}
          icon={CreditCard}
          colorClass="stat-card--green"
        />
        <StatCard
          label="Total Paid Out"
          value={formatAmount(totalPaidAmount)}
          icon={CheckCircle2}
          colorClass="stat-card--teal"
        />
      </div>

      {/* Table & Filter tabs */}
      <div className="claim-table-wrap">
        <div className="filter-bar" role="tablist" aria-label="Filter payments">
          <button
            role="tab"
            aria-selected={activeTab === "READY"}
            className={`filter-tab ${activeTab === "READY" ? "filter-tab--active" : ""}`}
            onClick={() => setActiveTab("READY")}
          >
            Ready for Payment ({readyToPay.length})
          </button>
          <button
            role="tab"
            aria-selected={activeTab === "PAID"}
            className={`filter-tab ${activeTab === "PAID" ? "filter-tab--active" : ""}`}
            onClick={() => setActiveTab("PAID")}
          >
            Payment History ({paidClaims.length})
          </button>
        </div>

        {activeTab === "READY" ? (
          readyToPay.length === 0 ? (
            <div className="empty-state">
              <p className="empty-state__text">All cleared claims have been paid! 🎉</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="claims-table" aria-label="Ready for payment">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Merchant & Ref</th>
                    <th>Category</th>
                    <th className="text-right">Amount</th>
                    <th>Finance Clearance Note</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {readyToPay.map((claim) => {
                    const empName = claim.employee?.name || "Employee";
                    const initials = empName.split(" ").map((n) => n[0]).join("").slice(0, 2);

                    return (
                      <tr key={claim.id} className="claims-table__row">
                        <td>
                          <div className="employee-row">
                            <div className="employee-avatar-sm" aria-hidden="true">
                              {initials}
                            </div>
                            <div className="claims-table__employee">
                              <span className="employee-name">{empName}</span>
                              <span className="claim-id">{claim.employee?.department || "Engineering"}</span>
                            </div>
                          </div>
                        </td>
                        <td className="claims-table__merchant">
                          <span className="merchant-name">{claim.merchant}</span>
                          <span className="claim-id">{claim.claimRef || claim.claim_ref || claim.id}</span>
                        </td>
                        <td className="claims-table__category">{claim.category}</td>
                        <td className="claims-table__amount text-right">
                          {formatAmount(claim.amount, claim.currency)}
                        </td>
                        <td>
                          <span style={{ fontSize: "13px", color: "var(--text)" }}>
                            {claim.financeVerification?.comment || claim.reviewComment || "Cleared for reimbursement payout"}
                          </span>
                        </td>
                        <td className="text-right">
                          <button
                            id={`btn-pay-now-${claim.id}`}
                            className="btn btn--primary btn--sm"
                            onClick={() => handleOpenPaymentModal(claim)}
                          >
                            Disburse Funds
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        ) : paidClaims.length === 0 ? (
          <div className="empty-state">
            <p className="empty-state__text">No completed payments found.</p>
          </div>
        ) : (
          <div className="table-container">
            <table className="claims-table" aria-label="Payment history">
              <thead>
                <tr>
                  <th>Payment Ref</th>
                  <th>Employee</th>
                  <th>Merchant & Ref</th>
                  <th className="text-right">Amount Disbursed</th>
                  <th>Settlement Status</th>
                </tr>
              </thead>
              <tbody>
                {paidClaims.map((claim) => {
                  const empName = claim.employee?.name || "Employee";
                  const initials = empName.split(" ").map((n) => n[0]).join("").slice(0, 2);

                  return (
                    <tr key={claim.id} className="claims-table__row">
                      <td>
                        <span style={{ fontFamily: "var(--mono)", fontSize: "12.5px", fontWeight: "600", color: "var(--accent)" }}>
                          {claim.paymentReference || "PAY-ARCHIVED"}
                        </span>
                      </td>
                      <td>
                        <div className="employee-row">
                          <div className="employee-avatar-sm" aria-hidden="true">
                            {initials}
                          </div>
                          <div className="claims-table__employee">
                            <span className="employee-name">{empName}</span>
                            <span className="claim-id">{claim.employee?.department || "Engineering"}</span>
                          </div>
                        </div>
                      </td>
                      <td className="claims-table__merchant">
                        <span className="merchant-name">{claim.merchant}</span>
                        <span className="claim-id">{claim.claimRef || claim.claim_ref || claim.id}</span>
                      </td>
                      <td className="claims-table__amount text-right text-success">
                        {formatAmount(claim.amount, claim.currency)}
                      </td>
                      <td className="claims-table__status">
                        <StatusBadge status="PAID" />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal */}
      <PaymentConfirmation
        claim={selectedClaim}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedClaim(null);
        }}
        onConfirm={handleConfirmPayment}
        loading={processing}
      />
    </div>
  );
}
