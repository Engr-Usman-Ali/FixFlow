import { useState } from "react";
import { Link } from "react-router-dom";
import { requestApi, userApi } from "../../api/services";
import PageHeader from "../../components/common/PageHeader";
import Pager from "../../components/common/Pager";
import { EmptyState, ErrorState, Loading } from "../../components/common/States";
import RequestFilters, { EMPTY_FILTERS } from "../../components/requests/RequestFilters";
import RequestTable from "../../components/requests/RequestTable";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import { useDebounce } from "../../hooks/useDebounce";
import { useLookups } from "../../hooks/useLookups";
import type { RequestFilters as Filters, UserBrief } from "../../types";
import { requestsLabel } from "../../utils/navigation";

const INITIAL: Filters = { ...EMPTY_FILTERS, sort: "created_at", order: "desc", page: 1 };

export default function Requests() {
  const { can } = useAuth();
  const [filters, setFilters] = useState<Filters>(INITIAL);
  const debounced = useDebounce(filters, 300); // one API call after typing stops
  const { categories, locations } = useLookups();
  const seesAll = can("request.view_all");

  const { data, loading, error, reload } = useAsync(() => requestApi.list(debounced), [JSON.stringify(debounced)]);
  const { data: technicians } = useAsync<UserBrief[]>(
    () => (seesAll ? userApi.technicians() : Promise.resolve([])),
    [seesAll],
  );

  return (
    <>
      <PageHeader
        title={requestsLabel(can)}
        subtitle={data ? `${data.total} request${data.total === 1 ? "" : "s"} found` : undefined}
        actions={can("request.create") && <Link to="/app/requests/new" className="btn btn-primary">New request</Link>}
      />
      <RequestFilters
        filters={filters}
        onChange={(patch) => setFilters((f) => ({ ...f, ...patch }))}
        showTechnician={seesAll}
        technicians={technicians ?? []}
        categories={categories}
        locations={locations}
      />

      {loading && !data ? <Loading /> : error ? <ErrorState message={error} onRetry={reload} /> : data && data.items.length === 0 ? (
        <EmptyState title="No requests match" text="Try clearing a filter or searching for something else." />
      ) : data && (
        <>
          <div className="card flush"><RequestTable items={data.items} /></div>
          <Pager page={filters.page} total={data.total} pageSize={data.page_size}
            onPage={(page) => setFilters((f) => ({ ...f, page }))} />
        </>
      )}
    </>
  );
}
