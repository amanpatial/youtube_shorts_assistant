import { useEffect, useState } from "react";
import { ApiError, getApiKey, listShorts } from "../api";
import type { WorkflowListItem } from "../types";

export default function History() {
  const [items, setItems] = useState<WorkflowListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!getApiKey()) {
        setError("Set an API key on Settings first.");
        setLoading(false);
        return;
      }
      try {
        const data = await listShorts(30, 0);
        if (!cancelled) {
          setItems(data.items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : String(err));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="card">
      <h2>History</h2>
      {loading ? <p className="muted">Loading…</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {!loading && !error && items.length === 0 ? (
        <p className="muted">No runs yet for this API key.</p>
      ) : null}
      {items.length > 0 ? (
        <table className="table">
          <thead>
            <tr>
              <th>Topic</th>
              <th>Status</th>
              <th>Score</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.workflow_id}>
                <td>
                  <a href={`#/runs/${row.workflow_id}`}>{row.topic}</a>
                </td>
                <td>
                  <span className={`badge ${row.status}`}>{row.status}</span>
                </td>
                <td>{row.best_score ?? "—"}</td>
                <td className="muted">
                  {row.created_at ? row.created_at.replace("T", " ").slice(0, 19) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
