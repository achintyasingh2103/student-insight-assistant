"""
llm/router.py
Provider abstraction layer with fallback chain.
Groq → NIM → Gemini → Claude Haiku

Each agent task is routed to the best available provider
based on task weight and current rate limit budget.
"""

import os
import time
from typing import Literal
from dotenv import load_dotenv

from groq import Groq
from openai import OpenAI as NIMClient   # NIM uses OpenAI-compatible API
import google.generativeai as genai
from anthropic import Anthropic

from llm.rate_limiter import can_send, record_request, with_backoff
from llm.cache import get_cached, set_cached
from utils.helpers import safe_json_parse, student_cache_key

load_dotenv()

# ── Provider clients ─────────────────────────────────────────────────────────

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

nim_client = NIMClient(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Model config per task type ───────────────────────────────────────────────

TASK_ROUTING = {
    # fast + light tasks → Groq 8b
    "ingestion":   {"primary": "groq",    "model": "llama-3.1-8b-instant"},
    "guardrails":  {"primary": "groq",    "model": "llama-3.1-8b-instant"},
    # heavy reasoning → NIM first (no TPM cap)
    "insight":     {"primary": "nim",     "model": "meta/llama-3.3-70b-instruct"},
    "career":      {"primary": "nim",     "model": "meta/llama-3.3-70b-instruct"},
    "report":      {"primary": "nim",     "model": "nvidia/nemotron-4-340b-instruct"},
    # dataset generation — one-off, quality matters
    "dataset":     {"primary": "groq",    "model": "llama-3.3-70b-versatile"},
}

FALLBACK_CHAIN = ["groq", "nim", "gemini", "anthropic"]

FALLBACK_MODELS = {
    "groq":      "llama-3.3-70b-versatile",
    "nim":       "meta/llama-3.3-70b-instruct",
    "gemini":    "gemini-2.0-flash",
    "anthropic": "claude-haiku-4-5-20251001",
}


# ── Core call functions ──────────────────────────────────────────────────────

def _call_groq(model: str, system: str, user: str) -> tuple[str, int]:
    response = groq_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    text = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else 500
    return text, tokens


def _call_nim(model: str, system: str, user: str) -> tuple[str, int]:
    response = nim_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=2048,
    )
    text = response.choices[0].message.content
    tokens = response.usage.total_tokens if response.usage else 500
    return text, tokens


def _call_gemini(system: str, user: str) -> tuple[str, int]:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system,
    )
    response = model.generate_content(user)
    text = response.text
    tokens = len((system + user + text).split()) * 1.3  # estimate
    return text, int(tokens)


def _call_anthropic(system: str, user: str) -> tuple[str, int]:
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    return text, tokens


# ── Main router ──────────────────────────────────────────────────────────────

def call_llm(
    task: Literal["ingestion", "guardrails", "insight", "career", "report", "dataset"],
    system_prompt: str,
    user_prompt: str,
    cache_key: str | None = None,
    estimated_tokens: int = 800,
) -> dict | str | None:
    """
    Route an LLM call to the best available provider.
    Falls back through the chain on rate limit or error.
    Returns parsed JSON if possible, raw string otherwise.
    """

    # Check cache first
    if cache_key:
        cached = get_cached(cache_key)
        if cached is not None:
            return cached

    route = TASK_ROUTING.get(task, {"primary": "groq", "model": "llama-3.3-70b-versatile"})
    primary_provider = route["primary"]
    primary_model = route["model"]

    # Build the provider attempt order: primary first, then remaining fallbacks
    providers_to_try = [primary_provider] + [
        p for p in FALLBACK_CHAIN if p != primary_provider
    ]

    last_error = None
    for provider in providers_to_try:
        if not can_send(provider, estimated_tokens):
            continue
        try:
            text, tokens_used = _dispatch(
                provider,
                primary_model if provider == primary_provider else FALLBACK_MODELS[provider],
                system_prompt,
                user_prompt,
            )
            record_request(provider, tokens_used)

            result = safe_json_parse(text) or text

            if cache_key and isinstance(result, (dict, list)):
                set_cached(cache_key, result)

            return result

        except Exception as e:
            last_error = e
            time.sleep(0.5)
            continue

    raise RuntimeError(
        f"All LLM providers exhausted for task '{task}'. Last error: {last_error}"
    )


def _dispatch(provider: str, model: str, system: str, user: str) -> tuple[str, int]:
    if provider == "groq":
        return _call_groq(model, system, user)
    elif provider == "nim":
        return _call_nim(model, system, user)
    elif provider == "gemini":
        return _call_gemini(system, user)
    elif provider == "anthropic":
        return _call_anthropic(system, user)
    raise ValueError(f"Unknown provider: {provider}")
