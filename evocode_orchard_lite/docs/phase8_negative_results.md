# Phase 8: System-Level Augmentation Negative Results

> Date: 2026-06-16
> Model: Qwen2.5-Coder-3B-Instruct + v2.1-clean LoRA
> Benchmark: Independent50 (bugfix_351-400, 50 harder unseen tasks)

---

## 1. Executive Summary

Phase 8 tests whether external system components (Planner, Auto-Read) can improve the 3B model's performance on harder tasks. Both interventions failed or degraded performance, establishing that **the bottleneck on Independent50 is base model coding capability, not lack of context or planning.**

---

## 2. Four-Group Experiment Results

| Group | Method | First-pass | Repair Gain | Final | NO_EDIT |
|---|---|---|---|---|---|
| A | 3B baseline (no assist) | 40% | — | 40% | — |
| B | 3B + Repair v3 | 40% | +4 | **44%** | 14 |
| C | Planner-prompt + 3B + Repair | 34% | +8 | 44% | 10 |
| D | Auto-Read + 3B + Repair | **26%** | +4 | **34%** | 8 |

---

## 3. Phase 8.1: Planner-Prompt (Negative Result)

### What was tested
A Rule Planner extracts function names, test file paths, and suspected source files from the issue text, then generates a structured JSON plan injected into the coder prompt.

### Results
- First-pass dropped from 40% to 34% (-6%)
- NO_EDIT dropped from 14 to 10 (-4) — the model was more willing to edit
- OTHER surged from 7 to 20 (+13) — but edits were low quality
- Final success unchanged at 44%

### Diagnosis
The Planner solved the "willingness to edit" problem but created a "quality of edit" problem. The 3B model, when given a longer prompt with a plan, produces more edits but worse ones. The plan text competes for attention with the actual task, degrading reasoning quality.

### Conclusion
**Planner reduces NO_EDIT but increases OTHER. Net effect: zero.**

---

## 4. Phase 8.2: Auto-Read Context Preparation (Negative Result)

### What was tested
The system automatically reads the suspected source file and test file, then injects the actual code into the prompt before the coder starts. No natural language plan — just raw code context.

### Results
- First-pass dropped from 40% to 26% (-14%)
- NO_EDIT dropped from 14 to 8 (-6) — even more willing to edit
- OTHER surged from 7 to 23 (+16) — edits became much worse
- Final success dropped from 44% to 34% (-10%)

### Diagnosis
Injecting code context made the prompt significantly longer. The 3B model's attention was overwhelmed by the additional context, producing worse edits. The model already has the ability to read files via the `read_file` tool — pre-loading context into the prompt was redundant and harmful.

### Conclusion
**Auto-Read reduces NO_EDIT but severely degrades overall performance. Harmful for 3B.**

---

## 5. Pattern Analysis

| Intervention | NO_EDIT | OTHER | Net Effect |
|---|---|---|---|
| Baseline | 14 | 7 | — |
| Planner | -4 | +13 | Neutral |
| Auto-Read | -6 | +16 | Negative |

**The more context we give the 3B model, the worse it performs.**

This is a clear capability boundary: the 3B model on Independent50 is operating at the edge of its reasoning capacity. Additional information is noise, not signal.

---

## 6. Key Engineering Conclusions

1. **Repair v3 is a genuine system-level improvement**: +4% on Independent50 without changing model parameters
2. **Planner and Auto-Read are negative results for 3B**: More context hurts rather than helps
3. **The bottleneck is model capability, not system design**: The 3B model cannot handle harder tasks regardless of how much context is provided
4. **Prompt length matters for small models**: Longer prompts degrade 3B performance
5. **System components should be model-adaptive**: What works for 7B may not work for 3B and vice versa

---

## 7. What This Means for the Project

The Phase 7 repair pipeline (66% → 76% on New100) is a real contribution. But its effectiveness is bounded by the base model's first-pass capability.

The path forward is not more system complexity, but:
1. **Stronger base model** (7B) to improve first-pass
2. **Model routing** (simple tasks → 3B, hard tasks → 7B)
3. **Failure memory** to learn from hard failures over time

---

## 8. Negative Results Value

These negative results are as valuable as the positive ones because they:

1. **Define the boundary** of what system-level optimization can achieve with a 3B model
2. **Prevent wasted effort** on Planner/Auto-Read improvements that won't help
3. **Redirect focus** to the actual bottleneck (model capability)
4. **Demonstrate rigorous methodology** — not just reporting successes

---

## 9. Next Steps

### Phase 8.3: Cross-Model Transfer
Test the same Repair v3 pipeline (no Planner, no Auto-Read) with:
- 7B Instruct (base, no adapter)
- 7B + best adapter

Goal: verify whether repair gains scale with model capability.

### Phase 8.4: Model Router
Based on Phase 8.3 results:
- If 7B first-pass >> 3B first-pass → implement difficulty-based routing
- If 7B repair gain > 0 → repair is a general framework contribution
- If both → Hybrid system: 3B for simple, 7B for hard, Repair for both
