// FinanceClaimReview.jsx — Detailed audit and action page for Finance Controller.

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  User,
  Calendar,
  Tag,
  FileText,
  DollarSign,
  Building2,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  CreditCard,
  Bot,
  Sparkles,
} from "lucide-react";
import StatusBadge from "../../components/common/StatusBadge";
import ClaimHistory from "../../components/claims/ClaimHistory";
import ReceiptPreview from "../../components/claims/ReceiptPreview";
import DuplicateAlert from "../../components/claims/DuplicateAlert";
import VerificationChecks from "../../components/claims/VerificationChecks";
import FinanceActionPanel from "../../components/finance/FinanceActionPanel";
import {
  getFinanceClaim,
  verifyClaim,
  clearFinancialException,
  confirmDuplicate,
  financeRejectClaim,
} from "../../services/api";

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

export default function FinanceClaimReview() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadClaimData();
  }, [id]);

  async function loadClaimData() {
    try {
      setLoading(true);
      const data = await getFinanceClaim(id);
      setClaim(data);
    } catch (err) {
      setError(err.message || "Claim not found");
    } finally {
      setLoading(false);
    }
  }

  const handleVerify = async (comment) => {
    setActionLoading(true);
    try {
      const updated = await verifyClaim(id, comment);
      setClaim(updated);
    } catch (err) {
      alert(err.message || "Verification failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleClearException = async (comment) => {
    setActionLoading(true);
    try {
      const updated = await clearFinancialException(id, comment);
      setClaim(updated);
    } catch (err) {
      alert(err.message || "Clearing exception failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDuplicate = async (reason) => {
    setActionLoading(true);
    try {
      const updated = await confirmDuplicate(id, reason);
      setClaim(updated);
    } catch (err) {
      alert(err.message || "Confirming duplicate failed");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (reason) => {
    setActionLoading(true);
    try {
      const updated = await financeRejectClaim(id, reason);
      setClaim(updated);
    } catch (err) {
      alert(err.message || "Rejection failed");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-content">
        <div className="loading-state">
          <div className="spinner" />
          <p>Loading claim for finance audit…</p>
        </div>
      </div>
    );
  }

  if (error || !claim) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>{error || "Claim not found."}</p>
          <button className="btn btn--ghost" onClick={() => navigate("/finance/verification")}>
            Back to Verification Queue
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-content">
      {/* Back button */}
      <button
        id="fin-review-back-btn"
        className="btn btn--ghost btn--sm back-btn"
        onClick={() => navigate("/finance/verification")}
      >
        <ArrowLeft size={15} strokeWidth={2} />
        Back to Verification Queue
      </button>

      {/* Header */}
      <div className="page-header page-header--compact">
        <div>
          <div className="page-header__meta">
            <span className="claim-id-label">{claim.id}</span>
            <StatusBadge status={claim.financeStatus || claim.status} />
            <StatusBadge status={claim.status} size="sm" />
          </div>
          <h1 className="page-header__title">{claim.merchant || "Finance Audit"}</h1>
          <p className="page-header__subtitle">
            {claim.employee?.name} · {claim.category} · {formatDate(claim.date)}
          </p>
        </div>

        <div className="claim-amount-hero">
          <p className="claim-amount-hero__label">Reimbursement Amount</p>
          <p className="claim-amount-hero__value">{formatAmount(claim.amount, claim.currency)}</p>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="detail-grid">
        {/* Left column */}
        <div className="detail-col">
          {/* Expense Details */}
          <div className="card">
            <h2 className="card__title">Expense Details</h2>
            <div className="detail-rows">
              <DetailRow icon={Building2} label="Merchant" value={claim.merchant} />
              <DetailRow icon={DollarSign} label="Amount" value={formatAmount(claim.amount, claim.currency)} />
              <DetailRow icon={Tag} label="Category" value={claim.category} />
              <DetailRow icon={Calendar} label="Expense Date" value={formatDate(claim.date)} />
              {claim.description && <DetailRow icon={FileText} label="Description" value={claim.description} />}
            </div>
          </div>

          {/* Employee & Manager Info */}
          <div className="card">
            <h2 className="card__title">Employee & Approval Context</h2>
            <div className="manager-row mb-3">
              <div className="manager-avatar">{claim.employee?.name?.charAt(0) || "E"}</div>
              <div>
                <p className="manager-name">{claim.employee?.name || "—"}</p>
                <p className="manager-meta">
                  {claim.employee?.department} · {claim.employee?.role}
                </p>
              </div>
            </div>

            <div className="detail-rows border-t pt-3">
              <DetailRow icon={User} label="Manager Approver" value={claim.manager?.name || claim.manager} />
              {claim.reviewComment && (
                <DetailRow icon={FileText} label="Manager Comment" value={`"${claim.reviewComment}"`} />
              )}
            </div>
          </div>

          {/* Verification Checks */}
          {claim.verification && claim.verification.length > 0 && (
            <div className="card">
              <VerificationChecks checks={claim.verification} />
            </div>
          )}

          {/* AI Forensic Intelligence Card */}
          {(claim.llm_analysis || claim.duplicate_risk_percentage || (claim.matched_candidates && claim.matched_candidates.length > 0)) && (
            <div className={`card ai-intelligence-card ${claim.duplicate_risk_percentage >= 40 ? "ai-intelligence-card--flagged" : ""}`}>
              <div className="ai-intelligence-card__header">
                <h2 className="ai-intelligence-card__title">
                  <Bot size={19} color="#6366f1" />
                  AI Verification & Forensic Analysis
                </h2>
                {claim.risk_classification && (
                  <span
                    className={`ai-risk-badge ${
                      claim.duplicate_risk_percentage >= 70
                        ? "ai-risk-badge--high"
                        : claim.duplicate_risk_percentage >= 40
                        ? "ai-risk-badge--medium"
                        : "ai-risk-badge--low"
                    }`}
                  >
                    {claim.risk_classification} ({claim.duplicate_risk_percentage}% duplicate risk)
                  </span>
                )}
              </div>

              {(claim.manager_recommendation || claim.llm_analysis?.manager_recommendation) && (
                <div className="ai-recommendation-box">
                  <div className="ai-recommendation-box__header">
                    <Sparkles size={14} color="#6366f1" />
                    <span className="ai-recommendation-box__title">
                      Automated Recommendation
                    </span>
                  </div>
                  <p className="ai-recommendation-box__text">
                    {claim.manager_recommendation || claim.llm_analysis?.manager_recommendation}
                  </p>
                </div>
              )}

              {claim.llm_analysis?.reasoning && (
                <div className="ai-reasoning-box">
                  <div className="ai-reasoning-box__label">
                    Forensic Reasoning
                  </div>
                  <p className="ai-reasoning-box__text">
                    {claim.llm_analysis.reasoning}
                  </p>
                </div>
              )}

              {/* Matched Candidates */}
              {claim.matched_candidates && claim.matched_candidates.length > 0 && (
                <div className="ai-candidates-section">
                  <div className="ai-candidates-title">
                    Matched Historical Claims ({claim.matched_candidates.length})
                  </div>
                  <div>
                    {claim.matched_candidates.map((cand, idx) => (
                      <div key={idx} className="ai-candidate-card">
                        <div className="ai-candidate-header">
                          <span className="ai-candidate-ref">{cand.claim_ref || "Claim"} · {cand.merchant_name}</span>
                          <span className="ai-candidate-score">
                            {Math.round((cand.similarity_score || 0) * 100)}% match
                          </span>
                        </div>
                        <div className="ai-candidate-meta">
                          <span>Amount: ₹{cand.amount?.toLocaleString("en-IN")}</span>
                          <span>Date: {cand.expense_date}</span>
                          <span>{cand.is_same_employee ? "Same employee" : "Different employee"}</span>
                        </div>
                        {cand.match_reasons && cand.match_reasons.length > 0 && (
                          <div className="ai-candidate-tags">
                            {cand.match_reasons.map((r, rIdx) => (
                              <span key={rIdx} className="ai-candidate-tag">
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

          {/* Duplicate Evidence */}
          {claim.duplicate?.flagged && (
            <div className="card">
              <DuplicateAlert duplicate={claim.duplicate} />
            </div>
          )}

          {/* Claim History */}
          <div className="card">
            <ClaimHistory history={claim.history || []} claim={claim} />
          </div>
        </div>

        {/* Right column */}
        <div className="detail-col">
          {/* Receipt Preview */}
          <div className="card">
            <ReceiptPreview receiptUrl={claim.receiptUrl} merchant={claim.merchant} />
          </div>

          {/* Finance Action Panel */}
          <FinanceActionPanel
            claim={claim}
            onVerify={handleVerify}
            onClearException={handleClearException}
            onConfirmDuplicate={handleConfirmDuplicate}
            onReject={handleReject}
            loading={actionLoading}
          />
        </div>
      </div>
    </div>
  );
}
