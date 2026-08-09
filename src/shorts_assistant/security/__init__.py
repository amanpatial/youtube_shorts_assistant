"""Practical API + AI guardrails (Phase 17)."""

from .auth import AuthContext, key_id_for, verify_api_key
from .input_guard import InputGuardError, guard_topic
from .output_policy import OutputPolicyResult, check_output_policy
from .rate_limit import get_rate_limiter, reset_rate_limiter_for_tests
from .redact import redact_secret_text, safe_api_error

__all__ = [
    "AuthContext",
    "InputGuardError",
    "OutputPolicyResult",
    "check_output_policy",
    "get_rate_limiter",
    "guard_topic",
    "key_id_for",
    "redact_secret_text",
    "reset_rate_limiter_for_tests",
    "safe_api_error",
    "verify_api_key",
]
