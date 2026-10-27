// "Suggest with AI" helper (Google Gemini on the server). The result is only a
// suggestion; a person must apply it (FR-091) and the form works without it (FR-093).
import { Sparkles } from "lucide-react";
import { useState } from "react";
import { aiApi } from "../../api/services";
import { useAuth } from "../../context/AuthContext";
import { useAsync } from "../../hooks/useAsync";
import type { AiSuggestion as Suggestion } from "../../types";

interface Props {
  title: string;
  description: string;
  onApply: (s: Suggestion) => void;
}

export default function AiSuggestion({ title, description, onApply }: Props) {
  const { can } = useAuth();
  const { data: status } = useAsync(() => aiApi.status(), []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Suggestion | null>(null);
  const ready = title.trim().length >= 3 && description.trim().length >= 10;

  if (!can("ai.suggest") || !status?.enabled) return null;

  async function ask() {
    setBusy(true);
    setError("");
    try {
      setResult(await aiApi.suggest(title, description));
    } catch (e) {
      setResult(null);
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-box">
      <button type="button" className="btn btn-secondary" onClick={ask} disabled={!ready || busy}>
        <Sparkles size={16} /> {busy ? "Thinking…" : "Suggest category and priority"}
      </button>
      {!ready && <span className="muted small">Add a title and a description first.</span>}
      {error && <p className="field-error">{error}</p>}
      {result && (
        <div className="ai-result">
          <p><strong>AI suggestion:</strong> {result.category}, {result.priority} priority</p>
          {result.rationale && <p className="muted small">{result.rationale}</p>}
          <p className="muted small">Suggested by {result.model}. Check it before using it.</p>
          <button type="button" className="btn btn-small btn-primary" onClick={() => { onApply(result); setResult(null); }}>
            Use this suggestion
          </button>
        </div>
      )}
    </div>
  );
}
