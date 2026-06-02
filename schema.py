from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Action:
    thought: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    success: bool
    observation: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    task_id: str
    task_dir: Path
    workspace: Path
    issue: str
    metadata: dict[str, Any]


@dataclass
class Step:
    step: int
    thought: str
    action: dict[str, Any]
    observation: str
    tool_success: bool


@dataclass
class ModelConfig:
    temperature: float = 0.7
    top_p: float = 0.95
    seed: int = 42
    max_steps: int = 10
    max_tokens: int = 2048


@dataclass
class Trace:
    task_id: str
    model: str
    success: bool = False
    reward: float = 0.0
    steps: list[Step] = field(default_factory=list)
    final_patch: str = ""
    test_result: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    failure_type: str | None = None
    run_id: str = ""
    rollout_id: str = ""
    model_config: ModelConfig = field(default_factory=ModelConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
