// ClaimHistory — activity timeline for a single claim.
// Mock history data is passed as a prop.
// When backend is connected, pass the audit_log array from the claim API response.

function formatTimestamp(ts) {
  if (!ts) return null;
  const d = new Date(ts);
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export default function ClaimHistory({ history = [] }) {
  return (
    <div className="claim-history">
      <h3 className="claim-history__title">History</h3>
      <ol className="claim-history__list">
        {history.map((item, i) => (
          <li
            key={i}
            className={`claim-history__item ${item.isCurrent ? "claim-history__item--current" : ""} ${item.done ? "claim-history__item--done" : ""}`}
          >
            <div className="claim-history__dot">
              {item.isCurrent ? (
                <span className="dot dot--pulse" />
              ) : item.done ? (
                <span className="dot dot--done">✓</span>
              ) : (
                <span className="dot dot--pending" />
              )}
            </div>
            <div className="claim-history__content">
              <p className="claim-history__event">{item.event}</p>
              <p className="claim-history__time">
                {item.isCurrent
                  ? "Current"
                  : item.timestamp
                  ? formatTimestamp(item.timestamp)
                  : "—"}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
