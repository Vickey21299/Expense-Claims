// FinanceActionPanel — Action panel for Finance Controller during claim review.
// Provides controls for:
// - Verifying and clearing a claim for payment
// - Clearing a financial exception/duplicate flag
// - Confirming duplicate (rejecting claim)
// - Rejecting claim (non-duplicate policy reason)
// Includes mandatory comment validation.

import { useState } from "react";
import { ShieldCheck, AlertTriangle, CheckCircle, XCircle, DollarSign } from "lucide-react";

export default function FinanceActionPanel({
  claim,
  onVerify,
  onClearException,
  onConfirmDuplicate,
  onReject,
  loading = false,
}) {
  const [comment, setComment] = useState("");
  const [activeAction, setActiveAction] = useState(null); // 'verify' | 'clear' | 'duplicate' | 'reject'
  const [error, setError] = useState("");

  const isPaid = claim?.status === "PAID";
  const isFinanceRejected = claim?.financeStatus === "FINANCE_REJECTED";
  const isFinanceCleared = claim?.financeStatus === "FINANCE_CLEARED" && claim?.status === "READY_FOR_PAYMENT";
  const isFlagged = claim?.financeStatus === "FINANCE_EXCEPTION" || claim?.duplicate?.flagged || claim?.status === "FLAGGED";

  if (isPaid) {
    return (
      <div className="card finance-action-panel finance-action-panel--completed">
        <div className="finance-action-panel__header">
          <CheckCircle size={20} className="text-emerald-500" />
          <h3 className="card__title">Payment Completed</h3>
        </div>
        <p className="card__description text-sm">
          This claim has been processed and paid. No further financial actions can be taken.
        </p>
        {claim.paymentReference && (
          <div className="finance-action-panel__ref">
            <span className="text-muted text-xs">Payment Ref:</span>
            <code className="text-sm font-mono">{claim.paymentReference}</code>
          </div>
        )}
      </div>
    );
  }

  if (isFinanceRejected) {
    return (
      <div className="card finance-action-panel finance-action-panel--rejected">
        <div className="finance-action-panel__header">
          <XCircle size={20} className="text-red-500" />
          <h3 className="card__title">Finance Rejected</h3>
        </div>
        <p className="card__description text-sm">
          This claim was rejected by Finance. Rejection details:
        </p>
        {claim.financeVerification?.comment && (
          <blockquote className="finance-action-panel__quote">
            "{claim.financeVerification.comment}"
          </blockquote>
        )}
      </div>
    );
  }

  const handleAction = (actionType) => {
    setError("");
    if (!comment.trim()) {
      setError("A comment/reason is required before executing this action.");
      return;
    }

    if (actionType === "verify") {
      onVerify(comment.trim());
    } else if (actionType === "clear") {
      onClearException(comment.trim());
    } else if (actionType === "duplicate") {
      onConfirmDuplicate(comment.trim());
    } else if (actionType === "reject") {
      onReject(comment.trim());
    }
  };

  return (
    <div className="card finance-action-panel">
      <div className="card__header">
        <div>
          <h3 className="card__title">Finance Review & Verification</h3>
          <p className="card__description">
            Perform financial checks, clear exceptions, or approve for payment queue.
          </p>
        </div>
      </div>

      <div className="finance-action-panel__body">
        {/* Exception alert callout if flagged */}
        {isFlagged && (
          <div className="alert-box alert-box--warning mb-4">
            <AlertTriangle size={18} />
            <div>
              <strong>Financial Exception / Flagged Issue</strong>
              <p className="text-xs">
                Review automated duplicate checks and verification details before clearing or confirming duplicate.
              </p>
            </div>
          </div>
        )}

        {/* Mandatory comment input */}
        <div className="form-group">
          <label htmlFor="finance-comment" className="form-label font-medium text-sm">
            Finance Verification Comment <span className="text-red-500">*</span>
          </label>
          <textarea
            id="finance-comment"
            className={`form-textarea ${error ? "form-input--error" : ""}`}
            rows={3}
            placeholder="Add mandatory notes regarding invoice match, tax validation, or reason for action..."
            value={comment}
            onChange={(e) => {
              setComment(e.target.value);
              if (error) setError("");
            }}
            disabled={loading}
          />
          {error && <p className="form-error text-xs text-red-500 mt-1">{error}</p>}
        </div>

        {/* Action Buttons */}
        <div className="finance-action-panel__actions">
          {isFlagged ? (
            <>
              <button
                type="button"
                id="btn-fin-clear-exception"
                className="btn btn--emerald"
                disabled={loading}
                onClick={() => handleAction("clear")}
              >
                <ShieldCheck size={16} />
                <span>Clear Exception</span>
              </button>
              <button
                type="button"
                id="btn-fin-confirm-duplicate"
                className="btn btn--danger"
                disabled={loading}
                onClick={() => handleAction("duplicate")}
              >
                <AlertTriangle size={16} />
                <span>Confirm Duplicate & Reject</span>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                id="btn-fin-verify"
                className="btn btn--emerald"
                disabled={loading}
                onClick={() => handleAction("verify")}
              >
                <CheckCircle size={16} />
                <span>Verify & Queue for Payment</span>
              </button>
              <button
                type="button"
                id="btn-fin-reject"
                className="btn btn--outline-danger"
                disabled={loading}
                onClick={() => handleAction("reject")}
              >
                <XCircle size={16} />
                <span>Reject Claim</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
