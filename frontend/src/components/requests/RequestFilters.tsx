import { Search } from "lucide-react";
import { PRIORITIES, STATUSES } from "../../types";
import type { Lookup, RequestFilters as Filters, UserBrief } from "../../types";

interface Props {
  filters: Filters;
  onChange: (patch: Partial<Filters>) => void;
  showTechnician: boolean;
  technicians: UserBrief[];
  categories: Lookup[];
  locations: Lookup[];
  hideStatus?: boolean;
}

export const EMPTY_FILTERS = {
  q: "", status: [] as string[], category_id: "", priority: "", location_id: "", technician_id: "",
  overdue: false, date_from: "", date_to: "",
};

/** Search, filter and sort controls (FR-070 to FR-072, IR-004). */
export default function RequestFilters(props: Props) {
  const { filters, onChange, showTechnician, technicians, categories, locations, hideStatus } = props;

  return (
    <div className="filters card">
      <label className="search-field">
        <Search size={16} aria-hidden="true" />
        <input
          type="search"
          placeholder="Search by request ID, title or description"
          value={filters.q}
          onChange={(e) => onChange({ q: e.target.value, page: 1 })}
          aria-label="Search requests"
        />
      </label>

      {!hideStatus && (
        <select value={filters.status[0] ?? ""} onChange={(e) => onChange({ status: e.target.value ? [e.target.value] : [], page: 1 })} aria-label="Status">
          <option value="">Any status</option>
          {STATUSES.map((s) => <option key={s}>{s}</option>)}
        </select>
      )}
      <select value={filters.category_id} onChange={(e) => onChange({ category_id: e.target.value, page: 1 })} aria-label="Category">
        <option value="">Any category</option>
        {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <select value={filters.priority} onChange={(e) => onChange({ priority: e.target.value, page: 1 })} aria-label="Priority">
        <option value="">Any priority</option>
        {PRIORITIES.map((p) => <option key={p}>{p}</option>)}
      </select>
      <select value={filters.location_id} onChange={(e) => onChange({ location_id: e.target.value, page: 1 })} aria-label="Location">
        <option value="">Any location</option>
        {locations.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
      </select>
      {showTechnician && (
        <select value={filters.technician_id} onChange={(e) => onChange({ technician_id: e.target.value, page: 1 })} aria-label="Technician">
          <option value="">Any technician</option>
          {technicians.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      )}
      <label className="date-field">From
        <input type="date" value={filters.date_from} onChange={(e) => onChange({ date_from: e.target.value, page: 1 })} />
      </label>
      <label className="date-field">To
        <input type="date" value={filters.date_to} onChange={(e) => onChange({ date_to: e.target.value, page: 1 })} />
      </label>
      <label className="check">
        <input type="checkbox" checked={filters.overdue} onChange={(e) => onChange({ overdue: e.target.checked, page: 1 })} />
        Overdue only
      </label>

      <select
        value={`${filters.sort}:${filters.order}`}
        onChange={(e) => {
          const [sort, order] = e.target.value.split(":");
          onChange({ sort, order: order as "asc" | "desc" });
        }}
        aria-label="Sort"
      >
        <option value="created_at:desc">Newest first</option>
        <option value="created_at:asc">Oldest first</option>
        <option value="priority:desc">Highest priority first</option>
        <option value="updated_at:desc">Recently updated</option>
        <option value="status:asc">Status A to Z</option>
        <option value="title:asc">Title A to Z</option>
      </select>
      <button className="btn btn-ghost" onClick={() => onChange({ ...EMPTY_FILTERS, status: hideStatus ? filters.status : [], page: 1 })}>
        Clear filters
      </button>
    </div>
  );
}
