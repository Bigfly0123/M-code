"""Run rollouts for benchmark tasks with proper trace management.

Usage:
    python -m evocode_orchard_lite.run_rollouts \
        --run-id 20260531_qwen25_7b_t07 \
        --profile xiaomi \
        --rollouts-per-task 2 \
        --temperature 0.7 \
        --max-steps 10 \
        --resume
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from dotenv import load_dotenv

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.eval.metrics import summarize_traces
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.schema import ModelConfig, Trace
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger, Manifest

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# Profiles
_PROFILES: dict[str, dict[str, str]] = {
    "xiaomi": {
        "base_url_env": "XIAOMI_BASE_URL",
        "model_name_env": "XIAOMI_MODEL_NAME",
        "api_key_env": "XIAOMI_API_KEY",
    },
    "bailian": {
        "base_url_env": "BAILIAN_BASE_URL",
        "model_name_env": "BAILIAN_MODEL_NAME",
        "api_key_env": "BAILIAN_API_KEY",
    },
    "deepseek": {
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_name_env": "DEEPSEEK_MODEL_NAME",
        "api_key_env": "DEEPSEEK_API_KEY",
    },
}


def build_model(args: argparse.Namespace) -> Model:
    if args.model_type == "litellm":
        from evocode_orchard_lite.models.litellm_chat_model import LiteLLMChatModel
        return LiteLLMChatModel(
            model_name=args.model_name,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    if args.model_type in ("openai_compatible", "local"):
        from evocode_orchard_lite.models.local_openai_model import LocalOpenAIModel
        return LocalOpenAIModel(
            model_name=args.model_name,
            base_url=args.base_url,
            api_key=args.api_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    raise ValueError(f"Unknown model type: {args.model_type}")


def generate_run_id(prefix: str, model_name: str, temperature: float) -> str:
    """Generate a run ID from prefix, model name, and temperature."""
    model_slug = model_name.split("/")[-1].replace("-", "_").lower()[:20]
    temp_slug = f"t{int(temperature * 10):02d}"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{model_slug}_{temp_slug}_{timestamp}"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tasks_root = root / "benchmark" / "tasks"

    parser = argparse.ArgumentParser(description="Run rollouts for benchmark tasks.")
    parser.add_argument("--run-id", type=str, help="Run ID. Auto-generated if not provided.")
    parser.add_argument("--profile", choices=list(_PROFILES.keys()), help="Model profile.")
    parser.add_argument("--model-type", default="openai_compatible", choices=["litellm", "openai_compatible", "local"])
    parser.add_argument("--model-name", type=str, help="Model name.")
    parser.add_argument("--base-url", type=str, help="API base URL.")
    parser.add_argument("--api-key", type=str, help="API key.")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--max-format-retries", type=int, default=3)
    parser.add_argument("--rollouts-per-task", type=int, default=2)
    parser.add_argument("--task", action="append", dest="tasks", help="Specific task(s) to run.")
    parser.add_argument("--tasks-file", type=Path, help="File with task IDs, one per line.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resume", action="store_true", help="Resume from manifest.")
    parser.add_argument("--limit", type=int, help="Limit number of tasks.")
    parser.add_argument("--output-root", type=Path, default=root / "outputs")
    args = parser.parse_args()

    # Resolve model config from profile
    if args.profile:
        profile = _PROFILES[args.profile]
        args.base_url = args.base_url or __import__("os").environ.get(profile["base_url_env"], "")
        args.model_name = args.model_name or __import__("os").environ.get(profile["model_name_env"], "")
        args.api_key = args.api_key or __import__("os").environ.get(profile["api_key_env"], "")

    # Generate run ID if not provided
    if not args.run_id:
        args.run_id = generate_run_id("run", args.model_name, args.temperature)

    # Load tasks
    if args.tasks_file and args.tasks_file.exists():
        selected = [line.strip() for line in args.tasks_file.read_text().splitlines() if line.strip()]
    elif args.tasks:
        selected = args.tasks
    else:
        selected = sorted(path.name for path in tasks_root.iterdir() if path.is_dir())

    if args.limit:
        selected = selected[:args.limit]

    logger.info("Run ID: %s", args.run_id)
    logger.info("Tasks: %d", len(selected))
    logger.info("Rollouts per task: %d", args.rollouts_per_task)
    logger.info("Temperature: %.2f", args.temperature)

    # Setup manifest
    manifest_path = args.output_root / "rollouts" / args.run_id / "manifest.jsonl"
    manifest = Manifest(manifest_path)
    completed = manifest.completed_keys() if args.resume else set()

    if args.resume and completed:
        logger.info("Resuming: %d rollouts already completed", len(completed))

    # Setup environment and model
    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=args.output_root / "workspaces")
    trace_logger = TraceLogger(args.output_root)
    model = build_model(args)
    model_config = ModelConfig(
        temperature=args.temperature,
        top_p=0.95,
        seed=args.seed,
        max_steps=args.max_steps,
        max_tokens=args.max_tokens,
    )

    logger.info("Model: %s (type=%s)", model.name, args.model_type)

    traces: list[Trace] = []
    total_expected = len(selected) * args.rollouts_per_task
    total_completed = len(completed)

    for task_id in selected:
        for rollout_idx in range(args.rollouts_per_task):
            rollout_id = f"{rollout_idx:04d}"
            key = (task_id, rollout_id)

            if args.resume and key in completed:
                logger.info("Skipping %s/%s (already completed)", task_id, rollout_id)
                continue

            logger.info("Running %s/%s (%d/%d)", task_id, rollout_id, total_completed + 1, total_expected)

            task = env.load_task(task_id)
            agent = AgentLoop(auto_save=False, 
                model=model,
                tools=default_tool_registry(),
                trace_logger=trace_logger,
                max_steps=args.max_steps,
                max_format_retries=args.max_format_retries,
            )

            trace = agent.run(task)
            trace.run_id = args.run_id
            trace.rollout_id = rollout_id
            trace.model_config = model_config

            # Save trace
            trace_path = trace_logger.save(trace)

            # Update manifest
            trace_summary = {
                "run_id": args.run_id,
                "task_id": task_id,
                "rollout_id": rollout_id,
                "status": "success" if trace.success else "failed",
                "trace_path": str(trace_path),
                "model": model.name,
                "temperature": args.temperature,
                "top_p": 0.95,
                "seed": args.seed,
                "max_steps": args.max_steps,
                "success": trace.success,
                "reward": trace.reward,
                "failure_type": trace.failure_type,
                "num_steps": len(trace.steps),
            }
            manifest.append(trace_summary)

            traces.append(trace)
            total_completed += 1

            status = "SUCCESS" if trace.success else "FAILED"
            logger.info("  %s | reward=%.2f | steps=%d | failure=%s", status, trace.reward, len(trace.steps), trace.failure_type)

    # Generate summary
    summary = vars(summarize_traces(traces))
    summary["run_id"] = args.run_id
    summary["total_expected"] = total_expected
    summary["total_completed"] = total_completed

    # Save summary
    summary_path = args.output_root / "rollouts" / args.run_id / "reports" / "run_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("Run complete: %d/%d rollouts", total_completed, total_expected)
    logger.info("Summary: %s", json.dumps(summary, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
