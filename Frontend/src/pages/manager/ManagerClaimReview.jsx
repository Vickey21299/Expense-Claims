import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft, User, Calendar, Tag, FileText, DollarSign,
  Building2, CheckCircle2, XCircle, ShieldAlert, ShieldCheck,
  AlertTriangle, Bot, Layers, Check,
} from "lucide-react";
import StatusBadge from "../../components/common/StatusBadge";
import ClaimHistory from "../../components/claims/ClaimHistory";
import ReceiptPreview from "../../components/claims/ReceiptPreview";
import ReviewConfirmation from "../../components/manager/ReviewConfirmation";
import { getManagerClaim, approveClaim, confirmClaimContext, rejectClaim } from "../../services/api";
import { CURRENT_MANAGER } from "../../data/users";

function formatDate(dateStr) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function formatAmount(amount, currency = "INR") {
  if (!amount && amount !== 0) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

function DetailRow({ icon: Icon, label, value }) {
  return (
    <div className="detail-row">
      <div className="detail-row__icon">
        <Icon size={15} strokeWidth={1.75} />
      </div>
      <div className="detail-row__body">
        <p className="detail-row__label">{label}</p>
        <p className="detail-row__value">{value || "—"}</p>
      </div>
    </div>
  );
}

const REVIEWABLE_STATUSES = ["SUBMITTED", "UNDER_REVIEW", "FLAGGED"];

export default function ManagerClaimReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modal, setModal] = useState(null); // "approve" | "confirm_context" | "reject" | null
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  useEffect(() => {
    setLoading(true);
    getManagerClaim(id)
      .then((data) => {
        setClaim(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  // Self-claim check
  const isSelfClaim = claim?.employee?.id === (CURRENT_MANAGER.uuid || CURRENT_MANAGER.id);
  const isFlagged = claim?.status === "FLAGGED" || claim?.verification_status === "FLAGGED";
  const canReview = !isSelfClaim && REVIEWABLE_STATUSES.includes(claim?.status);

  async function handleApprove(comment) {
    setActionLoading(true);
    setActionMessage(null);
    try {
      const updated = await approveClaim(id, comment);
      setClaim(updated);
      setModal(null);
      setActionMessage({ type: "success", text: "Clean claim approved successfully and queued for payment." });
    } catch (err) {
      console.error("Approve failed:", err);
      setActionMessage({ type: "error", text: err.message || "Approval failed" });
    }
    setActionLoading(false);
  }

  async function handleConfirmContext(comment) {
    setActionLoading(true);
    setActionMessage(null);
    try {
      const updated = await confirmClaimContext(id, comment);
      setClaim(updated);
      setModal(null);
      setActionMessage({ type: "success", text: "Business context confirmed. Claim forwarded to Finance for clearance." });
    } catch (err) {
      console.error("Confirm context failed:", err);
      setActionMessage({ type: "error", text: err.message || "Confirmation failed" });
    }
    setActionLoading(false);
  }

  async function handleReject(reason) {
    setActionLoading(true);
    setActionMessage(null);
    try {
      const updated = await rejectClaim(id, reason);
      setClaim(updated);
      setModal(null);
      setActionMessage({ type: "success", text: "Claim rejected." });
    } catch (err) {
      console.error("Reject failed:", err);
      setActionMessage({ type: "error", text: err.message || "Rejection failed" });
    }
    setActionLoading(false);
  }

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading claim dossier…</p>
        </div>
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>{error || "Claim not found."}</p>
          <button className="btn btn--ghost" onClick={() => navigate("/manager/claims")}>
            Back to Team Claims
          </button>
        </div>
      </div>
    );
  }

  const llm = claim.llm_analysis;
  const candidates = claim.matched_candidates || [];

  return (
    <div className="page-content">
      {/* Back */}
      <button
        id="mgr-review-back-btn"
        className="btn btn--ghost btn--sm back-btn"
        onClick={() => navigate("/manager/claims")}
      >
        <ArrowLeft size={15} strokeWidth={2} />
        Back to Team Claims
      </button>

      {/* Action Notification Toast */}
      {actionMessage && (
        <div className={`alert-banner ${actionMessage.type === "success" ? "alert-banner--success" : "alert-banner--error"}`} style={{ marginBottom: "16px" }}>
          {actionMessage.type === "success" ? <Check size={16} /> : <AlertTriangle size={16} />}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {/* Header */}
      <div className="page-header page-header--compact">
        <div>
          <div className="page-header__meta">
            <span className="claim-id-label">{claim.claimRef || claim.id}</span>
            <StatusBadge status={claim.status} />
            {isFlagged && <StatusBadge status="FLAGGED" />}
          </div>
          <h1 className="page-header__title">
            {claim.merchant || "Claim Review"}
          </h1>
          <p className="page-header__subtitle">
            {claim.employee?.name} · {claim.category} · Expense Date: {formatDate(claim.date)}
          </p>
        </div>

        <div className="claim-amount-hero">
          <p className="claim-amount-hero__label">Amount</p>
          <p className="claim-amount-hero__value">
            {formatAmount(claim.amount, claim.currency)}
          </p>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="detail-grid">
        {/* Left column */}
        <div className="detail-col">
          {/* Expense Details */}
          <div className="card">
            <h2 className="card__title">Expense Information</h2>
            <div className="detail-rows">
              <DetailRow icon={Building2} label="Merchant" value={claim.merchant} />
              <DetailRow icon={DollarSign} label="Amount" value={formatAmount(claim.amount, claim.currency)} />
              <DetailRow icon={Tag} label="Category" value={claim.category} />
              <DetailRow icon={Calendar} label="Expense Date" value={formatDate(claim.date)} />
              {claim.submittedAt && (
                <DetailRow icon={Calendar} label="Submitted At" value={formatDate(claim.submittedAt)} />
              )}
              {claim.description && (
                <DetailRow icon={FileText} label="Description" value={claim.description} />
              )}
            </div>
          </div>

          {/* Employee Information */}
          <div className="card">
            <h2 className="card__title">Employee Details</h2>
            <div className="manager-row" style={{ marginBottom: "12px" }}>
              <div className="manager-avatar" aria-hidden="true">
                {claim.employee?.name?.charAt(0) || "E"}
              </div>
              <div>
                <p className="manager-name">{claim.employee?.name || "—"}</p>
                <p className="manager-meta">
                  {claim.employee?.department} · {claim.employee?.role}
                </p>
                {claim.employee?.email && (
                  <p className="manager-meta" style={{ fontSize: "12px", color: "var(--muted, #64748b)" }}>
                    {claim.employee?.email}
                  </p>
                )}
              </div>
            </div>
            <div className="detail-rows" style={{ borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
              <DetailRow
                icon={User}
                label="Assigned Manager"
                value="You (Rahul Sharma)"
              />
            </div>
          </div>

          {/* AI Forensic Intelligence Card */}
          {(llm || isFlagged || candidates.length > 0) && (
            <div className="card" style={{ border: isFlagged ? "1px solid rgba(245, 158, 11, 0.4)" : "1px solid var(--border)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
                <h2 className="card__title" style={{ display: "flex", alignItems: "center", gap: "8px", margin: 0 }}>
                  <Bot size={18} color="var(--primary, #3b82f6)" />
                  AI Verification & Forensic Analysis
                </h2>
                {claim.risk_classification && (
                  <span
                    style={{
                      padding: "4px 8px",
                      borderRadius: "6px",
                      fontSize: "12px",
                      fontWeight: 700,
                      backgroundColor: claim.duplicate_risk_percentage >= 70 ? "rgba(239, 68, 68, 0.15)" : "rgba(245, 158, 11, 0.15)",
                      color: claim.duplicate_risk_percentage >= 70 ? "#ef4444" : "#f59e0b",
                    }}
                  >
                    {claim.risk_classification} ({claim.duplicate_risk_percentage}% duplicate risk)
                  </span>
                )}
              </div>

              {llm?.manager_recommendation && (
                <div style={{ padding: "12px", borderRadius: "8px", backgroundColor: "rgba(59, 130, 246, 0.08)", marginBottom: "12px", borderLeft: "3px solid #3b82f6" }}>
                  <p style={{ fontWeight: 600, fontSize: "13px", color: "#1d4ed8", margin: "0 0 4px 0" }}>
                    Automated Recommendation:
                  </p>
                  <p style={{ fontSize: "13px", color: "var(--foreground, #1e293b)", margin: 0, lineHeight: 1.5 }}>
                    {llm.manager_recommendation}
                  </p>
                </div>
              )}

              {llm?.reasoning && (
                <div style={{ marginBottom: "12px" }}>
                  <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted, #64748b)", margin: "0 0 4px 0" }}>
                    Forensic Reasoning:
                  </p>
                  <p style={{ fontSize: "13px", color: "var(--foreground, #334155)", margin: 0, lineHeight: 1.5 }}>
                    {llm.reasoning}
                  </p>
                </div>
              )}

              {/* Matched Candidates List */}
              {candidates.length > 0 && (
                <div style={{ marginTop: "12px", borderTop: "1px solid var(--border)", paddingTop: "12px" }}>
                  <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--muted, #64748b)", margin: "0 0 8px 0" }}>
                    Matched Historical Claims:
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {candidates.map((cand, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: "10px",
                          borderRadius: "6px",
                          backgroundColor: "rgba(0,0,0,0.02)",
                          border: "1px solid var(--border)",
                          fontSize: "12px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                          <span style={{ fontWeight: 600 }}>{cand.claim_ref || "Claim"} · {cand.merchant_name}</span>
                          <span style={{ fontWeight: 600, color: "#f59e0b" }}>
                            {Math.round((cand.similarity_score || 0) * 100)}% match
                          </span>
                        </div>
                        <div style={{ display: "flex", gap: "12px", color: "var(--muted, #64748b)", marginBottom: "4px" }}>
                          <span>Amount: {formatAmount(cand.amount)}</span>
                          <span>Date: {formatDate(cand.expense_date)}</span>
                          <span>{cand.is_same_employee ? "Same employee" : "Different employee"}</span>
                        </div>
                        {cand.match_reasons && cand.match_reasons.length > 0 && (
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                            {cand.match_reasons.map((r, rIdx) => (
                              <span key={rIdx} style={{ fontSize: "11px", padding: "2px 6px", borderRadius: "4px", backgroundColor: "rgba(245, 158, 11, 0.1)", color: "#b45309" }}>
                                {r}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* History */}
          <div className="card">
            <ClaimHistory history={claim.history || []} claim={claim} />
          </div>
        </div>

        {/* Right column */}
        <div className="detail-col">
          <div className="card">
            <ReceiptPreview receiptUrl={claim.receiptUrl} merchant={claim.merchant} />
          </div>

          {/* Manager Decision Panel */}
          <div className="card review-decision">
            <h2 className="card__title">Manager Decision Panel</h2>

            {/* Already decided banners */}
            {claim.status === "READY_FOR_PAYMENT" && (
              <div className="review-decision__result review-decision__result--approved">
                <CheckCircle2 size={18} strokeWidth={2} />
                <div>
                  <p className="review-decision__status">Approved & Ready for Payment</p>
                  <p className="review-decision__comment">Clean claim approved by manager. Forwarded to Finance payout queue.</p>
                </div>
              </div>
            )}

            {claim.status === "MANAGER_CONFIRMED" && (
              <div className="review-decision__result review-decision__result--approved" style={{ backgroundColor: "rgba(59, 130, 246, 0.1)", borderColor: "#3b82f6" }}>
                <ShieldCheck size={18} strokeWidth={2} color="#2563eb" />
                <div>
                  <p className="review-decision__status" style={{ color: "#1d4ed8" }}>Business Context Confirmed</p>
                  <p className="review-decision__comment">You confirmed the business context for this flagged claim. It is currently in the Finance Queue awaiting clearance.</p>
                </div>
              </div>
            )}

            {claim.status === "APPROVED" && (
              <div className="review-decision__result review-decision__result--approved">
                <CheckCircle2 size={18} strokeWidth={2} />
                <div>
                  <p className="review-decision__status">Approved</p>
                  <p className="review-decision__comment">Claim approved and forwarded for processing.</p>
                </div>
              </div>
            )}

            {claim.status === "REJECTED" && (
              <div className="review-decision__result review-decision__result--rejected">
                <XCircle size={18} strokeWidth={2} />
                <div>
                  <p className="review-decision__status">Rejected</p>
                  <p className="review-decision__comment">This claim was rejected.</p>
                </div>
              </div>
            )}

            {claim.status === "PAID" && (
              <div className="review-decision__result review-decision__result--approved">
                <CheckCircle2 size={18} strokeWidth={2} />
                <div>
                  <p className="review-decision__status">Settled & Paid</p>
                  <p className="review-decision__comment">Payment has been disbursed for this claim.</p>
                </div>
              </div>
            )}

            {/* Self-claim warning */}
            {isSelfClaim && REVIEWABLE_STATUSES.includes(claim.status) && (
              <div className="review-decision__self-claim">
                <ShieldAlert size={18} strokeWidth={2} />
                <p>Self-approval is blocked. This claim requires review by your manager.</p>
              </div>
            )}

            {/* Flagged notice */}
            {canReview && isFlagged && (
              <div style={{ padding: "10px", borderRadius: "6px", backgroundColor: "rgba(245, 158, 11, 0.1)", border: "1px solid rgba(245, 158, 11, 0.3)", marginBottom: "14px", fontSize: "13px", color: "#92400e" }}>
                <p style={{ margin: 0, fontWeight: 600 }}>⚠️ Anomaly Action Required:</p>
                <p style={{ margin: "4px 0 0 0", lineHeight: 1.4 }}>
                  This claim is FLAGGED. Direct auto-approval is blocked. Please confirm the business context with justification, or reject it.
                </p>
              </div>
            )}

            {/* Action buttons */}
            {canReview && (
              <div className="review-decision__actions">
                <button
                  id="mgr-reject-btn"
                  className="btn btn--danger"
                  onClick={() => setModal("reject")}
                  disabled={actionLoading}
                >
                  <XCircle size={15} strokeWidth={2} />
                  Reject
                </button>

                {isFlagged ? (
                  <button
                    id="mgr-confirm-context-btn"
                    className="btn btn--warning"
                    onClick={() => setModal("confirm_context")}
                    disabled={actionLoading}
                    style={{ backgroundColor: "#f59e0b", color: "#fff", borderColor: "#d97706" }}
                  >
                    <ShieldCheck size={15} strokeWidth={2} />
                    Confirm Business Context
                  </button>
                ) : (
                  <button
                    id="mgr-approve-btn"
                    className="btn btn--primary"
                    onClick={() => setModal("approve")}
                    disabled={actionLoading}
                  >
                    <CheckCircle2 size={15} strokeWidth={2} />
                    Approve
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Confirmation modal */}
      {modal && (
        <ReviewConfirmation
          mode={modal}
          claim={claim}
          onConfirm={
            modal === "approve"
              ? handleApprove
              : modal === "confirm_context"
              ? handleConfirmContext
              : handleReject
          }
          onCancel={() => setModal(null)}
          loading={actionLoading}
        />
      )}
    </div>
  );
}
