from __future__ import annotations


class ScriptedModel:
    def __init__(self, responses: list[str], name: str = "scripted-model"):
        self.responses = responses
        self.name = name
        self.index = 0

    def generate(self, prompt: str) -> str:
        if self.index >= len(self.responses):
            return '{"thought": "No more scripted actions.", "action": "submit_patch", "arguments": {}}'
        response = self.responses[self.index]
        self.index += 1
        return response
