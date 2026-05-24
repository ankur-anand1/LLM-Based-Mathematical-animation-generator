"""Thin wrapper around an OpenAI-compatible chat API."""

from __future__ import annotations

import base64
import re
from pathlib import Path

from openai import OpenAI

from .config import Config


class LLMClient:
    def __init__(self, config: Config):
        if not config.is_configured:
            raise ValueError(
                "No API key found. Copy .env.example to .env and set OPENAI_API_KEY."
            )
        self._config = config
        # Longer timeout + automatic retries make transient network/API
        # timeouts (ConnectTimeout, etc.) recover on their own.
        self._client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=90.0,
            max_retries=5,
        )

    def complete(self, messages: list[dict]) -> str:
        """Send chat messages and return the cleaned code string."""
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=messages,
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        return _strip_code_fences(content)

    def describe_image(self, text_prompt: str, image_path: str) -> str:
        """Ask a vision-capable model a question about an image. Returns raw text."""
        b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
        response = self._client.chat.completions.create(
            model=self._config.model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": text_prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }],
            temperature=0,
        )
        return (response.choices[0].message.content or "").strip()


def _strip_code_fences(text: str) -> str:
    """LLMs often wrap code in ```python ... ``` despite instructions; remove it."""
    text = text.strip()
    fenced = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return text
