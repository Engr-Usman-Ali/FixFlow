import { useCallback, useEffect, useState } from "react";
import { orgApi } from "../api/services";
import type { Lookup } from "../types";

/** Company categories and locations, used by forms and filters. */
export function useLookups(includeInactive = false) {
  const [categories, setCategories] = useState<Lookup[]>([]);
  const [locations, setLocations] = useState<Lookup[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    Promise.all([orgApi.categories(includeInactive), orgApi.locations(includeInactive)])
      .then(([c, l]) => {
        if (cancelled) return;
        setCategories(c);
        setLocations(l);
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [includeInactive, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { categories, locations, error, reload };
}
