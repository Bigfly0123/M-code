from __future__ import annotations

import logging
import time
from typing import Any

from openai import OpenAI

from evocode_orchard_lite.models.base import Model

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a coding repair agent. Your task is to fix bugs in Python code.\n"
    "You have access to tools: list_files, read_file, search_code, edit_file, "
    "run_tests, git_diff, submit_patch.\n\n"
    "You MUST respond with exactly one JSON object on a single line, no markdown fences:\n"
    '{"thought": "<your reasoning>", "action": "<tool_name>", "arguments": {<params>}}\n\n'
    "Do NOT wrap the JSON in markdown code blocks. Output ONLY the raw JSON."
)


class LocalOpenAIModel(Model):
    """Connect to an OpenAI-compatible endpoint (vLLM, Ollama, etc.)."""

    def __init__(
        self,
        model_name: str,
        *,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "EMPTY",
        temperature: float = 0.0,
        max_tokens: int = 1024,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        **kwargs: Any,
    ):
        self.name = model_name
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.extra_kwargs = kwargs
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **self.extra_kwargs,
                )
                return response.choices[0].message.content.strip()
            except Exception as exc:
                last_exc = exc
                logger.warning("LocalOpenAI attempt %d/%d failed: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
        raise RuntimeError(f"LocalOpenAIModel failed after {self.max_retries} attempts") from last_exc
