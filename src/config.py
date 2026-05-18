"""Central configuration loaded from environment / .env file."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# override=True so values in .env win over any stale system environment
# variables (e.g. a leftover OPENAI_API_KEY set on the machine).
load_dotenv(override=True)

# An EMPTY OPENAI_BASE_URL ("") would be read by the OpenAI SDK as a malformed
# server address. Remove it so the SDK falls back to the default OpenAI URL.
if not os.environ.get("OPENAI_BASE_URL", "").strip():
    os.environ.pop("OPENAI_BASE_URL", None)


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str
    base_url: str | None
    # How many times the generator is allowed to ask the LLM to fix broken code.
    max_repair_attempts: int = 5
    # Render quality flag passed to manim: l=low, m=medium, h=high.
    quality: str = "m"

    @classmethod
    def load(cls) -> "Config":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        return cls(
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "gpt-4o").strip(),
            base_url=(os.getenv("OPENAI_BASE_URL") or None),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)
