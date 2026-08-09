export type ApiStatus =
  | "queued"
  | "running"
  | "awaiting_human"
  | "succeeded"
  | "failed"
  | "cancelled";

export type AgentStepState = "pending" | "running" | "paused" | "done" | "failed";

export type AgentStep = {
  id: string;
  label: string;
  state: AgentStepState;
};

export type StatusResponse = {
  workflow_id: string;
  status: ApiStatus;
  execution_id: string | null;
  iteration: number | null;
  best_score: number | null;
  error: string | null;
  topic: string | null;
  created_at: string | null;
  agents?: AgentStep[];
};

export type WorkflowListItem = {
  workflow_id: string;
  topic: string;
  status: ApiStatus;
  execution_id: string | null;
  iteration: number | null;
  best_score: number | null;
  created_at: string | null;
};

export type ScriptSection = {
  label?: string;
  text?: string;
  estimated_seconds?: number;
};

export type GeneratedScript = {
  title?: string;
  hook?: string;
  body?: string;
  cta?: string;
  target_audience?: string;
  estimated_duration_seconds?: number;
  sections?: ScriptSection[];
};

export type Evaluation = {
  overall_score?: number;
  hook_score?: number;
  clarity_score?: number;
  pacing_score?: number;
  technical_accuracy?: number;
  factual_correctness?: number;
  developer_value?: number;
  duration_score?: number;
  cta_score?: number;
  tone_score?: number;
  issues?: string[];
  approved?: boolean;
  summary?: string;
};

export type VisualShot = {
  beat?: string;
  description?: string;
  on_screen_text?: string;
  shot_type?: string;
};

export type VisualPlan = {
  shots?: VisualShot[];
  pacing?: string;
  graphics_notes?: string;
  b_roll?: string[];
};

export type ConceptRow = {
  timestamp_or_beat?: string;
  spoken_line?: string;
  visual?: string;
};

export type ShortConcept = {
  hook?: string;
  script_and_visuals?: ConceptRow[];
  visual_notes?: string;
  cta?: string;
  quality_notes?: string | null;
};

export type ResultResponse = {
  workflow_id: string;
  status: ApiStatus;
  final_short_concept: ShortConcept | null;
  generated_script: GeneratedScript | null;
  research: string | null;
  evaluation: Evaluation | null;
  visual_concepts: VisualPlan | null;
  memory_context: string | null;
  retrieved_memory_ids: string[];
  trace_id: string | null;
  execution_id: string | null;
  script_version: number | null;
  max_iterations: number | null;
  human_decision: string | null;
  human_feedback: string | null;
  human_reviewer: string | null;
  human_revision_count: number | null;
  error_class: string | null;
  error_node: string | null;
  agents?: AgentStep[];
};
