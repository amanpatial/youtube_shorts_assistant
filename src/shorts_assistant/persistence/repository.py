"""WorkflowRepository: domain writes for durable audit/history."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..schemas import ScriptEvaluation, ShortScript
from ..state import WorkflowState
from .models import (
    AgentExecutionRow,
    EvaluationRow,
    ExecutionRow,
    ScriptVersionRow,
    WorkflowRow,
)


def _strip_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    """Purpose: never persist API keys in checkpoint JSON."""
    banned = {"api_key", "google_api_key", "password", "token", "secret"}
    return {k: v for k, v in payload.items() if k.lower() not in banned}


class WorkflowRepository:
    """Purpose: CRUD for workflows / executions / versions / evaluations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_workflow(
        self,
        request: str,
        *,
        status: str = "CREATED",
        owner_key_id: str | None = None,
    ) -> str:
        """Purpose: insert a logical job row; return UUID string."""
        row = WorkflowRow(
            request=request.strip(),
            status=status,
            owner_key_id=owner_key_id,
        )
        self.session.add(row)
        self.session.flush()
        return str(row.id)

    def get_workflow(self, workflow_id: str) -> WorkflowRow | None:
        """Purpose: load workflow by id."""
        return self.session.get(WorkflowRow, uuid.UUID(workflow_id))

    def list_workflows(
        self,
        *,
        owner_key_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WorkflowRow]:
        """Purpose: newest-first workflows for the web UI (owner-scoped)."""
        stmt = select(WorkflowRow).order_by(WorkflowRow.created_at.desc())
        if owner_key_id:
            stmt = stmt.where(WorkflowRow.owner_key_id == owner_key_id)
        stmt = stmt.offset(max(offset, 0)).limit(max(1, min(limit, 100)))
        return list(self.session.scalars(stmt).all())

    def latest_execution(self, workflow_id: str) -> ExecutionRow | None:
        """Purpose: newest execution for a workflow (HITL / status)."""
        return self.session.scalar(
            select(ExecutionRow)
            .where(ExecutionRow.workflow_id == uuid.UUID(workflow_id))
            .order_by(ExecutionRow.started_at.desc())
            .limit(1)
        )

    def start_execution(
        self,
        workflow_id: str,
        *,
        max_iterations: int = 3,
        trace_id: str | None = None,
    ) -> str:
        """Purpose: open one pipeline run; return execution UUID string."""
        row = ExecutionRow(
            workflow_id=uuid.UUID(workflow_id),
            workflow_trace_id=trace_id,
            max_iterations=max_iterations,
            iteration=0,
        )
        self.session.add(row)
        self.session.flush()
        wf = self.session.get(WorkflowRow, uuid.UUID(workflow_id))
        if wf is not None:
            wf.status = "RUNNING"
        return str(row.id)

    def checkpoint(self, execution_id: str, state: WorkflowState | dict[str, Any]) -> None:
        """Purpose: persist latest domain checkpoint + counters on the execution."""
        if isinstance(state, WorkflowState):
            payload = _strip_secrets(state.to_dict())
            iteration = state.iteration
            best_score = state.best_score
        else:
            payload = _strip_secrets(dict(state))
            iteration = int(payload.get("iteration") or 0)
            best_score = payload.get("best_score")

        row = self.session.get(ExecutionRow, uuid.UUID(execution_id))
        if row is None:
            raise ValueError(f"unknown execution_id: {execution_id}")
        row.state_checkpoint = payload
        row.iteration = iteration
        row.best_score = float(best_score) if best_score is not None else None
        self.session.flush()

    def load_checkpoint(self, execution_id: str) -> WorkflowState | None:
        """Purpose: reload WorkflowState from domain checkpoint JSON."""
        row = self.session.get(ExecutionRow, uuid.UUID(execution_id))
        if row is None or not row.state_checkpoint:
            return None
        return WorkflowState.from_dict(row.state_checkpoint)

    def record_agent_execution(
        self,
        execution_id: str,
        *,
        agent_name: str,
        iteration: int = 0,
        status: str | None = None,
        duration_ms: int | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost_usd: float | None = None,
        retry_count: int = 0,
        error: str | None = None,
    ) -> str:
        """Purpose: append one agent history row (fail-open caller wraps this)."""
        now = datetime.now(UTC)
        row = AgentExecutionRow(
            execution_id=uuid.UUID(execution_id),
            agent_name=agent_name,
            iteration=iteration,
            status=status,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost_usd,
            retry_count=retry_count,
            error=error,
            finished_at=now,
        )
        self.session.add(row)
        self.session.flush()
        return str(row.id)

    def add_script_version(
        self,
        execution_id: str,
        *,
        iteration: int,
        script: ShortScript | dict[str, Any],
        is_best: bool = False,
        version: int | None = None,
    ) -> str:
        """Purpose: insert-only script snapshot; optionally mark as best."""
        script_payload = (
            script.model_dump(mode="json") if isinstance(script, ShortScript) else dict(script)
        )
        if version is None:
            existing = self.session.scalars(
                select(ScriptVersionRow).where(
                    ScriptVersionRow.execution_id == uuid.UUID(execution_id)
                )
            ).all()
            version = max((r.version for r in existing), default=0) + 1

        if is_best:
            self.session.execute(
                update(ScriptVersionRow)
                .where(ScriptVersionRow.execution_id == uuid.UUID(execution_id))
                .values(is_best=False)
            )

        row = ScriptVersionRow(
            execution_id=uuid.UUID(execution_id),
            iteration=iteration,
            version=version,
            script=script_payload,
            is_best=is_best,
        )
        self.session.add(row)
        self.session.flush()
        return str(row.id)

    def add_evaluation(
        self,
        execution_id: str,
        *,
        script_version_id: str,
        evaluation: ScriptEvaluation | dict[str, Any],
        iteration: int,
    ) -> str:
        """Purpose: insert-only evaluation linked to a script version."""
        if isinstance(evaluation, ScriptEvaluation):
            payload = evaluation.model_dump(mode="json")
            score = float(evaluation.overall_score)
            approved = bool(evaluation.approved)
        else:
            payload = dict(evaluation)
            score = float(payload.get("overall_score") or 0.0)
            approved = bool(payload.get("approved", False))

        row = EvaluationRow(
            execution_id=uuid.UUID(execution_id),
            script_version_id=uuid.UUID(script_version_id),
            iteration=iteration,
            evaluation=payload,
            overall_score=score,
            approved=approved,
        )
        self.session.add(row)
        self.session.flush()
        return str(row.id)

    def finish_execution(
        self,
        execution_id: str,
        *,
        final_status: str,
        error: str | None = None,
    ) -> None:
        """Purpose: mark execution finished and mirror status on workflow."""
        row = self.session.get(ExecutionRow, uuid.UUID(execution_id))
        if row is None:
            raise ValueError(f"unknown execution_id: {execution_id}")
        row.final_status = final_status
        row.error = error
        row.finished_at = datetime.now(UTC)
        wf = self.session.get(WorkflowRow, row.workflow_id)
        if wf is not None:
            wf.status = final_status
        self.session.flush()
