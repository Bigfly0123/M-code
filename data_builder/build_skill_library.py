"""Build 5 core skills from mimo success traces and model failures."""
import json
from pathlib import Path

SKILLS = [
    {
        "skill_id": "patch_apply_stability",
        "trigger_keywords": ["edit_file", "old_text", "patch", "indentation", "replace"],
        "when_to_use": "When using edit_file to fix code. Applies to ALL bug types.",
        "success_pattern": "Successful edits use the SHORTEST possible old_text that uniquely identifies the replacement location. They preserve exact indentation and whitespace. They read the file first to see the current content.",
        "failure_pattern": "Failed edits use overlong old_text that includes surrounding context, mismatch indentation, or use paraphrased text instead of exact copy-paste from the file.",
        "action_checklist": [
            "Read the file first to see exact current content",
            "Use the MINIMUM old_text needed for unique match (1-3 lines)",
            "Copy old_text EXACTLY from file content, including indentation",
            "Keep new_text change minimal - only fix the bug",
            "After edit, run tests to verify",
        ],
        "edit_guidance": "old_text should be 1-3 lines, copied verbatim from file. new_text should change only the buggy part.",
        "test_guidance": "Always run tests after edit. If tests fail, re-read the file to check if edit applied correctly.",
        "example_task": "bugfix_319",
        "example_trace": "read_file(rgb_to_hex.py) -> edit_file(old='return f\"#{r}{g}{b}\"', new='return f\"#{r:02x}{g:02x}{b:02x}\"') -> run_tests -> submit_patch",
    },
    {
        "skill_id": "test_feedback_correction",
        "trigger_keywords": ["test failed", "assertion", "assert", "expected", "actual", "run_tests"],
        "when_to_use": "After edit_file, if run_tests shows failure. Need to read test output, understand the assertion, and revise the patch.",
        "success_pattern": "Successful correction: (1) edit -> (2) run_tests -> (3) READ the test output carefully -> (4) identify which assertion failed and what expected vs actual -> (5) revise edit to fix the specific assertion -> (6) run_tests again -> (7) submit.",
        "failure_pattern": "Failed correction: (1) edit -> (2) run_tests fail -> (3) repeat same edit without reading test output -> (4) submit anyway. Or: never re-read file after failed edit.",
        "action_checklist": [
            "After edit, ALWAYS run tests",
            "If tests fail, READ the test output (don't skip)",
            "Identify which assertion failed: expected vs actual",
            "Trace the assertion back to the buggy code",
            "Make a NEW edit (don't repeat the same one)",
            "Run tests again after revised edit",
        ],
        "edit_guidance": "When revising, re-read the file first (it may have changed after your edit). Use a different old_text that matches the current file state.",
        "test_guidance": "Parse AssertionError: look for 'assert X == Y' where X is actual, Y is expected. The difference tells you what to fix.",
        "example_task": "bugfix_306",
        "example_trace": "edit_file(fahrenheit_to_celsius) -> run_tests(FAIL: assert 36.999 == 37.0) -> edit_file(add round()) -> run_tests(PASS) -> submit",
    },
    {
        "skill_id": "regex_parsing",
        "trigger_keywords": ["regex", "re.match", "re.search", "pattern", "regular expression", "re.compile"],
        "when_to_use": "When the bug involves regex pattern matching - validation, extraction, or parsing with regular expressions.",
        "success_pattern": "Successful regex fixes: (1) read the failing test to understand what should match/reject, (2) identify the regex issue (missing anchors, wrong quantifiers, unescaped chars), (3) apply minimal fix to the pattern.",
        "failure_pattern": "Failed regex fixes: rewrite the entire regex instead of minimal fix, forget anchors (^$), use wrong quantifier (* vs +), don't escape special chars.",
        "action_checklist": [
            "Read test cases first to understand valid/invalid inputs",
            "Check for missing ^ and $ anchors",
            "Check quantifier: * (0+) vs + (1+) vs ? (0-1)",
            "Escape special chars: . * + ? [ ] ( ) { } | \\",
            "Use character classes: [a-z] [0-9] \\d \\w \\s",
            "Test the pattern mentally against test cases before editing",
        ],
        "edit_guidance": "Fix the regex pattern minimally. Don't rewrite the entire function unless necessary.",
        "test_guidance": "If regex test fails, check: does the pattern match what it should? Does it reject what it should? Test both positive and negative cases.",
        "example_task": "bugfix_214",
        "example_trace": "run_tests(FAIL: is_valid_time('25:30') returns True) -> read_file(time_validate.py) -> edit_file(pattern = r'\\d{2}:\\d{2}' -> pattern = r'^[0-2]\\d:[0-5]\\d$') -> run_tests(PASS) -> submit",
    },
    {
        "skill_id": "type_conversion",
        "trigger_keywords": ["int", "float", "str", "type", "TypeError", "ValueError", "conversion", "cast"],
        "when_to_use": "When the bug involves type conversion, implicit casting, or type errors (int/float/str mismatch).",
        "success_pattern": "Successful type fixes: (1) identify where type mismatch occurs, (2) add explicit conversion or guard, (3) handle edge cases (None, empty string, non-numeric).",
        "failure_pattern": "Failed type fixes: assume input is always the expected type, don't handle None/empty/invalid input, add conversion in wrong place.",
        "action_checklist": [
            "Read tests to see what input types are used",
            "Check for implicit type assumptions in the code",
            "Add explicit type conversion where needed",
            "Handle None, empty string, and invalid input",
            "Use try/except for type-sensitive operations",
        ],
        "edit_guidance": "Add type guards or conversions at function entry. Use isinstance() for type checking.",
        "test_guidance": "If TypeError occurs, trace which variable has wrong type. If ValueError, check input parsing.",
        "example_task": "bugfix_319",
        "example_trace": "run_tests(FAIL: rgb_to_hex(255,128,0) returns wrong format) -> read_file -> edit_file(f-string with :02x format) -> run_tests(PASS) -> submit",
    },
    {
        "skill_id": "date_time",
        "trigger_keywords": ["date", "time", "datetime", "timedelta", "strftime", "strptime", "calendar"],
        "when_to_use": "When the bug involves date/time parsing, comparison, formatting, or calendar calculations.",
        "success_pattern": "Successful date fixes: (1) identify the date logic error, (2) handle edge cases (leap year, month boundaries, timezone), (3) use proper date arithmetic.",
        "failure_pattern": "Failed date fixes: ignore leap years, don't handle month boundaries, use string comparison instead of date comparison, forget edge cases.",
        "action_checklist": [
            "Check leap year handling (divisible by 4, not 100, unless 400)",
            "Check month boundaries (28/29/30/31 days)",
            "Use datetime module for date arithmetic, not manual calculation",
            "Handle timezone if relevant",
            "Check date format string matches input",
        ],
        "edit_guidance": "Use datetime module functions instead of manual date math. Handle edge cases explicitly.",
        "test_guidance": "If date test fails, check: is it a boundary case? leap year? month end? format mismatch?",
        "example_task": "bugfix_253",
        "example_trace": "run_tests(FAIL: days_between backward returns negative) -> read_file -> edit_file(add abs()) -> run_tests(PASS) -> submit",
    },
]

# Build skill library JSON
skill_library = {
    "version": "1.0",
    "description": "EvoCode-Agent skill library for prompt-side injection",
    "skills": [],
}

for skill in SKILLS:
    skill_library["skills"].append({
        "skill_id": skill["skill_id"],
        "trigger_keywords": skill["trigger_keywords"],
        "when_to_use": skill["when_to_use"],
        "summary": skill["success_pattern"][:200],
    })

# Save
root = Path(".")
skills_dir = root / "skills"
skills_dir.mkdir(exist_ok=True)

for skill in SKILLS:
    md = f"""# Skill: {skill['skill_id']}

## When to Use
{skill['when_to_use']}

## Success Pattern
{skill['success_pattern']}

## Common Failure Pattern
{skill['failure_pattern']}

## Action Checklist
{chr(10).join('- ' + item for item in skill['action_checklist'])}

## Edit Guidance
{skill['edit_guidance']}

## Test Feedback Guidance
{skill['test_guidance']}

## Example
Task: {skill['example_task']}
Trace: {skill['example_trace']}
"""
    (skills_dir / f"{skill['skill_id']}.md").write_text(md, encoding="utf-8")
    print(f"  Created skills/{skill['skill_id']}.md")

(root / "data" / "skill_library.json").write_text(json.dumps(skill_library, indent=2), encoding="utf-8")
print(f"\nSaved: data/skill_library.json")
print(f"Skills: {[s['skill_id'] for s in SKILLS]}")
