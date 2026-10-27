// Horizontal bars drawn with plain CSS, used by the reports and the dashboard.
export default function BarList({ data }: { data: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(data));
  return (
    <ul className="bar-list">
      {Object.entries(data).map(([label, value]) => (
        <li key={label}>
          <span className="bar-label">{label}</span>
          <span className="bar-track"><span className="bar-fill" style={{ width: `${(value / max) * 100}%` }} /></span>
          <span className="bar-value">{value}</span>
        </li>
      ))}
    </ul>
  );
}
