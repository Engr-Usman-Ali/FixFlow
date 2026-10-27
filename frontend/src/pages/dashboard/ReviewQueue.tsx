// FR-020: managers' queue of work waiting for a decision.
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { requestApi } from "../../api/services";
import PageHeader from "../../components/common/PageHeader";
import Pager from "../../components/common/Pager";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import RequestTable from "../../components/requests/RequestTable";
import { useAsync } from "../../hooks/useAsync";
import type { Status } from "../../types";

const TABS: { key: string; label: string; statuses: Status[]; hint: string; unassigned?: boolean }[] = [
  { key: "review", label: "Awaiting review", statuses: ["New", "Under Review"], hint: "Confirm the priority, then assign a technician, hold or reject." },
  { key: "closure", label: "Awaiting closure", statuses: ["Resolved"], hint: "Check the completion details, then close or send back for more work." },
  { key: "hold", label: "On hold", statuses: ["On Hold"], hint: "Paused work. Resume it when the reason is cleared." },
  { key: "unassigned", label: "Unassigned", statuses: ["New", "Under Review", "On Hold"], unassigned: true, hint: "Open requests that still need a technician." },
];

export default function ReviewQueue() {
  const [params, setParams] = useSearchParams();
  const tab = TABS.find((t) => t.key === params.get("tab")) ?? TABS[0];
  const [page, setPage] = useState(1);

  const { data, loading, error, reload } = useAsync(
    () => requestApi.list({ status: tab.statuses, unassigned: tab.unassigned, sort: "priority", order: "desc", page }),
    [tab.key, page],
  );

  return (
    <>
      <PageHeader title="Review queue" subtitle="Most urgent first. Open a request to act on it." />
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t.key} role="tab" aria-selected={t.key === tab.key}
            className={`tab ${t.key === tab.key ? "tab-active" : ""}`}
            onClick={() => { setPage(1); setParams(t.key === "review" ? {} : { tab: t.key }); }}>
            {t.label}
          </button>
        ))}
      </div>
      <p className="muted">{tab.hint}</p>

      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && data.items.length === 0 ? (
        <EmptyState title="Nothing waiting here" text="Good news: this part of the queue is empty." />
      ) : data && (
        <>
          <div className="card flush"><RequestTable items={data.items} /></div>
          <Pager page={page} total={data.total} pageSize={data.page_size} onPage={setPage} />
        </>
      )}
    </>
  );
}
