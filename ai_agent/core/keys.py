"""
API key rotation and multi-key quota management.
Supports automatic failover across multiple keys in API_KEYS_OPEN_ROUTER.txt.
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
from ..config import PROJECT_ROOT


def is_quota_or_rate_limit_error(e: Exception) -> bool:
    """Check if an exception indicates a rate limit or exhausted quota."""
    status_code = getattr(e, "status_code", None)
    if status_code in (402, 429):
        return True

    msg = str(e).lower()
    quota_keywords = [
        "rate limit",
        "rate_limit",
        "429",
        "quota",
        "credit",
        "402",
        "daily limit",
        "usage limit",
        "insufficient",
        "free model daily",
    ]
    return any(keyword in msg for keyword in quota_keywords)


class KeyManager:
    """
    Manages multiple OpenRouter API keys with automatic failover and rotation.
    Loads keys from API_KEYS_OPEN_ROUTER.txt and active environment variables.
    """

    def __init__(self, key_file: Optional[Path] = None, keys: Optional[List[str]] = None):
        self.key_file = key_file or (PROJECT_ROOT / "API_KEYS_OPEN_ROUTER.txt")
        if keys is not None:
            self.keys: List[str] = list(keys)
        else:
            self.keys = self._load_keys()
        self.current_index: int = 0
        self.exhausted_keys: set[str] = set()

    def _load_keys(self) -> List[str]:
        """Load unique, non-empty keys from file and environment."""
        keys: List[str] = []

        search_paths = [
            self.key_file,
            PROJECT_ROOT / "app" / "API_KEYS_OPEN_ROUTER.txt",
        ]

        # Prioritize keys found in API_KEYS_OPEN_ROUTER.txt
        for path in search_paths:
            if path and path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            clean = line.strip()
                            if clean and not clean.startswith("#") and clean not in keys:
                                keys.append(clean)
                except Exception:
                    pass

        # Also append current env key if set and not already present
        env_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if env_key and env_key not in keys and not env_key.startswith("ollama"):
            keys.insert(0, env_key)

        return keys

    @property
    def total_keys(self) -> int:
        return len(self.keys)

    @property
    def has_multiple_keys(self) -> bool:
        return len(self.keys) > 1

    def get_current_key(self) -> str:
        """Return the currently active API key."""
        if not self.keys:
            return os.getenv("OPENROUTER_API_KEY", "").strip()
        if self.current_index >= len(self.keys):
            self.current_index = 0
        return self.keys[self.current_index]

    def rotate_key(self) -> Tuple[bool, str, str]:
        """
        Advance to the next unexhausted API key.
        Returns: (success: bool, new_key: str, message: str)
        """
        if not self.keys:
            return (
                False,
                "",
                "No API keys found in API_KEYS_OPEN_ROUTER.txt or environment variables.",
            )

        current = self.get_current_key()
        if current:
            self.exhausted_keys.add(current)

        # Search for the next unexhausted key
        for offset in range(1, len(self.keys) + 1):
            next_idx = (self.current_index + offset) % len(self.keys)
            candidate = self.keys[next_idx]
            if candidate not in self.exhausted_keys:
                self.current_index = next_idx
                os.environ["OPENROUTER_API_KEY"] = candidate
                masked = f"{candidate[:8]}...{candidate[-4:]}" if len(candidate) > 12 else "key"
                msg = f"Switched to API key {self.current_index + 1} of {len(self.keys)} ({masked})."
                return True, candidate, msg

        # All keys in the file have been exhausted
        return (
            False,
            "",
            f"All {len(self.keys)} API keys in API_KEYS_OPEN_ROUTER.txt have exhausted their usage limit.",
        )
