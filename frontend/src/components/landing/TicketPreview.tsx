// A static "work order" card for the hero: shows the lifecycle a request moves through.
const STAGES = ["New", "Review", "Assigned", "In progress", "Resolved", "Closed"];
const CURRENT = 3;

export default function TicketPreview() {
  return (
    <div className="ticket" aria-label="Example of a request moving through its stages">
      <div className="ticket-top">
        <span className="ticket-id">ACME-00042</span>
        <span className="badge priority-high">High</span>
      </div>
      <h3>Conveyor belt 3 jams at start-up</h3>
      <p className="muted small">Warehouse A · reported by Eli, 2 hours ago</p>

      <ol className="rail">
        {STAGES.map((stage, i) => (
          <li key={stage} className={i < CURRENT ? "rail-done" : i === CURRENT ? "rail-now" : ""}>
            <span className="rail-node" />
            <span className="rail-label">{stage}</span>
          </li>
        ))}
      </ol>

      <div className="ticket-note">
        <strong>Tariq (technician)</strong>
        <p>Drive roller was seized. Freed it and ordered a new bearing.</p>
      </div>
      <div className="ticket-foot">
        <span>Priority confirmed by Maya</span>
        <span>Due in 22 h</span>
      </div>
    </div>
  );
}
