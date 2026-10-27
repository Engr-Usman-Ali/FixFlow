// Loading, error and empty states shared by every page.
import { ReactNode } from "react";
import { AlertCircle, Inbox } from "lucide-react";

export const Loading = ({ label = "Loading" }: { label?: string }) => (
  <div className="state" role="status"><span className="spinner" />{label}…</div>
);

export const ErrorState = ({ message, onRetry }: { message: string; onRetry?: () => void }) => (
  <div className="state state-error" role="alert">
    <AlertCircle size={20} />
    <p>{message}</p>
    {onRetry && <button className="btn btn-secondary" onClick={onRetry}>Try again</button>}
  </div>
);

export const EmptyState = ({ title, text, action }: { title: string; text?: string; action?: ReactNode }) => (
  <div className="state">
    <Inbox size={28} />
    <strong>{title}</strong>
    {text && <p className="muted">{text}</p>}
    {action}
  </div>
);
