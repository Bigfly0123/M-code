# Phase 7: Skill Self-Distillation Plan

> Status: Planning
> Prerequisite: Phase 6 DPO experiments completed, diminishing returns confirmed

---

## 1. Why Skill Self-Distillation

Phase 6 DPO proved that preference optimization has limited gains for patch correctness at current data scale. The bottleneck is not format/tool/NO_EDIT, but harder bugs requiring stronger code reasoning.

Skill Self-Distillation takes a different approach: instead of training the model to prefer correct patches via DPO, extract reusable debugging strategies from success trajectories and inject them as structured knowledge.

This is more suitable for:
- Project demonstration (shows engineering depth)
- Interview discussion (explains agent capabilities)
- Incremental improvement (skills can be tested independently)
- Foundation for future GRPO (skills as structured priors)

---

## 2. What Skills to Extract

### Priority 1: Bug-type specific skills

| Skill | Source | Example |
|---|---|---|
| regex_parsing | regex bug successes | "When regex validation fails, check for missing anchors (^$), wrong quantifiers, and unescaped special chars" |
| type_conversion | type_conversion successes | "When type errors occur, check implicit conversions, str/int/float casting, and None handling" |
| none_handling | none_handling successes | "Add explicit None checks before attribute access or arithmetic operations" |
| off_by_one | off_by_one successes | "Check loop bounds: range(n) vs range(n+1), < vs <=, 0-indexed vs 1-indexed" |

### Priority 2: Process skills

| Skill | Source | Example |
|---|---|---|
| test_feedback_correction | multi-step success traces | "After edit, run tests. If fail, read test output, identify the assertion, revise patch" |
| patch_apply_stability | edit_file success traces | "Use exact old_text from file, preserve indentation, minimal change" |
| minimal_edit | success vs over-edit comparison | "Change only the buggy line, don't refactor unrelated code" |
| run_tests_first | test-first success traces | "Always run tests before editing to understand current behavior" |

### Priority 3: Localization skills

| Skill | Source | Example |
|---|---|---|
| multi_file_localization | multi-file success traces | "Read test file first to identify expected behavior, then locate target file" |
| error_message_reading | test output analysis | "Parse AssertionError message to find expected vs actual values" |

---

## 3. Skill Extraction Pipeline

### Step 1: Collect high-quality success traces

Source: mimo v2.5-pro rollouts on bugfix_001-350
Filter: patch_apply=true, tests_pass=true, steps<=8, no unrelated edits

### Step 2: Cluster by bug_type and action pattern

Group traces by:
- bug_type (regex, type_conversion, etc.)
- action pattern (test-first, edit-direct, multi-file)
- failure type that was avoided (vs model failures)

### Step 3: Extract skill templates

For each cluster, extract:
- When to apply (trigger condition)
- What to do (action sequence)
- What to avoid (anti-pattern)
- Example (short trace excerpt)

### Step 4: Store as structured skill library

```json
{
  "skill_id": "regex_parsing_v1",
  "bug_type": "regex",
  "trigger": "regex validation test failures",
  "strategy": "Check anchors, quantifiers, escaping, character classes",
  "anti_patterns": ["Using .* without anchors", "Forgetting to escape dots"],
  "example_task": "bugfix_214",
  "example_trace_excerpt": "..."
}
```

---

## 4. Skill Injection Methods

### Method A: Prompt-side injection (no training)

Inject retrieved skill into the prompt before agent runs:

```
You are a code repair agent.

Relevant skill for this task:
[regex_parsing skill]: When regex validation fails, check for missing
anchors (^$), wrong quantifiers, and unescaped special chars.

Task: Fix the bug...
```

This requires no training and can be tested immediately.

### Method B: SFT with skill-augmented prompts

Construct SFT data where prompt includes retrieved skill:

```
prompt: [task + retrieved skill + history]
completion: [correct action]
```

### Method C: Teacher-with-skill vs student-without-skill distillation

Teacher sees: task + skill + context -> generates high-quality trace
Student sees: task + context -> learns to generate same trace

This is the full OPSD-lite approach.

---

## 5. Execution Plan

### Step 1: Skill library construction (no training)

- Extract skills from mimo success traces
- Store as JSON skill library
- Test prompt-side injection on New100

### Step 2: Prompt-side evaluation

- Run v2.1-clean on New100 with skill injection
- Compare with v2.1-clean without skills
- If improvement: skills are valuable
- If no improvement: skills need better extraction or injection

### Step 3: Skill-augmented SFT (if Step 2 shows improvement)

- Construct skill-augmented SFT data
- Train from v2.1-clean
- Evaluate on New100 + clean independent eval

### Step 4: Skill Self-Distillation (if Step 3 shows improvement)

- Teacher with skill generates traces
- Student without skill learns from traces
- Full distillation loop

---

## 6. Success Criteria

### Step 1 success: skill library exists with 8+ skills

### Step 2 success: prompt-side injection improves New100 by >= 3%

### Step 3 success: skill-augmented SFT improves New100 by >= 5% over v2.1-clean

### Step 4 success: distilled student matches teacher-with-skill performance

---

## 7. What NOT to do

- Don't immediately train - test prompt-side injection first
- Don't extract too many skills - quality over quantity
- Don't make skills too long - concise trigger + strategy + example
- Don't conflate skills with DPO - different mechanism
- Don't skip evaluation - every skill injection must be measured
