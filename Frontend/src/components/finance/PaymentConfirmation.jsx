// PaymentConfirmation.jsx — Modal for confirming and processing claim payment.

import { useState } from "react";
import { CreditCard, CheckCircle2, X, AlertCircle } from "lucide-react";

export default function PaymentConfirmation({ claim, isOpen, onClose, onConfirm, loading = false }) {
  const [confirmed, setConfirmed] = useState(false);
  const [resultRef, setResultRef] = useState(null);

  if (!isOpen || !claim) return null;

  const handleProcessPayment = async () => {
    try {
      const updated = await onConfirm(claim.id);
      setResultRef(updated.paymentReference || "PAY-SUCCESS");
      setConfirmed(true);
    } catch (err) {
      alert(err.message || "Failed to process payment");
    }
  };

  const handleCloseModal = () => {
    setConfirmed(false);
    setResultRef(null);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleCloseModal}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title flex items-center gap-2">
            <CreditCard size={20} className="text-emerald-500" />
            <span>{confirmed ? "Payment Processed" : "Confirm Payment"}</span>
          </div>
          <button className="btn-icon" onClick={handleCloseModal} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {confirmed ? (
            <div className="text-center py-4">
              <CheckCircle2 size={48} className="text-emerald-500 mx-auto mb-3 animate-bounce" />
              <h4 className="text-lg font-semibold mb-1">Payment Successfully Initiated!</h4>
              <p className="text-sm text-muted mb-4">
                The reimbursement of <strong>₹{claim.amount?.toLocaleString()}</strong> to{" "}
                <strong>{claim.employee?.name}</strong> has been sent to processing.
              </p>

              <div className="p-3 bg-slate-100 rounded-lg text-center font-mono text-sm mb-4">
                <span className="text-xs text-muted block mb-1 font-sans">Payment Reference Number</span>
                <span className="text-emerald-600 font-bold">{resultRef}</span>
              </div>
            </div>
          ) : (
            <div>
              <p className="text-sm mb-4">
                Are you sure you want to process payment for claim <strong>{claim.id}</strong>?
              </p>

              <div className="summary-box p-3 bg-slate-50 rounded-lg text-sm mb-4 space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted">Employee:</span>
                  <span className="font-medium">{claim.employee?.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Merchant:</span>
                  <span className="font-medium">{claim.merchant}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Category:</span>
                  <span className="font-medium">{claim.category}</span>
                </div>
                <div className="flex justify-between border-t pt-2 mt-2 font-semibold">
                  <span>Reimbursement Amount:</span>
                  <span className="text-emerald-600">₹{claim.amount?.toLocaleString()}</span>
                </div>
              </div>

              <div className="text-xs text-muted flex items-center gap-1">
                <AlertCircle size={14} className="text-amber-500" />
                <span>Payment will update the status to PAID and cannot be undone.</span>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {confirmed ? (
            <button className="btn btn--emerald w-full" onClick={handleCloseModal}>
              Done
            </button>
          ) : (
            <div className="flex gap-2 justify-end w-full">
              <button className="btn btn--outline" onClick={handleCloseModal} disabled={loading}>
                Cancel
              </button>
              <button
                id="btn-confirm-payment-submit"
                className="btn btn--emerald"
                onClick={handleProcessPayment}
                disabled={loading}
              >
                {loading ? "Processing..." : "Process Payment"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
