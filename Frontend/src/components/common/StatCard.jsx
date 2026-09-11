// StatCard — summary metric card for the staff dashboard.

export default function StatCard({ label, value, icon: Icon, colorClass = "" }) {
  return (
    <div className={`stat-card ${colorClass}`}>
      <div className="stat-card__body">
        <p className="stat-card__label">{label}</p>
        <p className="stat-card__value">{value}</p>
      </div>
      {Icon && (
        <div className="stat-card__icon-wrap">
          <Icon size={22} strokeWidth={1.75} />
        </div>
      )}
    </div>
  );
}
