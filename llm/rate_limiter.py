"""
llm/rate_limiter.py
Token budget tracker + exponential backoff queue.
Tracks rolling 60s windows for both RPM and TPM per provider.
"""

import time
import threading
from collections import deque
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Per-provider rolling window limits
PROVIDER_LIMITS = {
    "groq": {
        "rpm": 30,
        "tpm": 6000,
    },
    "nim": {
        "rpm": 40,
        "tpm": float("inf"),  # NIM has no token cap
    },
    "gemini": {
        "rpm": 60,
        "tpm": 1_000_000,
    },
    "anthropic": {
        "rpm": 50,
        "tpm": 100_000,
    },
}

_lock = threading.Lock()

# Rolling windows: {provider: deque of (timestamp, tokens)}
_request_windows: dict[str, deque] = {p: deque() for p in PROVIDER_LIMITS}
_token_windows: dict[str, deque] = {p: deque() for p in PROVIDER_LIMITS}


def _purge_old(window: deque, window_secs: int = 60) -> None:
    now = time.time()
    while window and now - window[0][0] > window_secs:
        window.popleft()


def can_send(provider: str, estimated_tokens: int = 500) -> bool:
    limits = PROVIDER_LIMITS.get(provider, {})
    with _lock:
        _purge_old(_request_windows[provider])
        _purge_old(_token_windows[provider])

        current_rpm = len(_request_windows[provider])
        current_tpm = sum(t for _, t in _token_windows[provider])

        if current_rpm >= limits.get("rpm", 999):
            return False
        if current_tpm + estimated_tokens > limits.get("tpm", float("inf")):
            return False
        return True


def record_request(provider: str, tokens_used: int) -> None:
    now = time.time()
    with _lock:
        _request_windows[provider].append((now, 1))
        _token_windows[provider].append((now, tokens_used))


def budget_status(provider: str) -> dict:
    limits = PROVIDER_LIMITS.get(provider, {})
    with _lock:
        _purge_old(_request_windows[provider])
        _purge_old(_token_windows[provider])
        return {
            "provider": provider,
            "rpm_used": len(_request_windows[provider]),
            "rpm_limit": limits.get("rpm", "∞"),
            "tpm_used": sum(t for _, t in _token_windows[provider]),
            "tpm_limit": limits.get("tpm", "∞"),
        }


def all_budget_status() -> list[dict]:
    return [budget_status(p) for p in PROVIDER_LIMITS]


# Retry decorator for LLM calls — exponential backoff on rate limit errors
def with_backoff(func):
    return retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=16),
        stop=stop_after_attempt(4),
    )(func)
