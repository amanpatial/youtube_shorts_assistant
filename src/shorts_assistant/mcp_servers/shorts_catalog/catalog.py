"""Domain queries for the shorts_catalog MCP tools (read-only)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ...persistence.models import EvaluationRow, ExecutionRow, ScriptVersionRow, WorkflowRow
from ...persistence.session import ensure_schema, session_scope
from .schemas import GetShortArgs, ListRecentShortsArgs, SearchShortsArgs


class CatalogService:
    """Purpose: read-only catalog over executions / scripts / evaluations."""

    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def list_recent_shorts(self, *, limit: int = 5) -> dict[str, Any]:
        args = ListRecentShortsArgs(limit=limit)
        ensure_schema()

        def _run(session: Session) -> dict[str, Any]:
            rows = session.execute(
                select(ExecutionRow, WorkflowRow)
                .join(WorkflowRow, ExecutionRow.workflow_id == WorkflowRow.id)
                .where(ExecutionRow.final_status.in_(["COMPLETED", "PASSED", "EXHAUSTED"]))
                .order_by(desc(ExecutionRow.finished_at), desc(ExecutionRow.started_at))
                .limit(args.limit)
            ).all()
            items = []
            for ex, wf in rows:
                items.append(
                    {
                        "execution_id": str(ex.id),
                        "topic": wf.request,
                        "final_status": ex.final_status,
                        "best_score": ex.best_score,
                        "iteration": ex.iteration,
                    }
                )
            return {"items": items, "count": len(items)}

        if self._session is not None:
            return _run(self._session)
        with session_scope() as session:
            return _run(session)

    def search_shorts(self, *, query: str, limit: int = 5) -> dict[str, Any]:
        args = SearchShortsArgs(query=query, limit=limit)
        ensure_schema()

        def _run(session: Session) -> dict[str, Any]:
            # Filter in Python for portable SQLite/Postgres keyword match.
            rows = session.execute(
                select(ExecutionRow, WorkflowRow)
                .join(WorkflowRow, ExecutionRow.workflow_id == WorkflowRow.id)
                .order_by(desc(ExecutionRow.started_at))
                .limit(max(args.limit * 5, 20))
            ).all()
            q = args.query.lower()
            items: list[dict[str, Any]] = []
            for ex, wf in rows:
                sv = session.scalars(
                    select(ScriptVersionRow)
                    .where(ScriptVersionRow.execution_id == ex.id)
                    .where(ScriptVersionRow.is_best.is_(True))
                    .limit(1)
                ).first()
                hook = None
                if sv is not None and isinstance(sv.script, dict):
                    hook = sv.script.get("hook")
                topic = wf.request or ""
                if q not in topic.lower() and q not in (hook or "").lower():
                    continue
                items.append(
                    {
                        "execution_id": str(ex.id),
                        "topic": topic,
                        "hook": hook,
                        "best_score": ex.best_score,
                        "final_status": ex.final_status,
                    }
                )
                if len(items) >= args.limit:
                    break
            return {"query": args.query, "items": items, "count": len(items)}

        if self._session is not None:
            return _run(self._session)
        with session_scope() as session:
            return _run(session)

    def get_short(self, *, execution_id: str) -> dict[str, Any]:
        args = GetShortArgs(execution_id=uuid.UUID(str(execution_id)))
        ensure_schema()

        def _run(session: Session) -> dict[str, Any]:
            ex = session.get(ExecutionRow, args.execution_id)
            if ex is None:
                return {"found": False, "execution_id": str(args.execution_id)}
            wf = session.get(WorkflowRow, ex.workflow_id)
            sv = session.scalars(
                select(ScriptVersionRow)
                .where(ScriptVersionRow.execution_id == ex.id)
                .where(ScriptVersionRow.is_best.is_(True))
                .limit(1)
            ).first()
            if sv is None:
                sv = session.scalars(
                    select(ScriptVersionRow)
                    .where(ScriptVersionRow.execution_id == ex.id)
                    .order_by(desc(ScriptVersionRow.version))
                    .limit(1)
                ).first()
            ev = session.scalars(
                select(EvaluationRow)
                .where(EvaluationRow.execution_id == ex.id)
                .order_by(desc(EvaluationRow.created_at))
                .limit(1)
            ).first()
            script_summary = None
            if sv is not None and isinstance(sv.script, dict):
                script_summary = {
                    "title": sv.script.get("title"),
                    "hook": sv.script.get("hook"),
                    "cta": sv.script.get("cta"),
                }
            return {
                "found": True,
                "execution_id": str(ex.id),
                "topic": wf.request if wf else None,
                "final_status": ex.final_status,
                "best_score": ex.best_score,
                "iteration": ex.iteration,
                "script": script_summary,
                "evaluation": {
                    "overall_score": ev.overall_score,
                    "approved": ev.approved,
                }
                if ev is not None
                else None,
            }

        if self._session is not None:
            return _run(self._session)
        with session_scope() as session:
            return _run(session)

    def stats(self) -> dict[str, Any]:
        """Purpose: catalog://stats resource payload."""
        ensure_schema()

        def _run(session: Session) -> dict[str, Any]:
            executions = len(list(session.scalars(select(ExecutionRow)).all()))
            scripts = len(list(session.scalars(select(ScriptVersionRow)).all()))
            evaluations = len(list(session.scalars(select(EvaluationRow)).all()))
            return {
                "executions": executions,
                "script_versions": scripts,
                "evaluations": evaluations,
            }

        if self._session is not None:
            return _run(self._session)
        with session_scope() as session:
            return _run(session)
