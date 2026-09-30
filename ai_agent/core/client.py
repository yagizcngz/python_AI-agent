"""
OpenAI / OpenRouter API client creation, model discovery, and recovery helpers.
"""

import sys
from typing import List, Optional
from openai import OpenAI
from ..config import (
    BASE_URL,
    DEFAULT_API_TIMEOUT,
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_OPENROUTER_BASE_URL,
    RECOMMENDED_FREE_MODELS,
    get_api_key,
    is_local_url,
)


def create_client(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    is_local: bool = False,
    timeout: float = DEFAULT_API_TIMEOUT,
) -> OpenAI:
    """
    Create and configure an OpenAI client instance.
    Supports OpenRouter, local Ollama/LM Studio servers, or any OpenAI-compatible API.
    """
    effective_base_url = base_url or (DEFAULT_LOCAL_BASE_URL if is_local else BASE_URL)
    effective_api_key = api_key or get_api_key()

    # For local loopback endpoints (Ollama, LM Studio), any dummy key is accepted
    if not effective_api_key and is_local_url(effective_base_url):
        effective_api_key = "ollama-local"

    if not effective_api_key:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Please configure it in your environment, "
            "add it to a .env file, or pass --local to connect to a local server."
        )

    return OpenAI(api_key=effective_api_key, base_url=effective_base_url, timeout=timeout)


def fetch_models(client: OpenAI, only_free: bool = True) -> List[str]:
    """Fetch active models from the endpoint."""
    try:
        models = client.models.list()
        all_ids = [m.id for m in models.data]
        if only_free:
            free_ids = [m_id for m_id in all_ids if ":free" in m_id]
            if free_ids:
                return free_ids
        return all_ids
    except Exception as e:
        print(f"Notice: Failed to fetch live models from API ({e}). Using defaults.", file=sys.stderr)
        return list(RECOMMENDED_FREE_MODELS)


def get_model_suggestions(current_model: str) -> List[str]:
    """Return alternative free models excluding the current one."""
    return [m for m in RECOMMENDED_FREE_MODELS if m != current_model]


def fetch_account_usage(api_key: Optional[str] = None) -> Optional[dict]:
    """
    Fetch live remaining limits and usage metrics from OpenRouter key endpoint.
    Returns None if offline, using local models, or if request fails.
    """
    key = api_key or get_api_key()
    if not key or key.startswith("ollama"):
        return None

    import json
    import time
    import urllib.request

    try:
        url = f"https://openrouter.ai/api/v1/key?_={int(time.time() * 1000)}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "User-Agent": "python-ai-agent",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=5.0) as res:
            payload = json.loads(res.read().decode("utf-8"))
            return payload.get("data")
    except Exception:
        return None


_MODEL_CACHE: Optional[set[str]] = None


def get_all_valid_models(force_refresh: bool = False) -> set[str]:
    """
    Fetch and cache the full set of valid OpenRouter model IDs.
    Returns cached set if already fetched in the current process.
    """
    global _MODEL_CACHE
    if _MODEL_CACHE is not None and not force_refresh:
        return _MODEL_CACHE

    import json
    import urllib.request

    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"User-Agent": "python-ai-agent"},
        )
        with urllib.request.urlopen(req, timeout=6.0) as res:
            data = json.loads(res.read().decode("utf-8"))
            models = {m["id"] for m in data.get("data", [])}
            if models:
                _MODEL_CACHE = models
                return _MODEL_CACHE
    except Exception:
        pass

    if _MODEL_CACHE is None:
        _MODEL_CACHE = set(RECOMMENDED_FREE_MODELS)
    return _MODEL_CACHE


def get_all_free_models(force_refresh: bool = False) -> List[str]:
    """Fetch and return all active free models (:free) from OpenRouter."""
    models = get_all_valid_models(force_refresh=force_refresh)
    free = [m for m in models if ":free" in m]
    if not free:
        return list(RECOMMENDED_FREE_MODELS)
    return sorted(free)


def validate_model_id(
    model_id: str,
    is_local: bool = False,
    base_url: Optional[str] = None,
) -> tuple[bool, str]:
    """
    Check if a model exists on OpenRouter or local server.
    Returns (is_valid, resolved_model_or_error_message).
    """
    cleaned = model_id.strip()
    if not cleaned:
        return False, "Model ID cannot be empty."

    # If it's a local Ollama model
    if is_local or cleaned.startswith("ollama/"):
        return True, cleaned[7:] if cleaned.startswith("ollama/") else cleaned

    if cleaned in RECOMMENDED_FREE_MODELS:
        return True, cleaned

    valid_models = get_all_valid_models()

    if cleaned in valid_models:
        return True, cleaned

    # Check without :free suffix if present, or with :free suffix
    if cleaned.endswith(":free") and cleaned[:-5] in valid_models:
        return True, cleaned
    if f"{cleaned}:free" in valid_models:
        return True, cleaned

    # Case-insensitive match check
    lowered = {m.lower(): m for m in valid_models}
    if cleaned.lower() in lowered:
        return True, lowered[cleaned.lower()]

    base_lower = cleaned[:-5].lower() if cleaned.endswith(":free") else cleaned.lower()
    if base_lower in lowered:
        return True, lowered[base_lower]

    return False, f"Model '{cleaned}' does not exist on OpenRouter."

