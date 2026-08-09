import type { AgentStep } from "../types";

type Props = { agents: AgentStep[] };

export default function AgentPipeline({ agents }: Props) {
  if (!agents.length) {
    return null;
  }
  return (
    <div className="pipeline" aria-label="Agent pipeline">
      {agents.map((step, i) => (
        <div key={step.id} className="pipeline-item">
          {i > 0 ? <div className={`pipeline-line ${step.state}`} /> : null}
          <div className={`pipeline-node ${step.state}`} title={`${step.label}: ${step.state}`}>
            <span className="pipeline-dot" />
            <span className="pipeline-label">{step.label}</span>
            <span className="pipeline-state">{step.state}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
