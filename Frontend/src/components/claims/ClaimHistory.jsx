// ClaimHistory.jsx — Activity timeline, Manager/Finance comments, and SLA tracker.

import {
  FileText,
  Send,
  ShieldCheck,
  UserCheck,
  UserX,
  CreditCard,
  AlertTriangle,
  Clock,
  MessageSquareQuote,
  CheckCircle2,
  XCircle,
  Timer,
  Bot,
  Sparkles,
} from "lucide-react";

function formatTimestamp(ts) {
  if (!ts) return null;
  const d = new Date(ts);
  if (isNaN(d.getTime())) return null;
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

function formatDuration(ms) {
  if (ms < 0 || isNaN(ms)) return null;
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${Math.max(1, seconds)}s`;
}

function getEventIcon(item) {
  const ev = (item.event || "").toLowerCase();
  const toStatus = item.toStatus || "";

  if (toStatus === "REJECTED" || ev.includes("reject")) {
    return <XCircle size={15} className="text-red-500" />;
  }
  if (toStatus === "PAID" || ev.includes("payment")) {
    return <CreditCard size={15} className="text-emerald-500" />;
  }
  if (toStatus === "READY_FOR_PAYMENT" || ev.includes("finance")) {
    return <ShieldCheck size={15} className="text-purple-500" />;
  }
  if (toStatus === "APPROVED" || toStatus === "MANAGER_CONFIRMED" || ev.includes("manager")) {
    return <UserCheck size={15} className="text-blue-500" />;
  }
  if (ev.includes("verification") || ev.includes("ocr") || ev.includes("flagged") || ev.includes("ai")) {
    return <Bot size={15} color="#6366f1" />;
  }
  if (ev.includes("submit")) {
    return <Send size={15} className="text-amber-500" />;
  }
  return <FileText size={15} className="text-slate-500" />;
}

export default function ClaimHistory({ history = [], claim = null }) {
  // Extract completed timestamps to calculate turnaround / SLAs
  const completedItems = history.filter((h) => h.done && h.timestamp);
  const startTime = completedItems.length > 0 ? new Date(completedItems[0].timestamp).getTime() : null;
  const endTime =
    completedItems.length > 1
      ? new Date(completedItems[completedItems.length - 1].timestamp).getTime()
      : null;

  const totalTurnaround = startTime && endTime && endTime >= startTime ? formatDuration(endTime - startTime) : null;

  return (
    <div className="claim-history-card">
      <div className="claim-history-card__header">
        <div className="claim-history-card__title-wrap">
          <Clock size={16} className="text-accent" />
          <h3 className="claim-history__title" style={{ margin: 0 }}>
            Audit Trail & SLA History
          </h3>
        </div>
        {totalTurnaround && (
          <div className="sla-badge" title="Total turnaround from creation to current step">
            <Timer size={13} />
            <span>Turnaround: {totalTurnaround}</span>
          </div>
        )}
      </div>

      <ol className="claim-history__list" style={{ marginTop: "16px" }}>
        {history.map((item, i) => {
          // Calculate step duration from previous completed item
          let stepDuration = null;
          if (item.timestamp && i > 0 && history[i - 1].timestamp) {
            const prevTime = new Date(history[i - 1].timestamp).getTime();
            const currTime = new Date(item.timestamp).getTime();
            if (currTime >= prevTime) {
              stepDuration = formatDuration(currTime - prevTime);
            }
          }

          const isRejectEvent =
            item.toStatus === "REJECTED" || (item.event || "").toLowerCase().includes("reject");

          const isFinanceEvent =
            !isRejectEvent &&
            (item.toStatus === "READY_FOR_PAYMENT" ||
              item.toStatus === "PAID" ||
              (item.event || "").toLowerCase().includes("finance"));

          const isManagerEvent =
            !isRejectEvent &&
            !isFinanceEvent &&
            (item.toStatus === "APPROVED" ||
              item.toStatus === "MANAGER_CONFIRMED" ||
              (item.event || "").toLowerCase().includes("manager"));

          const isAiEvent =
            !isRejectEvent &&
            !isFinanceEvent &&
            !isManagerEvent &&
            ((item.event || "").toLowerCase().includes("verification") ||
              (item.event || "").toLowerCase().includes("flagged") ||
              (item.event || "").toLowerCase().includes("ai") ||
              (item.comment || "").toLowerCase().startsWith("automation alert") ||
              (item.comment || "").toLowerCase().includes("deterministic"));

          return (
            <li
              key={item.id || i}
              className={`claim-history__item ${item.isCurrent ? "claim-history__item--current" : ""} ${
                item.done ? "claim-history__item--done" : ""
              }`}
            >
              <div className="claim-history__dot">
                {item.isCurrent ? (
                  <span className="dot dot--pulse" />
                ) : item.done ? (
                  <span className="dot dot--done">{getEventIcon(item)}</span>
                ) : (
                  <span className="dot dot--pending" />
                )}
              </div>

              <div className="claim-history__content" style={{ width: "100%" }}>
                <div className="claim-history__event-row">
                  <p className="claim-history__event">{item.event}</p>
                  {stepDuration && (
                    <span className="sla-step-tag">
                      <Clock size={11} /> +{stepDuration}
                    </span>
                  )}
                </div>

                <div className="claim-history__meta-row">
                  <span className="claim-history__time">
                    {item.isCurrent
                      ? "In Progress / Action Pending"
                      : item.timestamp
                      ? formatTimestamp(item.timestamp)
                      : "—"}
                  </span>
                  {item.actor && (
                    <span className="claim-history__actor">
                      by <strong>{item.actor}</strong>
                    </span>
                  )}
                </div>

                {/* Manager / Finance / Rejection / AI Automation Comment Box */}
                {item.comment && (
                  <div
                    className={`history-comment-box ${
                      isRejectEvent
                        ? "history-comment-box--reject"
                        : isFinanceEvent
                        ? "history-comment-box--finance"
                        : isManagerEvent
                        ? "history-comment-box--manager"
                        : isAiEvent
                        ? "history-comment-box--ai"
                        : ""
                    }`}
                  >
                    <div className="history-comment-header">
                      {isAiEvent ? (
                        <Bot size={14} color="#6366f1" />
                      ) : (
                        <MessageSquareQuote size={14} />
                      )}
                      <span>
                        {isRejectEvent
                          ? "Rejection Reason"
                          : isFinanceEvent
                          ? "Finance Verification Note"
                          : isManagerEvent
                          ? "Manager Approval Justification"
                          : isAiEvent
                          ? "AI Automation & Verification Intelligence"
                          : "Audit Note"}
                      </span>
                    </div>
                    <p className="history-comment-text">"{item.comment}"</p>
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
