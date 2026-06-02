# EvoCode-Orchard-Lite

This directory is the new lightweight project skeleton for an Orchard-inspired coding-agent post-training loop.

Current first milestone:

- `env_lite/`: local task workspace reset and command execution
- `tools/`: structured coding tools
- `harness/`: JSON action parsing and minimal agent loop
- `trajectory/`: structured trace saving
- `eval/`: pytest-based reward
- `benchmark/tasks/bugfix_001`: first toy code-repair task

Architecture note:

- [Layer 1 Architecture](docs/layer1_architecture.md)
- [Roadmap for Next Agent](docs/roadmap_for_next_agent.md)
- [Data Cleaning and Expansion Guide](docs/data_cleaning_and_expansion_guide.md)
- [Data Generation Protocol](docs/data_generation_protocol.md)

Run the smoke test from the repository root:

```bash
python -m evocode_orchard_lite.run_smoke
```

Run the current scripted baseline over all toy tasks:

```bash
python -m evocode_orchard_lite.run_eval
```

Validate that every toy task fails before the scripted fix and passes after it:

```bash
python -m evocode_orchard_lite.benchmark.validate_tasks
```

Build the first SFT dataset from successful traces:

```bash
python -m evocode_orchard_lite.data_builder.build_sft
```
