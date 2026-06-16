# Phase 7.3: Independent50 Failure Decomposition

> Date: 2026-06-16
> Eval set: Independent50 (bugfix_351-400, 50 unseen tasks)
> Model: 3B v2.1-clean + Repair v3

---

## 1. Sub-Type Distribution (30 failures)

| Sub-type | Count | % | Definition |
|---|---|---|---|
| NO_EDIT | 14 | 47% | Model won't produce an edit |
| PATCH_WRONG_LOGIC | 9 | 30% | Edit applied but logic incorrect |
| TOO_COMPLEX_FOR_MODEL | 4 | 13% | Task exceeds model capability |
| INSUFFICIENT_IMPLEMENTATION | 3 | 10% | Required functionality not implemented |
| **Total** | **30** | 100% | |

---

## 2. Repair Effectiveness by Sub-Type

| Sub-type | Failures | Repaired | Rate |
|---|---|---|---|
| PATCH_WRONG_LOGIC | 9 | 2 | 22% |
| NO_EDIT | 14 | 0 | 0% |
| TOO_COMPLEX_FOR_MODEL | 4 | 0 | 0% |
| INSUFFICIENT_IMPLEMENTATION | 3 | 0 | 0% |

**Only PATCH_WRONG_LOGIC is repairable.** The other categories are immune to current repair pipeline.

---

## 3. Key Insight: Where Repair Works and Where It Doesn't

### Repair works (9 tasks, 2 repaired):
PATCH_WRONG_LOGIC — the model understands the task, makes an edit, but the logic has a gap. Repair can sometimes close this gap by providing expected vs actual output.

### Repair doesn't work (21 tasks, 0 repaired):
- **NO_EDIT (14):** The model reads the code but won't edit. Root cause: poor task comprehension, insufficient planning, or inability to locate the bug. Repair prompt cannot motivate what the model doesn't understand.
- **TOO_COMPLEX (4):** LRU cache semantics, BST operations, state machine history. Requires deep data structure understanding beyond the model's capability.
- **INSUFFICIENT_IMPL (3):** Functions like `from_roman`, `redo`, `eval_safe` need full implementation, not a patch.

---

## 4. Failure Root Cause Summary

| Root Cause | Tasks | Implication |
|---|---|---|
| **Model won't act** | 14 (47%) | Needs: Planner Agent (task decomposition) |
| **Model acts wrong** | 9 (30%) | Needs: Reviewer Agent (patch quality check) |
| **Task too hard** | 7 (23%) | Needs: Stronger base model (7B) |

---

## 5. Comparison: New100 vs Independent50

| Metric | New100 | Independent50 |
|---|---|---|
| First-pass | 66% | 40% |
| NO_EDIT rate | 11/34 (32%) | 14/30 (47%) |
| PATCH_WRONG_LOGIC rate | 13/34 (38%) | 9/30 (30%) |
| Repair success | 10/34 (29%) | 2/30 (7%) |
| Repairable (PATCH_WRONG_LOGIC) repaired | 5/13 (38%) | 2/9 (22%) |

Independent50 has **more NO_EDIT** (47% vs 32%) and **fewer repairable tasks**. The model struggles more with harder tasks because it can't even start editing.

---

## 6. Conclusions

1. **47% of failures are NO_EDIT** — the model won't act. This is the #1 bottleneck.
2. **Repair only works on PATCH_WRONG_LOGIC** (22% success rate on this set).
3. **For harder tasks, repair is not the answer** — stronger planning or a stronger model is needed.
4. **Planner Agent** could address the 14 NO_EDIT failures by helping the model locate and plan edits.
5. **7B model** could address the 7 TOO_COMPLEX/INSUFFICIENT failures.

---

## 7. Recommended Next Steps

### Phase 7.4: Cross-Model Repair Transfer
Test whether a stronger model (7B) has:
- Higher first-pass (fewer NO_EDIT)
- Better repair gain (more PATCH_WRONG_LOGIC to work with)

### Phase 8.1: Planner Agent
For the 14 NO_EDIT failures, a Planner Agent could:
- Read the issue and test output
- Identify the specific file and function to edit
- Generate a step-by-step fix plan
- Pass the plan to the Coder Agent

### Phase 8.2: Reviewer Agent
For the 9 PATCH_WRONG_LOGIC failures, a Reviewer Agent could:
- Evaluate the patch against test output
- Identify logic gaps before repair
- Suggest specific corrections
