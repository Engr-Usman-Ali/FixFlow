import type { Status } from "../types";

// Dates come from the API in UTC and are shown in the browser's local time zone (DR-005).
export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });

export const formatDateTime = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export function timeAgo(iso: string): string {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}

export function dueLabel(iso: string | null): string {
  if (!iso) return "";
  const hours = Math.round((new Date(iso).getTime() - Date.now()) / 3600000);
  if (hours < 0) return `${Math.abs(hours) < 48 ? `${Math.abs(hours)} h` : `${Math.round(-hours / 24)} d`} overdue`;
  return hours < 48 ? `due in ${hours} h` : `due in ${Math.round(hours / 24)} d`;
}

/** Button wording for a status move, based on where the request is now. */
export function actionLabel(current: Status, target: Status): string {
  if (current === "Closed" || current === "Rejected") return "Reopen request";
  if (current === "Resolved" && target === "In Progress") return "Send back for more work";
  const labels: Partial<Record<Status, string>> = {
    "Under Review": current === "New" ? "Start review" : "Return to review",
    Assigned: "Resume as assigned",
    "In Progress": current === "On Hold" ? "Resume work" : "Start work",
    "On Hold": "Put on hold",
    Resolved: "Submit as resolved",
    Closed: "Close request",
    Rejected: "Reject request",
  };
  return labels[target] ?? target;
}

/** Mirrors the server rule so the dialog can ask for a reason up front. */
export const needsReason = (current: Status, target: Status) =>
  target === "On Hold" || target === "Rejected" || current === "Closed" || current === "Rejected" ||
  (current === "Resolved" && target === "In Progress");

/** Mirrors the server password rule for instant feedback. */
export function passwordProblem(pw: string): string | null {
  if (pw.length < 8 || !/[A-Z]/.test(pw) || !/[a-z]/.test(pw) || !/\d/.test(pw)) {
    return "Use at least 8 characters with an uppercase letter, a lowercase letter and a number.";
  }
  return null;
}

/** Download rows as a CSV file (used by Reports). */
export function downloadCsv(filename: string, rows: (string | number | null)[][]) {
  const escape = (v: string | number | null) => {
    const s = v === null ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const blob = new Blob([rows.map((r) => r.map(escape).join(",")).join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
