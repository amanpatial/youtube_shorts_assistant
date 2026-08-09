import { FormEvent, useState } from "react";
import { ApiError, createShort, getApiKey } from "../api";

export default function Create() {
  const [topic, setTopic] = useState("");
  const [audience, setAudience] = useState("developers");
  const [hitl, setHitl] = useState(false);
  const [maxIterations, setMaxIterations] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!getApiKey()) {
      setError("Set an API key on Settings first.");
      return;
    }
    setBusy(true);
    try {
      const created = await createShort({
        topic: topic.trim(),
        audience: audience.trim() || "developers",
        hitl_required: hitl,
        max_iterations: maxIterations,
      });
      window.location.hash = `#/runs/${created.workflow_id}`;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>New Short</h2>
      <p className="muted">
        Enqueues a job. Keep the API and worker running or status stays queued.
      </p>
      <form onSubmit={onSubmit}>
        <label htmlFor="topic">Topic</label>
        <textarea
          id="topic"
          required
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="How to build AI agents with LangGraph"
        />
        <div className="row">
          <div>
            <label htmlFor="audience">Audience</label>
            <input
              id="audience"
              type="text"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="iters">Max iterations</label>
            <input
              id="iters"
              type="number"
              min={1}
              max={10}
              value={maxIterations}
              onChange={(e) => setMaxIterations(Number(e.target.value))}
            />
          </div>
        </div>
        <label className="check">
          <input
            type="checkbox"
            checked={hitl}
            onChange={(e) => setHitl(e.target.checked)}
          />
          Require human approval (HITL)
        </label>
        <div className="actions">
          <button className="btn" type="submit" disabled={busy || !topic.trim()}>
            {busy ? "Enqueueing…" : "Create"}
          </button>
        </div>
      </form>
      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
