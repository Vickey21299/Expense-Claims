// StatusBadge — reusable status pill for all claim statuses.
// Staff cannot change status via this component.

const STATUS_MAP = {
  DRAFT: {
    label: "Draft",
    className: "status-draft",
  },
  SUBMITTED: {
    label: "Submitted",
    className: "status-submitted",
  },
  UNDER_REVIEW: {
    label: "Under Review",
    className: "status-under-review",
  },
  FLAGGED: {
    label: "Flagged",
    className: "status-flagged",
  },
  APPROVED: {
    label: "Approved",
    className: "status-approved",
  },
  REJECTED: {
    label: "Rejected",
    className: "status-rejected",
  },
  READY_FOR_PAYMENT: {
    label: "Ready for Payment",
    className: "status-ready",
  },
  PAID: {
    label: "Paid",
    className: "status-paid",
  },
  PENDING_REVIEW: {
    label: "Pending Review",
    className: "status-under-review",
  },
  FINANCE_PENDING: {
    label: "Finance Pending",
    className: "status-finance-pending",
  },
  FINANCE_CLEARED: {
    label: "Finance Cleared",
    className: "status-finance-cleared",
  },
  FINANCE_REJECTED: {
    label: "Finance Rejected",
    className: "status-finance-rejected",
  },
  FINANCE_EXCEPTION: {
    label: "Finance Exception",
    className: "status-finance-exception",
  },
};

export default function StatusBadge({ status, size = "md" }) {
  const config = STATUS_MAP[status] || { label: status, className: "status-draft" };

  return (
    <span className={`status-badge ${config.className} status-badge--${size}`}>
      {config.label}
    </span>
  );
}
