# Phase 7: Verifier-Guided Repair — Final Report

> Date: 2026-06-16
> Model: Qwen2.5-Coder-3B-Instruct + v2.1-clean LoRA (QLoRA 4-bit)
> Benchmark: New100 (bugfix_251-350) + Independent50 (bugfix_351-400)

---

## 1. Core Conclusion

**Repair is a local correction mechanism, not a substitute for base coding capability.**

Verifier-Guided Repair brings significant gains on same-distribution tasks and positive (but limited) gains on harder unseen tasks. The repair pipeline works — but its effectiveness is bounded by the base model's first-pass ability to locate, understand, and partially fix the bug.

---

## 2. Results Summary

### 2.1 New100 (same-distribution, 100 tasks)

| Method | First-pass | Repair Gain | Final |
|---|---|---|---|
| Single-pass (baseline) | 65% | — | 65% |
| + Repair v1 (generic prompt) | 65% | +4 | 69% |
| + Repair v2 (failure-type-specific) | 66% | +8 | 74% |
| + Repair v3 (OTHER decomposition) | 66% | +10 | **76%** |

On New100, the full repair pipeline adds **+11 percentage points** without changing model parameters.

### 2.2 Independent50 (harder unseen tasks, 50 tasks)

| Method | First-pass | Repair Gain | Final |
|---|---|---|---|
| Single-pass | 40% | — | 40% |
| + Repair v3 (same prompts) | 40% | +4 | **44%** |

On Independent50, repair adds **+4 percentage points** — positive but significantly less than New100.

### 2.3 Key Comparison

| Metric | New100 | Independent50 |
|---|---|---|
| First-pass | 66% | 40% |
| Repair gain | +10 | +2 |
| Final | 76% | 44% |
| Repair success rate | 10/34 (29%) | 2/30 (7%) |

The 26-point drop in first-pass (66% → 40%) indicates Independent50 is substantially harder. Repair still works on harder tasks, but the gain shrinks because fewer failures are "close to correct."

---

## 3. What Repair Can and Cannot Fix

### Repair works when:
- The model correctly identifies the bug location
- The initial edit is close but has a logic gap (PATCH_WRONG_LOGIC)
- The model made no edit but understands the issue (NO_EDIT)
- A specific edge case or boundary is missing

### Repair struggles when:
- The model cannot locate the bug at all
- The task requires understanding the model fundamentally lacks
- The initial patch quality is very poor
- The fix requires rewriting significant logic (not a local edit)

**In other words:** Repair is effective for "almost correct" failures. For "fundamentally wrong" failures, stronger planning or coding capability is needed.

---

## 4. Failure Decomposition on Independent50

### 4.1 First-pass failure distribution (30/50 failures)

| Type | Count | % |
|---|---|---|
| OTHER | 23 | 77% |
| TEST_STILL_FAIL | 4 | 13% |
| NO_EDIT | 3 | 10% |

Compared to New100: OTHER is similarly dominant (77% vs 59%), but the absolute number is higher relative to task count.

### 4.2 Repair outcome on Independent50

| Transition | Count |
|---|---|
| FIRST_PASS_OK | 20 |
| OTHER -> OTHER | 10 |
| OTHER -> NO_EDIT -> OTHER | 4 |
| OTHER -> NO_EDIT -> NO_EDIT | 3 |
| OTHER -> NO_EDIT -> NO_TEST_AFTER_EDIT | 1 |
| OTHER -> REPAIR_OK | 0 |
| OTHER -> NO_EDIT -> REPAIR_OK (forced) | 1 |
| TEST_STILL_FAIL -> TEST_STILL_FAIL | 2 |
| TEST_STILL_FAIL -> REPAIR_OK | 1 |
| NO_EDIT -> REPAIR_OK | 0 |

**Key observation:** On Independent50, no OTHER failure was directly repaired. The only repair successes came from TEST_STILL_FAIL (1) and forced-edit (1). This suggests the OTHER prompt v3 is partially overfit to New100 task patterns.

---

## 5. Engineering Conclusions

1. **Failure-type-specific prompts work on same-distribution tasks**: v2 doubled repair success (11% → 24%)
2. **OTHER decomposition helps but has limits**: v3 added +2% over v2 on New100, but 0% direct OTHER repair on Independent50
3. **Forced-edit is a weak but real mechanism**: 2/6 on New100, 1/8 on Independent50
4. **Repair effectiveness scales with first-pass quality**: When first-pass is 66%, repair adds +10%; when first-pass is 40%, repair adds +4%
5. **The boundary has been mapped**: Repair is a local correction mechanism. Beyond this boundary, stronger models or multi-agent planning is needed.

---

## 6. Recommendations

### Phase 7.3: Independent50 Failure Decomposition
- Classify the 30 first-pass failures into fine-grained sub-types
- Focus on distinguishing "repairable" vs "needs stronger model" failures
- This tells us where the repair boundary actually is

### Phase 7.4: Cross-Model Repair Transfer
- Test Repair v3 pipeline (no prompt changes) on:
  - 7B Base/Instruct
  - 3B DPO best
- Answer: does repair gain scale with model capability?
- If 7B also gets +4-6% from repair, it's a general framework contribution

### Phase 8: Multi-Agent Planning
- Independent50 first-pass 40% suggests the model lacks planning ability
- Introduce Planner (task decomposition) + Reviewer (patch quality check)
- This addresses the root cause: poor first-pass quality on hard tasks

---

## 7. Final Framing

> In New100, Verifier-Guided Repair raises success from 65/66% to 76%, demonstrating that failure attribution and targeted repair prompts significantly enhance same-distribution performance.
>
> On the harder Independent50, first-pass drops to 40% and repair lifts it to 44%. This confirms the pipeline generalizes positively, but its gain is bounded by base model coding comprehension and initial patch quality.
>
> The next phase shifts from prompt-level repair to multi-agent planning and cross-model transfer, to improve first-pass capability on difficult tasks.

**This is not a failure. The boundary has been measured.**
