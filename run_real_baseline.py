from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from evocode_orchard_lite.env_lite import CodeRepairEnv
from evocode_orchard_lite.eval.failure_analysis import analyze_failures, write_failure_taxonomy
from evocode_orchard_lite.eval.metrics import summarize_traces
from evocode_orchard_lite.eval.report_generator import write_real_baseline_report
from evocode_orchard_lite.harness import AgentLoop
from evocode_orchard_lite.models.base import Model
from evocode_orchard_lite.schema import Trace
from evocode_orchard_lite.tools import default_tool_registry
from evocode_orchard_lite.trajectory import TraceLogger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Profiles: read BASE_URL / MODEL_NAME / API_KEY from env vars with this prefix.
# E.g. profile "xiaomi" reads XIAOMI_BASE_URL, XIAOMI_MODEL_NAME, XIAOMI_API_KEY.
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


def run_real_baseline(args: argparse.Namespace) -> tuple[list[Trace], dict]:
    root = Path(__file__).resolve().parents[1]
    tasks_root = root / "benchmark" / "tasks"
    all_task_ids = sorted(path.name for path in tasks_root.iterdir() if path.is_dir())
    selected = args.tasks if args.tasks else all_task_ids

    model = build_model(args)
    logger.info("Model: %s (type=%s)", model.name, args.model_type)

    env = CodeRepairEnv(tasks_root=tasks_root, workspaces_root=root / "outputs" / "workspaces")
    trace_logger = TraceLogger(root / "outputs" / "traces")
    traces: list[Trace] = []

    for task_id in selected:
        logger.info("Running task: %s", task_id)
        task = env.load_task(task_id)
        agent = AgentLoop(
            model=model,
            tools=default_tool_registry(),
            trace_logger=trace_logger,
            max_steps=args.max_steps,
            max_format_retries=args.max_format_retries,
        )
        trace = agent.run(task)
        status = "SUCCESS" if trace.success else "FAILED"
        logger.info("  %s | reward=%.2f | steps=%d | failure=%s", status, trace.reward, len(trace.steps), trace.failure_type)
        traces.append(trace)

    summary = summarize_traces(traces)

    task_metadata_map = {}
    for task_id in selected:
        meta_path = tasks_root / task_id / "metadata.json"
        if meta_path.exists():
            task_metadata_map[task_id] = json.loads(meta_path.read_text(encoding="utf-8"))

    failure = analyze_failures(traces, task_metadata_map)

    reports_dir = root / "outputs" / "reports"
    write_real_baseline_report(
        reports_dir / "real_baseline_report.md",
        traces,
        summary,
        failure,
    )
    write_failure_taxonomy(reports_dir / "failure_taxonomy.json", failure)

    (reports_dir / "real_baseline_summary.json").write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("Summary: %s", json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
    return traces, summary.to_dict()


def main() -> int:
    # Load .env from project root
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")

    parser = argparse.ArgumentParser(description="Run EvoCode-Orchard-Lite real-model baseline evaluation.")
    parser.add_argument(
        "--model-type",
        choices=["litellm", "openai_compatible", "local"],
        default=None,
        help=(
            "Model backend: 'litellm' for litellm-routed API models; "
            "'openai_compatible' (alias: 'local') for any OpenAI-compatible endpoint. "
            "Defaults to 'openai_compatible' when using --profile."
        ),
    )
    parser.add_argument(
        "--profile",
        choices=list(_PROFILES.keys()),
        default=None,
        help="Read base_url / model_name / api_key from .env using a named profile (e.g. xiaomi, bailian).",
    )
    parser.add_argument("--model-name", default=None, help="Model name. Overrides profile.")
    parser.add_argument("--base-url", default=None, help="Base URL. Overrides profile.")
    parser.add_argument("--api-key", default=None, help="API key. Overrides profile.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature.")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Max tokens per generation.")
    parser.add_argument("--max-steps", type=int, default=10, help="Max agent steps per task.")
    parser.add_argument("--max-format-retries", type=int, default=3, help="Max retries on format errors.")
    parser.add_argument("--task", action="append", dest="tasks", help="Task id to run (can repeat). Omit to run all.")
    args = parser.parse_args()

    # Resolve from profile if not given on CLI
    if args.profile:
        spec = _PROFILES[args.profile]
        if args.base_url is None:
            args.base_url = os.environ.get(spec["base_url_env"], "")
        if args.model_name is None:
            args.model_name = os.environ.get(spec["model_name_env"], "")
        if args.api_key is None:
            args.api_key = os.environ.get(spec["api_key_env"], "EMPTY")
        if args.model_type is None:
            args.model_type = "openai_compatible"

    # Validate required args
    if args.model_type is None:
        parser.error("--model-type is required (or use --profile)")
    if not args.model_name:
        parser.error("--model-name is required (or set it in .env via --profile)")
    if args.model_type in ("openai_compatible", "local") and not args.base_url:
        args.base_url = "http://localhost:8000/v1"

    traces, _summary = run_real_baseline(args)
    successes = sum(1 for t in traces if t.success)
    print(f"\nDone: {successes}/{len(traces)} tasks succeeded.")
    return 0 if successes == len(traces) else 1


if __name__ == "__main__":
    raise SystemExit(main())
