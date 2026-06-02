from __future__ import annotations

import logging
import time
from typing import Any

import litellm

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


class LiteLLMChatModel(Model):
    """Call any LLM through the litellm library.

    Supports OpenAI, Anthropic, DeepSeek, etc. – anything litellm can route.
    API keys are picked up from environment variables automatically.
    """

    def __init__(
        self,
        model_name: str,
        *,
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

    def generate(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = litellm.completion(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **self.extra_kwargs,
                )
                return response.choices[0].message.content.strip()
            except Exception as exc:
                last_exc = exc
                logger.warning("LiteLLM attempt %d/%d failed: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * attempt)
        raise RuntimeError(f"LiteLLMChatModel failed after {self.max_retries} attempts") from last_exc
