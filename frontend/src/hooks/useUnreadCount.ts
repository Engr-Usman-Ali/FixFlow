import { useEffect, useState } from "react";
import { notificationApi } from "../api/services";

/** Polls the unread-notification count so the bell badge stays current. */
export function useUnreadCount(intervalMs = 30000) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const load = () => notificationApi.unreadCount().then((r) => setCount(r.count)).catch(() => undefined);
    load();
    const timer = setInterval(load, intervalMs);
    window.addEventListener("fixflow:notifications-changed", load);
    return () => {
      clearInterval(timer);
      window.removeEventListener("fixflow:notifications-changed", load);
    };
  }, [intervalMs]);
  return count;
}
