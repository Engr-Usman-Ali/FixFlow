// Status and priority badges. Each has a text label, so meaning never relies on colour alone.
import type { Condition, Priority, Status } from "../../types";

const slug = (value: string) => value.toLowerCase().replace(/\s+/g, "-");

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`badge status-${slug(status)}`}>
      <span className="badge-dot" aria-hidden="true" />
      {status}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <span className={`badge priority-${slug(priority)}`}>{priority}</span>;
}

export function ConditionBadge({ condition }: { condition: Condition }) {
  return <span className={`badge condition-${slug(condition)}`}>{condition}</span>;
}
