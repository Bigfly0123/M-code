from __future__ import annotations

import logging

from evocode_orchard_lite.harness.action_parser import ActionParseError, parse_action
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.schema import Action

logger = logging.getLogger(__name__)

_RETRY_PROMPT_TEMPLATE = (
    "Your previous response was not valid JSON or was missing required fields.\n"
    "Error: {error}\n\n"
    "Your previous response:\n{raw_response}\n\n"
    "Please respond again with exactly one JSON object on a single line:\n"
    '{{"thought": "<reasoning>", "action": "<tool_name>", "arguments": {{}}}}'
)


class FormatErrorHandler:
    """Retry action parsing when the model produces malformed output.

    Returns a parsed :class:`Action` on success, or ``None`` when all retries
    are exhausted.
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def handle(self, raw_response: str, error: Exception, prompt: str, model: Model) -> Action | None:
        """Attempt to recover from a format error by asking the model to retry.

        Parameters
        ----------
        raw_response:
            The original (malformed) model output.
        error:
            The parse error that was raised.
        prompt:
            The original prompt sent to the model (not used in retry – the
            retry prompt is self-contained).
        model:
            The model instance to call for retries.

        Returns
        -------
        Action or None
            A successfully parsed action, or ``None`` if all retries fail.
        """
        last_error = error
        for attempt in range(1, self.max_retries + 1):
            retry_prompt = _RETRY_PROMPT_TEMPLATE.format(
                error=last_error,
                raw_response=raw_response[:500],
            )
            logger.info("Format error retry %d/%d", attempt, self.max_retries)
            try:
                raw_response = model.generate(retry_prompt)
            except Exception:
                logger.warning("Model call failed during format retry %d", attempt)
                continue

            try:
                return parse_action(raw_response)
            except ActionParseError as exc:
                last_error = exc
                logger.warning("Format retry %d failed: %s", attempt, exc)

        logger.warning("All %d format retries exhausted", self.max_retries)
        return None
