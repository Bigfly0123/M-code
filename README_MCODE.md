# EvoCode-Orchard-Lite (M-code)

> Coding Agent Post-Training Framework: from SFT to Test-Feedback-Driven Repair

An Orchard-inspired framework for training and evaluating coding agents on bug-fixing tasks. Built on mini-swe-agent architecture with custom tool protocol, step-level SFT, DPO, and verifier-guided repair.

---

## Current Results

| Phase | Method | New50 | New100 | Notes |
|---|---|---|---|---|
| Baseline | 3B Base | 52% | 38% | No training |
| Phase 2 | Step-SFT v2 | 90% | 58% | Step-level prompt-completion SFT |
| Phase 3 | Read-to-Edit SFT | 94% | 62% | NO_EDIT problem partially solved |
| Phase 4 | Step-SFT v2.1-clean | **98%** | 66% | Clean data pipeline + EOS fix |
| Phase 6 | DPO (patch-correctness) | — | 68% | Diminishing returns |
| Phase 7 | + Repair v1 | — | 69% | +4% from repair loop |
| **Phase 7.1** | **+ Repair v2 + Guard** | — | **74%** | **+5% from failure-type-specific prompts** |

**Best result: 74% on New100 (100 harder held-out tasks)**

---

## Key Innovations

1. **Step-level SFT** (not trajectory-level): Training on individual action steps rather than full trajectories
2. **Read-to-Edit transition**: Solving the NO_EDIT problem by training the model to transition from reading to editing
3. **Verifier-Guided Repair**: After first-pass failure, the model receives test failure feedback and attempts repair
4. **Failure-Type-Specific Repair**: Different repair prompts for NO_EDIT, TEST_STILL_FAIL, and OTHER failures

---

## Project Structure

```
evocode_orchard_lite/
  training/          # SFT and DPO training scripts
  eval/              # Evaluation scripts (single-pass, repair v1, repair v2)
  data_builder/      # Data pipeline for SFT and DPO
  tools/             # MCP-style tool protocol (read_file, edit_file, run_tests, etc.)
  harness/           # Agent loop and action parsing
  models/            # Model base class
  env_lite/          # Code repair environment
  docs/              # Phase reports and planning docs
benchmark/
  tasks/             # bugfix_001 to bugfix_400 (500+ tasks)
```

---

## Phase Reports

- [Phase 7 Report](evocode_orchard_lite/docs/phase7_verifier_guided_repair_report.md) - Repair v1 (69%)
- [Phase 7.1 Report](evocode_orchard_lite/docs/phase7_1_repair_v2_report.md) - Repair v2 (74%)

---

## Next: Phase 7.2 - OTHER Failure Decomposition

The 19 remaining OTHER failures (73% of all failures) need secondary classification:
- PATCH_WRONG_LOGIC, PARTIAL_FIX, WRONG_FILE, OFF_BY_ONE, REGRESSION, INSUFFICIENT_EDIT
- Targeted repair strategies per sub-type
