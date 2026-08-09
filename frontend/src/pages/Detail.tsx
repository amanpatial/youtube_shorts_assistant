import { FormEvent, useEffect, useState } from "react";
import { ApiError, approve, getResult, getStatus, revise } from "../api";
import AgentPipeline from "../components/AgentPipeline";
import type { Evaluation, ResultResponse, StatusResponse } from "../types";

type Props = { workflowId: string };

const SCORE_KEYS: { key: keyof Evaluation; label: string }[] = [
  { key: "overall_score", label: "Overall" },
  { key: "hook_score", label: "Hook" },
  { key: "clarity_score", label: "Clarity" },
  { key: "pacing_score", label: "Pacing" },
  { key: "cta_score", label: "CTA" },
  { key: "tone_score", label: "Tone" },
  { key: "developer_value", label: "Dev value" },
  { key: "technical_accuracy", label: "Technical" },
  { key: "factual_correctness", label: "Factual" },
  { key: "duration_score", label: "Duration" },
];

function asText(value: unknown): string {
  if (value == null) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

export default function Detail({ workflowId }: Props) {
  const [status, setStatus] = useState<StatusResponse | null>(null);
  const [result, setResult] = useState<ResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function tick() {
      try {
        const st = await getStatus(workflowId);
        if (cancelled) {
          return;
        }
        setStatus(st);
        setError(null);
        if (st.status === "succeeded" || st.status === "awaiting_human") {
          try {
            const res = await getResult(workflowId);
            if (!cancelled) {
              setResult(res);
            }
          } catch (err) {
            if (err instanceof ApiError && err.status === 409) {
              if (!cancelled) {
                setResult(null);
              }
            } else if (!cancelled) {
              setError(err instanceof Error ? err.message : String(err));
            }
          }
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : String(err));
        }
      }
    }
    void tick();
    const id = window.setInterval(() => {
      void tick();
    }, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [workflowId]);

  async function onApprove() {
    setBusy(true);
    setError(null);
    try {
      await approve(workflowId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onRevise(e: FormEvent) {
    e.preventDefault();
    if (!feedback.trim()) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await revise(workflowId, feedback.trim());
      setFeedback("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const script = result?.generated_script;
  const concept = result?.final_short_concept;
  const evaluation = result?.evaluation;
  const visuals = result?.visual_concepts;
  const shots = visuals?.shots ?? [];
  const rows = concept?.script_and_visuals ?? [];

  return (
    <div className="card">
      <h2>Run</h2>
      <p className="muted">
        <code>{workflowId}</code>
        {result?.execution_id ? (
          <>
            {" "}
            · exec <code>{result.execution_id}</code>
          </>
        ) : null}
        {result?.trace_id ? (
          <>
            {" "}
            · <code>{result.trace_id}</code>
          </>
        ) : null}
      </p>
      {status ? (
        <p>
          <span className={`badge ${status.status}`}>{status.status}</span>
          {status.topic ? <> · {status.topic}</> : null}
          {status.best_score != null ? <> · score {status.best_score}</> : null}
          {status.iteration != null ? (
            <>
              {" "}
              · iter {status.iteration}
              {result?.max_iterations != null ? `/${result.max_iterations}` : ""}
            </>
          ) : null}
          {result?.script_version != null ? <> · script v{result.script_version}</> : null}
        </p>
      ) : (
        <p className="muted">Loading…</p>
      )}
      <AgentPipeline agents={status?.agents?.length ? status.agents : (result?.agents ?? [])} />
      {status?.created_at ? (
        <p className="muted">{status.created_at.replace("T", " ").slice(0, 19)}</p>
      ) : null}
      {status?.error ? <p className="error">{status.error}</p> : null}
      {result?.error_node ? (
        <p className="error">
          Failed at {result.error_node}
          {result.error_class ? ` (${result.error_class})` : ""}
        </p>
      ) : null}
      {error ? <p className="error">{error}</p> : null}

      {status?.status === "queued" || status?.status === "running" ? (
        <p className="muted">Waiting for the worker… polling every 2s.</p>
      ) : null}

      {status?.status === "awaiting_human" ? (
        <div>
          <h3>Human review</h3>
          {result?.human_reviewer ? (
            <p className="muted">
              Last: {result.human_decision ?? "—"} by {result.human_reviewer}
              {result.human_revision_count
                ? ` · revisions ${result.human_revision_count}`
                : ""}
            </p>
          ) : null}
          {result?.human_feedback ? <pre>{result.human_feedback}</pre> : null}
          <div className="actions">
            <button className="btn" type="button" disabled={busy} onClick={() => void onApprove()}>
              Approve
            </button>
          </div>
          <form onSubmit={(e) => void onRevise(e)}>
            <label htmlFor="feedback">Request changes</label>
            <textarea
              id="feedback"
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="Make the CTA sharper"
            />
            <div className="actions">
              <button className="btn secondary" type="submit" disabled={busy || !feedback.trim()}>
                Send revision
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {result?.research ? (
        <div>
          <h3>Research</h3>
          <pre>{result.research}</pre>
        </div>
      ) : null}

      {result?.memory_context ? (
        <div>
          <h3>Retrieved memory</h3>
          <pre>{result.memory_context}</pre>
        </div>
      ) : null}

      {evaluation ? (
        <div>
          <h3>
            Evaluation{" "}
            {evaluation.approved ? (
              <span className="badge succeeded">approved</span>
            ) : (
              <span className="badge failed">not approved</span>
            )}
          </h3>
          {evaluation.summary ? <p>{evaluation.summary}</p> : null}
          <div className="score-grid">
            {SCORE_KEYS.map(({ key, label }) => {
              const value = evaluation[key];
              if (typeof value !== "number") {
                return null;
              }
              return (
                <div key={key} className="score-cell">
                  <span className="muted">{label}</span>
                  <strong>{value}</strong>
                </div>
              );
            })}
          </div>
          {evaluation.issues && evaluation.issues.length > 0 ? (
            <ul>
              {evaluation.issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {script ? (
        <div className="script-grid">
          {script.title ? (
            <div>
              <h3>Title</h3>
              <pre>{script.title}</pre>
            </div>
          ) : null}
          <div>
            <h3>Hook</h3>
            <pre>{asText(script.hook)}</pre>
          </div>
          <div>
            <h3>Body</h3>
            <pre>{asText(script.body)}</pre>
          </div>
          <div>
            <h3>CTA</h3>
            <pre>{asText(script.cta)}</pre>
          </div>
          <p className="muted">
            {script.target_audience ? <>Audience: {script.target_audience}</> : null}
            {script.estimated_duration_seconds != null ? (
              <> · ~{script.estimated_duration_seconds}s</>
            ) : null}
          </p>
          {script.sections && script.sections.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Beat</th>
                  <th>Text</th>
                  <th>Sec</th>
                </tr>
              </thead>
              <tbody>
                {script.sections.map((sec, i) => (
                  <tr key={`${sec.label ?? i}`}>
                    <td>{sec.label ?? "—"}</td>
                    <td>{sec.text ?? ""}</td>
                    <td>{sec.estimated_seconds ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      ) : null}

      {shots.length > 0 ? (
        <div>
          <h3>Visual plan</h3>
          {visuals?.pacing ? <p className="muted">{visuals.pacing}</p> : null}
          {visuals?.graphics_notes ? <p className="muted">{visuals.graphics_notes}</p> : null}
          {visuals?.b_roll && visuals.b_roll.length > 0 ? (
            <p className="muted">B-roll: {visuals.b_roll.join(", ")}</p>
          ) : null}
          <table className="table">
            <thead>
              <tr>
                <th>Beat</th>
                <th>Shot</th>
                <th>On-screen</th>
                <th>Type</th>
              </tr>
            </thead>
            <tbody>
              {shots.map((shot, i) => (
                <tr key={`${shot.beat ?? i}`}>
                  <td>{shot.beat ?? "—"}</td>
                  <td>{shot.description ?? ""}</td>
                  <td>{shot.on_screen_text || "—"}</td>
                  <td>{shot.shot_type ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {concept ? (
        <div>
          <h3>Final concept</h3>
          {concept.hook ? (
            <>
              <h3>Hook</h3>
              <pre>{concept.hook}</pre>
            </>
          ) : null}
          {rows.length > 0 ? (
            <table className="table">
              <thead>
                <tr>
                  <th>Beat</th>
                  <th>Spoken</th>
                  <th>Visual</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={`${row.timestamp_or_beat ?? i}`}>
                    <td>{row.timestamp_or_beat ?? "—"}</td>
                    <td>{row.spoken_line ?? ""}</td>
                    <td>{row.visual ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {concept.visual_notes ? (
            <>
              <h3>Visual notes</h3>
              <pre>{concept.visual_notes}</pre>
            </>
          ) : null}
          {concept.cta ? (
            <>
              <h3>CTA</h3>
              <pre>{concept.cta}</pre>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
