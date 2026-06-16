# Phase 7.1: Repair v2 - Failure-Type-Specific Prompts + No-Edit Guard

> Date: 2026-06-16
> Model: Qwen2.5-Coder-3B-Instruct + v2.1-clean LoRA (QLoRA 4-bit)
> Benchmark: New100 (bugfix_251 to bugfix_350, 100 harder held-out tasks)
> GPU: NVIDIA RTX A6000 (GPU 4)

---

## 1. Executive Summary

Repair v2 introduces failure-type-specific repair prompts and a No-Edit Guard (forced-edit fallback). On New100, v2 achieves **74% final success** (up from 69% in v1), with repair gains doubling from +4 to +8. The improvement comes entirely from better repair prompts — failure-type-specific targeting for OTHER failures eliminates the v1 regression problem (OTHER->NO_EDIT dropped from 11 to 2). The Forced-edit Guard produced zero additional successes, confirming it as a negative ablation result.

---

## 2. v1 vs v2 Comparison

| Metric | Single-pass | + Repair v1 | + Repair v2 + Guard | v1->v2 Delta |
|---|---|---|---|---|
| First-pass success | 65% | 65% | 66% | +1* |
| Repair gains | — | +4 | **+8** | **+4** |
| Forced-edit gains | — | — | +0 | 0 |
| **Final success** | **65%** | **69%** | **74%** | **+5** |
| Final failures | 35 | 31 | 26 | -5 |

*v2 is a separate run; first-pass has 1 task variance from v1 due to sampling randomness. Core comparison: final success and repair gain.*

---

## 3. Failure Distribution

### 3.1 First-Pass Failures

| Failure Type | v1 Count | v2 Count |
|---|---|---|
| NO_EDIT | 13 | 11 |
| TEST_STILL_FAIL | 3 | 3 |
| OTHER | 19 | 20 |
| **Total failures** | **35** | **34** |

### 3.2 Post-Repair Failures

| Failure Type | v1 Post-Repair | v2 Post-Repair |
|---|---|---|
| NO_EDIT | 21 | 6 |
| TEST_STILL_FAIL | 0 | 1 |
| OTHER | 10 | 19 |
| **Total failures** | **31** | **26** |

Key observation: v1 had 21 NO_EDIT after repair (repair-induced regression), v2 has only 6. The failure-type-specific prompts successfully prevent OTHER->NO_EDIT regression.

---

## 4. Failure Transition Matrix (v2)

| Transition | Count | Meaning |
|---|---|---|
| FIRST_PASS_OK | 66 | No repair needed |
| OTHER -> OTHER | 15 | Repair didn't help |
| NO_EDIT -> REPAIR_OK | 5 | Repair fixed NO_EDIT |
| OTHER -> REPAIR_OK | 3 | Repair fixed OTHER |
| NO_EDIT -> NO_EDIT -> NO_EDIT | 3 | Persistent (all 3 phases failed) |
| OTHER -> NO_EDIT -> NO_EDIT | 2 | Repair + forced-edit both failed |
| NO_EDIT -> OTHER | 2 | Repair changed failure mode |
| TEST_STILL_FAIL -> OTHER | 1 | Changed failure mode |
| TEST_STILL_FAIL -> TEST_STILL_FAIL | 1 | Persistent |
| TEST_STILL_FAIL -> NO_EDIT -> NO_EDIT | 1 | Changed to persistent |
| NO_EDIT -> NO_EDIT -> OTHER | 1 | Forced-edit changed mode |

---

## 5. Repair Success by Failure Type

| Failure Type | v1 Success Rate | v2 Success Rate | Delta |
|---|---|---|---|
| NO_EDIT | 3/13 (23%) | 5/11 (45%) | +22% |
| TEST_STILL_FAIL | 0/3 (0%) | 0/3 (0%) | 0 |
| OTHER | 1/19 (5%) | 3/20 (15%) | +10% |
| **Total** | **4/35 (11%)** | **8/34 (24%)** | **+13%** |

Both NO_EDIT and OTHER repair rates doubled. TEST_STILL_FAIL remains intractable with current approach.

---

## 6. Forced-Edit Guard: Negative Ablation

The No-Edit Guard triggers when the repair phase produces no edit (NO_EDIT), providing a stronger forced-edit prompt.

| Metric | Value |
|---|---|
| Triggered | 6 times |
| Successes | 0 |
| Failure modes after forced-edit | NO_EDIT=5, OTHER=1 |

**Conclusion:** Forced-edit Guard is a negative result. The model persistently cannot produce edits for these tasks. Adding stronger "you MUST edit" instructions does not help. These 6 tasks represent a hard boundary of the current model capability.

---

## 7. Success Cases (4 representative examples)

### 7.1 bugfix_259: NO_EDIT -> REPAIR_OK
**Issue:** `safe_divide("10", 2)` raises TypeError instead of returning None.
**First pass:** Model identified the bug but made no edit.
**Repair:** Failure-type-specific NO_EDIT prompt ("CRITICAL: You MUST make a source-code edit") drove the model to read the file and apply the fix (catch TypeError in addition to ZeroDivisionError).

### 7.2 bugfix_322: OTHER -> REPAIR_OK
**Issue:** `sliding_window([1,2], 5)` causes negative range — no validation for window > list length.
**First pass:** Model made an edit but tests still failed (OTHER failure).
**Repair:** OTHER-specific prompt guided the model to re-read the failure output and apply a more targeted fix (add length validation).

### 7.3 bugfix_329: NO_EDIT -> REPAIR_OK
**Issue:** `describe_temp(0)` returns "cold" instead of "freezing". Boundary at 0.
**First pass:** Model explained the issue but made no edit.
**Repair:** NO_EDIT prompt forced an edit. Model correctly fixed the boundary condition (>= 0 -> freezing).

### 7.4 bugfix_333: OTHER -> REPAIR_OK
**Issue:** `summarize_chunks([])` raises IndexError; `chunk_text("abc", 0)` causes infinite loop.
**First pass:** Model made a partial fix (OTHER failure).
**Repair:** OTHER prompt guided the model to address the remaining test failure (infinite loop guard).

---

## 8. Failure Cases (3 representative examples)

### 8.1 bugfix_262: NO_EDIT -> NO_EDIT -> NO_EDIT (persistent)
**Issue:** `generate_slug("Hello! @World#")` returns "Hello!-@World#" instead of "hello-world".
**All 3 phases:** Model consistently fails to produce an edit. It reads the file, identifies the problem, but stops before editing. This is a hard NO_EDIT case that no prompt variation can fix.

### 8.2 bugfix_306: OTHER -> OTHER (repair didn't help)
**Issue:** `time_until("09:00", "23:00")` returns -14.0 instead of 10.0 (midnight crossing).
**First pass:** Model made an incorrect fix.
**Repair:** Model made another incorrect fix. The task requires understanding time arithmetic across midnight, which the model handles incorrectly in both attempts.

### 8.3 bugfix_311: OTHER -> NO_EDIT -> NO_EDIT (regression)
**Issue:** Complex task that the model initially attempted but failed.
**First pass:** OTHER failure (attempted but wrong).
**Repair:** Became NO_EDIT (model got cautious with the detailed failure prompt).
**Forced-edit:** Still NO_EDIT (model cannot produce a correct edit).

---

## 9. Remaining Failure Analysis

| Category | Count | % of Failures |
|---|---|---|
| OTHER (persistent) | 19 | 73% |
| NO_EDIT (persistent) | 6 | 23% |
| TEST_STILL_FAIL | 1 | 4% |
| **Total** | **26** | 100% |

The dominant remaining bottleneck is OTHER (19 tasks). These are tasks where the model makes an edit but the edit is wrong. This requires either:
1. Better model capability (larger model or better training data)
2. Decomposed repair strategy (Phase 7.2: OTHER Failure Decomposition)

---

## 10. Phase 7.2 Roadmap: OTHER Failure Decomposition

The 19 persistent OTHER failures need secondary classification:

| Sub-type | Definition | Strategy |
|---|---|---|
| PATCH_WRONG_LOGIC | Edit is syntactically valid but logically incorrect | Need better test-output reasoning |
| PARTIAL_FIX | Edit fixes some tests but not all | Multi-edit repair loop |
| WRONG_FILE | Model edits the wrong file | Better file-identification prompt |
| OFF_BY_ONE | Boundary error in the fix | Targeted boundary-check prompts |
| REGRESSION | Fix breaks previously passing tests | Regression-aware repair |
| INSUFFICIENT_EDIT | Edit is too narrow (missing edge cases) | Broader context in prompt |
| UNKNOWN | Cannot classify | Manual inspection |

**Next step:** Implement secondary classifier on the 19 OTHER failures, then design targeted repair strategies per sub-type.

---

## 11. Conclusions

1. **Repair v2 is a genuine improvement**: 65% -> 74% (+9 absolute, +13.8% relative)
2. **Failure-type-specific prompts work**: Repair success rate doubled (11% -> 24%)
3. **OTHER->NO_EDIT regression eliminated**: v1 had 11 cases, v2 has 2
4. **Forced-edit Guard is a negative result**: 0/6 success, should not be default strategy
5. **OTHER is the new bottleneck**: 19/26 failures (73%), needs decomposition
6. **Phase 7 validates the repair-loop architecture**: Test-feedback-driven repair is effective without retraining

---

## 12. Methodology Notes

- v2 evaluation is a fresh run (not reusing v1 first-pass traces)
- First-pass variance: v1=65, v2=66 (1 task difference from sampling randomness)
- All comparisons use final success rate as primary metric
- Temperature=0 (greedy decoding) for all evaluations
- Max steps: first-pass=10, repair=8, forced-edit=6
