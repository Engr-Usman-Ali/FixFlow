import { FormEvent, useState } from "react";
import { requestApi } from "../../api/services";
import { useToast } from "../../context/ToastContext";
import type { RequestDetail } from "../../types";
import { formatDateTime } from "../../utils/format";

export default function CommentSection({ request, onChanged }: { request: RequestDetail; onChanged: () => void }) {
  const toast = useToast();
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    setBusy(true);
    try {
      await requestApi.addComment(request.id, body);
      setBody("");
      onChanged();
    } catch (err) {
      toast((err as Error).message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h3>Comments</h3>
      {request.comments.length === 0 && <p className="muted">No comments yet.</p>}
      <ul className="log-list">
        {request.comments.map((c) => (
          <li key={c.id}>
            <div className="log-meta">
              <strong>{c.author.name} <span className="muted small">({c.author.role})</span></strong>
              <span className="muted small">{formatDateTime(c.created_at)}</span>
            </div>
            <p className="prose">{c.body}</p>
          </li>
        ))}
      </ul>
      {request.can_comment && (
        <form className="comment-form" onSubmit={submit}>
          <input value={body} onChange={(e) => setBody(e.target.value)} placeholder="Write a comment" maxLength={2000} aria-label="Comment" />
          <button className="btn btn-secondary" disabled={busy || !body.trim()}>Post</button>
        </form>
      )}
    </section>
  );
}
