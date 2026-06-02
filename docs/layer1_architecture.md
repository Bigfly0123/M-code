# Layer 1 Architecture: Env-lite, Trace, Eval, Data

Layer 1 is the minimum reliable foundation for EvoCode-Orchard-Lite.

It is intentionally lightweight. The goal is not to make a large agent framework yet, but to make the core loop reproducible:

```text
toy code-repair task
-> reset isolated workspace
-> execute structured tool actions
-> modify code and run tests
-> save trajectory
-> compute metrics and reward
-> convert successful traces to SFT data
```

## Scope

Layer 1 includes:

- `benchmark/tasks/`: toy code-repair benchmark
- `env_lite/`: local task workspace reset and command execution
- `tools/`: structured tools for file inspection, editing, testing, diff, and submit
- `harness/`: JSON action parsing and a minimal agent loop
- `trajectory/`: structured trace saving
- `eval/`: reward, metrics, reports, and benchmark validation
- `data_builder/`: trace-to-SFT conversion

Layer 1 does not include:

- real LLM inference
- LoRA / QLoRA training
- DPO or GRPO
- skill memory
- Docker isolation
- SWE-bench scale tasks

Those belong to later layers.

## Why Keep This Layer Small?

The post-training pipeline depends on clean trajectories. If the task reset, tool execution, reward, or trace schema is unstable, training data will be noisy and later SFT/DPO/RL work will be hard to debug.

Layer 1 therefore prioritizes:

- deterministic task validation
- clear JSON action format
- trace reproducibility
- basic safety boundary for workspace file paths
- measurable eval outputs
- data conversion that can be rerun

## Current Task Format

Each task lives under:

```text
benchmark/tasks/bugfix_xxx/
├── repo/
├── issue.md
└── metadata.json
```

`metadata.json` contains:

- `task_id`
- `bug_type`
- `test_command`
- `target_files`
- `difficulty`
- `scripted_fix`

The `scripted_fix` field is a temporary Layer 1 mechanism. It provides a deterministic repair path so the benchmark, trace, eval, and SFT conversion can be verified before introducing real LLM failures.

## Trace Schema

Each run saves a trace with:

- task id
- model name
- success flag
- reward
- step list
- final patch
- test result
- metrics
- failure type

Each step records:

- thought
- action name and arguments
- observation
- tool success

This is the source of later SFT, Credit-SFT, DPO, and GRPO data.

## Metrics

The current eval layer reports:

- task success rate
- test pass rate
- tool valid rate
- patch apply rate
- format error rate
- run-test-before-submit rate
- unrelated edit rate
- average steps
- failure counts

These are deliberately broader than just final success rate, because SFT may first improve behavior quality before improving task success.

## Layer 1 Commands

Validate benchmark tasks:

```bash
python -m evocode_orchard_lite.benchmark.validate_tasks
```

Run scripted baseline:

```bash
python -m evocode_orchard_lite.run_eval
```

Build SFT data:

```bash
python -m evocode_orchard_lite.data_builder.build_sft
```

## Next Layer

Layer 2 should replace `ScriptedModel` with a real LLM wrapper while keeping the same JSON action interface.

Expected new work:

- real model adapter
- format error retry
- failed trace collection
- failure taxonomy
- baseline report from real model behavior
- SFT data from a mix of scripted traces, successful LLM traces, and manually corrected traces
