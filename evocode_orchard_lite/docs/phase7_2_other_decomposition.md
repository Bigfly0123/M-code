# Phase 7.2: OTHER Failure Decomposition

> Date: 2026-06-16
> Model: Qwen2.5-Coder-3B-Instruct + v2.1-clean LoRA
> Benchmark: New100 (19 OTHER failures from Repair v2)

---

## 1. Executive Summary

The 19 persistent OTHER failures decompose into 4 sub-types. The dominant category is **PATCH_WRONG_LOGIC (13/19 = 68%)** — the model makes an edit but the logic is incorrect. This is fundamentally different from NO_EDIT (model won't edit) and requires a repair strategy focused on **test-output reasoning** rather than edit motivation.

---

## 2. OTHER Secondary Classification

| Sub-type | Count | % | Definition |
|---|---|---|---|
| PATCH_WRONG_LOGIC | 13 | 68% | Edit applied but logic incorrect |
| PARTIAL_FIX | 3 | 16% | Some tests fixed, others still fail |
| INSUFFICIENT_IMPLEMENTATION | 2 | 11% | Required functionality not implemented |
| BOUNDARY_ERROR | 1 | 5% | Boundary condition not handled |
| **Total** | **19** | 100% | |

---

## 3. Detailed Classification

### 3.1 PATCH_WRONG_LOGIC (13 tasks)

The model edits the code, but the fix is logically incorrect. The model either:
- Misunderstands the requirement
- Applies an incomplete fix
- Handles the wrong case

| Task | Issue | Root Cause |
|---|---|---|
| bugfix_252 | `format_phone("123")` returns invalid format | No length validation on digits |
| bugfix_265 | `join_paths` returns "/home///user/" | No slash normalization |
| bugfix_271 | `is_hex_color("#abc")` returns False | Doesn't accept 3-digit hex |
| bugfix_272 | `is_valid_ipv4("256.1.1.1")` returns True | No range check (>255) |
| bugfix_301 | `is_strong_password("abc12345")` True | Missing uppercase check |
| bugfix_303 | `get_extension("FILE.PDF")` returns "PDF" | Missing .lower() |
| bugfix_304 | `extract_headers` picks up inline # | No start-of-line anchor |
| bugfix_306 | `time_until` returns -14.0 | Doesn't handle midnight crossing |
| bugfix_307 | `days_in_month(2, 2024)` = 28 | Doesn't handle leap year |
| bugfix_309 | `elapsed_str(3661)` = "61m 1s" | Doesn't handle hours |
| bugfix_337 | `find_pairs` includes same-index pairs | Inner loop starts at i not i+1 |
| bugfix_341 | `is_isbn("978-0131103627")` False | ISBN validation logic wrong |
| bugfix_345 | `sort_by_key` raises KeyError | No missing-key handling |

**Pattern:** The model understands the general task but misses a specific requirement or edge case. The fix is usually a small additional check or condition.

**Repair strategy:** Feed the model the specific failing test assertion and expected vs actual output. Emphasize "compare expected vs actual" and "what specific condition is missing?"

### 3.2 PARTIAL_FIX (3 tasks)

The model makes an edit that fixes some tests but not all. The model makes progress but doesn't address all failure modes.

| Task | Issue | What was fixed | What's still broken |
|---|---|---|---|
| bugfix_266 | parse_ini includes comments | Basic parsing | Comment line skipping |
| bugfix_297 | parse_csv doesn't handle quotes | Basic CSV splitting | Quoted field handling |
| bugfix_346 | get_row IndexError | (unknown) | Boundary check |

**Pattern:** The model fixes the main case but misses edge cases. The remaining failures are usually about special characters, boundary conditions, or alternative formats.

**Repair strategy:** List all failing tests explicitly. Tell the model "you fixed N of M tests, here are the remaining failures."

### 3.3 INSUFFICIENT_IMPLEMENTATION (2 tasks)

The model either doesn't implement the required function or implements a stub.

| Task | Issue | What happened |
|---|---|---|
| bugfix_334 | from_roman returns 0 | Function not implemented (stub) |
| bugfix_339 | retry returns None | Error handling not implemented |

**Pattern:** The model reads the code, sees a stub or missing implementation, but doesn't add the actual logic. This is similar to NO_EDIT but the model DID make some edit (just not the right one).

**Repair strategy:** Explicitly tell the model "this function is not implemented. You need to write the actual logic."

### 3.4 BOUNDARY_ERROR (1 task)

| Task | Issue |
|---|---|
| bugfix_346 | `get_row([[1,2]], 5)` raises IndexError |

**Pattern:** Out-of-bounds access not guarded.

---

## 4. Comparison with v1 OTHER Failures

In Repair v1, 19 OTHER failures occurred. In v2, 3 of those were recovered (OTHER->REPAIR_OK), leaving 16 OTHER->OTHER transitions plus 3 that came from other failure types.

The v2 failure-type-specific prompt for OTHER ("Re-read source, run tests, then make minimal edit") was effective at preventing the OTHER->NO_EDIT regression (11 in v1 vs 2 in v2), but did not improve the PATCH_WRONG_LOGIC sub-type significantly.

---

## 5. Repair Prompt v3 Design

Based on the decomposition, v3 prompts should be:

### For PATCH_WRONG_LOGIC (13 tasks):
```
Your previous fix was applied but is logically incorrect.

Task: {issue}
Test failure: {test_output}

The test expects: {expected_value}
Your code returns: {actual_value}

What specific condition or check is missing?
- Compare expected vs actual output carefully
- Identify the exact logic gap
- Apply a targeted fix to address ONLY the failing assertion
- Do NOT change code that already works
```

### For PARTIAL_FIX (3 tasks):
```
Your fix resolved some tests but not all.

Task: {issue}
Passing tests: {pass_count}
Failing test: {failing_test_assertion}

Focus ONLY on the remaining failure.
- Read the failing test to understand what it expects
- Your current fix handles the basic case but misses this edge case
- Add the minimal additional logic needed
```

### For INSUFFICIENT_IMPLEMENTATION (2 tasks):
```
The function is not implemented or is a stub.

Task: {issue}
Current code: {current_code_snippet}

You need to implement the actual logic.
- Read the test file to understand all expected behaviors
- Write the complete implementation
- Do NOT just add a comment or pass statement
```

---

## 6. Success Criteria

| Metric | Current (v2) | Target (v3) |
|---|---|---|
| OTHER failures | 19 | <=12 |
| Final success | 74% | >=77% |
| PATCH_WRONG_LOGIC | 13 | <=8 |
| PARTIAL_FIX | 3 | <=2 |
| INSUFFICIENT_IMPLEMENTATION | 2 | <=1 |

---

## 7. Implementation Plan

1. Build a classifier that identifies the OTHER sub-type from trace data
2. Implement v3 repair prompts per sub-type
3. Run Repair v3 eval on New100
4. Compare v2 vs v3 results
5. Write Phase 7.2 report
