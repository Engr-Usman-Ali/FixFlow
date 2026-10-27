import { History, Pencil, Plus, Search } from "lucide-react";
import { FormEvent, useState } from "react";
import { equipmentApi } from "../../api/services";
import { ConditionBadge } from "../../components/common/Badges";
import Modal from "../../components/common/Modal";
import PageHeader from "../../components/common/PageHeader";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import RequestTable from "../../components/requests/RequestTable";
import { useToast } from "../../context/ToastContext";
import { useAsync } from "../../hooks/useAsync";
import { useDebounce } from "../../hooks/useDebounce";
import { useLookups } from "../../hooks/useLookups";
import { CONDITIONS } from "../../types";
import type { Condition, Equipment as EquipmentItem, EquipmentInput, MaintenanceRequest } from "../../types";

const BLANK: EquipmentInput = {
  asset_code: "", name: "", category_id: "", location_id: "", condition: "Good", description: "", is_active: true,
};

/** Equipment register (FR-050 to FR-054). */
export default function Equipment() {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const q = useDebounce(search, 300);
  const { data, loading, error, reload } = useAsync(() => equipmentApi.list({ q }), [q]);
  const { categories, locations } = useLookups(true);
  const [editing, setEditing] = useState<{ id: number | null; values: EquipmentInput } | null>(null);
  const [historyFor, setHistoryFor] = useState<EquipmentItem | null>(null);
  const [formError, setFormError] = useState("");
  const history = useAsync<MaintenanceRequest[]>(
    () => (historyFor ? equipmentApi.history(historyFor.id) : Promise.resolve([])),
    [historyFor?.id],
  );

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!editing) return;
    const v = editing.values;
    if (!v.category_id || !v.location_id) return setFormError("Choose a category and a location.");
    setFormError("");
    try {
      if (editing.id) await equipmentApi.update(editing.id, v);
      else await equipmentApi.create(v);
      toast(editing.id ? "Equipment updated" : "Equipment added");
      setEditing(null);
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    }
  }

  const patch = (field: keyof EquipmentInput, value: string | number | boolean) =>
    setEditing((cur) => (cur ? { ...cur, values: { ...cur.values, [field]: value } } : cur));

  const edit = (q: EquipmentItem) => {
    setFormError("");
    setEditing({
      id: q.id,
      values: {
        asset_code: q.asset_code, name: q.name, category_id: q.category.id, location_id: q.location.id,
        condition: q.condition, description: q.description ?? "", is_active: q.is_active,
      },
    });
  };

  return (
    <>
      <PageHeader
        title="Equipment"
        subtitle="Every asset that can be linked to a request, with its repair history."
        actions={
          <button className="btn btn-primary" onClick={() => { setFormError(""); setEditing({ id: null, values: BLANK }); }}>
            <Plus size={16} /> Add equipment
          </button>
        }
      />
      <div className="card filters-inline">
        <label className="search-field">
          <Search size={16} aria-hidden="true" />
          <input type="search" placeholder="Search by asset code or name" value={search}
            onChange={(e) => setSearch(e.target.value)} aria-label="Search equipment" />
        </label>
      </div>

      {loading && !data ? <Loading /> : error || !data ? (
        <ErrorState message={error ?? "Could not load equipment."} onRetry={reload} />
      ) : data.length === 0 ? (
        <EmptyState title="No equipment found" text="Add an asset to start tracking its repair history." />
      ) : (
        <div className="card flush table-wrap">
          <table className="table">
            <thead>
              <tr><th>Code</th><th>Name</th><th>Location</th><th>Condition</th><th>Requests</th><th><span className="sr-only">Actions</span></th></tr>
            </thead>
            <tbody>
              {data.map((q) => (
                <tr key={q.id}>
                  <td className="nowrap"><strong>{q.asset_code}</strong></td>
                  <td>
                    <span className="row-title">{q.name}</span>
                    <span className="muted small">{q.category.name}{q.is_active ? "" : " · retired"}</span>
                  </td>
                  <td>{q.location.name}</td>
                  <td><ConditionBadge condition={q.condition} /></td>
                  <td>{q.request_count}{q.request_count >= 2 && <span className="muted small block">repeat repairs</span>}</td>
                  <td className="row-actions">
                    <button className="icon-btn" aria-label={`History for ${q.name}`} title="Maintenance history" onClick={() => setHistoryFor(q)}>
                      <History size={17} />
                    </button>
                    <button className="icon-btn" aria-label={`Edit ${q.name}`} title="Edit" onClick={() => edit(q)}>
                      <Pencil size={17} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <Modal title={editing.id ? "Edit equipment" : "Add equipment"} onClose={() => setEditing(null)}>
          <form onSubmit={save} className="stack-form">
            <div className="form-grid">
              <label className="field"><span>Asset code <span className="req">*</span></span>
                <input required maxLength={40} pattern="[A-Za-z0-9._\-]+" title="Letters, numbers, dot, dash or underscore"
                  value={editing.values.asset_code} onChange={(e) => patch("asset_code", e.target.value)} />
                <small className="muted">Unique in your company, e.g. PMP-101.</small></label>
              <label className="field"><span>Name <span className="req">*</span></span>
                <input required minLength={2} value={editing.values.name} onChange={(e) => patch("name", e.target.value)} /></label>
              <label className="field"><span>Category <span className="req">*</span></span>
                <select required value={editing.values.category_id} onChange={(e) => patch("category_id", Number(e.target.value))}>
                  <option value="">Select…</option>
                  {categories.filter((c) => c.is_active || c.id === editing.values.category_id).map((c) =>
                    <option key={c.id} value={c.id}>{c.name}</option>)}
                </select></label>
              <label className="field"><span>Location <span className="req">*</span></span>
                <select required value={editing.values.location_id} onChange={(e) => patch("location_id", Number(e.target.value))}>
                  <option value="">Select…</option>
                  {locations.filter((l) => l.is_active || l.id === editing.values.location_id).map((l) =>
                    <option key={l.id} value={l.id}>{l.name}</option>)}
                </select></label>
              <label className="field"><span>Condition</span>
                <select value={editing.values.condition} onChange={(e) => patch("condition", e.target.value as Condition)}>
                  {CONDITIONS.map((c) => <option key={c}>{c}</option>)}
                </select></label>
              <label className="check field-check">
                <input type="checkbox" checked={editing.values.is_active} onChange={(e) => patch("is_active", e.target.checked)} />
                In service (can be linked to new requests)
              </label>
            </div>
            <label className="field"><span>Description (optional)</span>
              <textarea rows={3} maxLength={2000} value={editing.values.description} onChange={(e) => patch("description", e.target.value)} /></label>
            {formError && <p className="field-error" role="alert">{formError}</p>}
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setEditing(null)}>Cancel</button>
              <button className="btn btn-primary">Save equipment</button>
            </div>
          </form>
        </Modal>
      )}

      {historyFor && (
        <Modal title={`Maintenance history · ${historyFor.asset_code}`} onClose={() => setHistoryFor(null)} wide>
          <p className="muted">{historyFor.name} · {historyFor.location.name}</p>
          {history.loading ? <Loading /> : history.data && history.data.length > 0 ? (
            <RequestTable items={history.data} />
          ) : (
            <EmptyState title="No maintenance recorded" text="Requests linked to this equipment will appear here." />
          )}
        </Modal>
      )}
    </>
  );
}
