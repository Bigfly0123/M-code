from __future__ import annotations

from abc import ABC, abstractmethod


class Model(ABC):
    """Base class for all models used in the agent loop.

    Every model must implement ``generate`` which takes a prompt string
    and returns a JSON-encoded action string.
    """

    name: str

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return a JSON action string given *prompt*."""
