"""FastAPI job API for Shorts (Phase 16/17/19)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from ..runtime_lifecycle import is_shutting_down, request_shutdown
from ..security.auth import AuthContext
from ..security.input_guard import InputGuardError
from ..security.rate_limit import get_rate_limiter
from ..security.redact import safe_api_error
from . import service
from .auth import require_api_key
from .health import register_health_routes
from .schemas import (
    ApproveRequest,
    CreateShortRequest,
    CreateShortResponse,
    EnqueueResponse,
    ResultResponse,
    ReviseRequest,
    StatusResponse,
    WorkflowListResponse,
)
from .service import ForbiddenError


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    """Purpose: validate prod config on boot; mark draining on shutdown."""
    get_settings().validate_for_production()
    yield
    request_shutdown()


def create_app() -> FastAPI:
    """Purpose: build the FastAPI application (uvicorn entry)."""
    app = FastAPI(
        title="YouTube Shorts Assistant API",
        version="0.24.0",
        description="Async job API with authz, rate limits, and guardrails",
        lifespan=_lifespan,
    )
    origins = get_settings().cors_origin_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_health_routes(app)

    def _reject_if_draining() -> None:
        if is_shutting_down():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="shutting down",
            )

    @app.post(
        "/shorts",
        response_model=CreateShortResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_short(
        body: CreateShortRequest,
        response: Response,
        auth: AuthContext = Depends(require_api_key),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    ) -> CreateShortResponse:
        _reject_if_draining()
        allowed, retry_after = get_rate_limiter().allow(auth.key_id)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={"Retry-After": str(int(retry_after) or 1)},
            )
        try:
            return service.enqueue_short(body, auth=auth, idempotency_key=idempotency_key)
        except (ValueError, InputGuardError) as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=safe_api_error(exc)) from exc
        except ForbiddenError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=safe_api_error(exc)) from exc

    @app.get("/shorts", response_model=WorkflowListResponse)
    def list_shorts(
        auth: AuthContext = Depends(require_api_key),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
    ) -> WorkflowListResponse:
        return service.list_shorts(auth=auth, limit=limit, offset=offset)

    @app.get("/shorts/{workflow_id}", response_model=StatusResponse)
    def short_status(
        workflow_id: str,
        auth: AuthContext = Depends(require_api_key),
    ) -> StatusResponse:
        try:
            return service.get_status(workflow_id, auth=auth)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="workflow not found") from None
        except ForbiddenError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=safe_api_error(exc)) from exc

    @app.get("/shorts/{workflow_id}/result", response_model=ResultResponse)
    def short_result(
        workflow_id: str,
        auth: AuthContext = Depends(require_api_key),
    ) -> ResultResponse:
        try:
            return service.get_result(workflow_id, auth=auth)
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="workflow not found") from None
        except ForbiddenError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=safe_api_error(exc)) from exc
        except LookupError as exc:
            if str(exc) == "not_ready":
                raise HTTPException(status.HTTP_409_CONFLICT, detail="result not ready") from exc
            if str(exc) == "output_policy_blocked":
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="output blocked by safety policy",
                ) from exc
            raise HTTPException(status.HTTP_409_CONFLICT, detail=safe_api_error(exc)) from exc

    @app.post(
        "/shorts/{workflow_id}/approve",
        response_model=EnqueueResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def approve(
        workflow_id: str,
        body: ApproveRequest,
        auth: AuthContext = Depends(require_api_key),
    ) -> EnqueueResponse:
        _reject_if_draining()
        try:
            return service.enqueue_approve(
                workflow_id,
                auth=auth,
                reviewer=body.reviewer,
                feedback=body.feedback,
            )
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="workflow not found") from None
        except ForbiddenError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=safe_api_error(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=safe_api_error(exc)) from exc

    @app.post(
        "/shorts/{workflow_id}/revise",
        response_model=EnqueueResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def revise(
        workflow_id: str,
        body: ReviseRequest,
        auth: AuthContext = Depends(require_api_key),
    ) -> EnqueueResponse:
        _reject_if_draining()
        try:
            return service.enqueue_revise(
                workflow_id,
                auth=auth,
                decision=body.decision,
                feedback=body.feedback,
                reviewer=body.reviewer,
            )
        except KeyError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="workflow not found") from None
        except ForbiddenError as exc:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=safe_api_error(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, detail=safe_api_error(exc)) from exc

    return app


app = create_app()
