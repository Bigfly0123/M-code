"""Generate benchmark tasks bugfix_166 .. bugfix_200.

Target: 35 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_166",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "abs_val",
        "buggy_code":'''def absolute_value(n):
    """Get absolute value."""
    return abs(n)
''',
        "fixed_code":'''def absolute_value(n):
    """Get absolute value."""
    return abs(n)


def is_positive(n):
    """Check if number is positive."""
    return n > 0
''',
        "test_code":'''from abs_val import absolute_value, is_positive


def test_positive():
    assert absolute_value(5) == 5


def test_negative():
    assert absolute_value(-5) == 5


def test_zero():
    assert absolute_value(0) == 0


def test_is_positive():
    assert is_positive(5) is True
    assert is_positive(-5) is False
    assert is_positive(0) is False
''',
        "issue": "Tests expect `is_positive` function that doesn't exist.\n\nRun: `python -m pytest tests/test_abs_val.py`",
        "scripted_fix": {"path": "abs_val.py", "old": "    return abs(n)\n", "new": "    return abs(n)\n\n\ndef is_positive(n):\n    \"\"\"Check if number is positive.\"\"\"\n    return n > 0\n"},
    },
    {
        "task_id": "bugfix_167",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_endswith",
        "buggy_code":'''def ends_with(text, suffix):
    """Check if text ends with suffix."""
    return text.endswith(suffix)
''',
        "fixed_code":'''def ends_with(text, suffix):
    """Check if text ends with suffix."""
    if not text:
        return False
    return text.endswith(suffix)
''',
        "test_code":'''from safe_endswith import ends_with


def test_basic():
    assert ends_with("hello", "lo") is True


def test_false():
    assert ends_with("hello", "he") is False


def test_none():
    assert ends_with(None, "lo") is False
''',
        "issue": "`ends_with(None, \"lo\")` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_endswith.py`",
        "scripted_fix": {"path": "safe_endswith.py", "old": "def ends_with(text, suffix):\n    \"\"\"Check if text ends with suffix.\"\"\"\n    return text.endswith(suffix)", "new": "def ends_with(text, suffix):\n    \"\"\"Check if text ends with suffix.\"\"\"\n    if not text:\n        return False\n    return text.endswith(suffix)"},
    },
    {
        "task_id": "bugfix_168",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_update",
        "buggy_code":'''def merge(base, override):
    """Merge override into base."""
    base.update(override)
    return base
''',
        "fixed_code":'''def merge(base, override):
    """Merge override into base."""
    result = base.copy()
    result.update(override)
    return result
''',
        "test_code":'''from safe_update import merge


def test_merge():
    assert merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_no_mutation():
    base = {"a": 1}
    merge(base, {"b": 2})
    assert base == {"a": 1}
''',
        "issue": "`merge` mutates the `base` dict.\n\nShould return a new dict.\n\nRun: `python -m pytest tests/test_safe_update.py`",
        "scripted_fix": {"path": "safe_update.py", "old": "def merge(base, override):\n    \"\"\"Merge override into base.\"\"\"\n    base.update(override)\n    return base", "new": "def merge(base, override):\n    \"\"\"Merge override into base.\"\"\"\n    result = base.copy()\n    result.update(override)\n    return result"},
    },
    {
        "task_id": "bugfix_169",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "skip_first",
        "buggy_code":'''def skip_first(lst):
    """Skip first element."""
    return lst[2:]
''',
        "fixed_code":'''def skip_first(lst):
    """Skip first element."""
    return lst[1:]
''',
        "test_code":'''from skip_first import skip_first


def test_basic():
    assert skip_first([1, 2, 3]) == [2, 3]


def test_two():
    assert skip_first([1, 2]) == [2]


def test_empty():
    assert skip_first([]) == []
''',
        "issue": "`skip_first([1, 2, 3])` returns `[3]` instead of `[2, 3]`.\n\nOff-by-one: `[2:]` should be `[1:]`.\n\nRun: `python -m pytest tests/test_skip_first.py`",
        "scripted_fix": {"path": "skip_first.py", "old": "return lst[2:]", "new": "return lst[1:]"},
    },
    {
        "task_id": "bugfix_170",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "square",
        "buggy_code":'''def square(n):
    """Calculate square."""
    return n * n
''',
        "fixed_code":'''def square(n):
    """Calculate square."""
    return n * n


def is_even(n):
    """Check if number is even."""
    return n % 2 == 0
''',
        "test_code":'''from square import square, is_even


def test_square():
    assert square(5) == 25


def test_negative():
    assert square(-3) == 9


def test_is_even():
    assert is_even(4) is True
    assert is_even(3) is False
''',
        "issue": "Tests expect `is_even` function that doesn't exist.\n\nRun: `python -m pytest tests/test_square.py`",
        "scripted_fix": {"path": "square.py", "old": "    return n * n\n", "new": "    return n * n\n\n\ndef is_even(n):\n    \"\"\"Check if number is even.\"\"\"\n    return n % 2 == 0\n"},
    },
]


def build_metadata(task: dict) -> dict:
    test_file = f"tests/test_{task['module']}.py"
    return {
        "task_id": task["task_id"],
        "bug_type": task["bug_type"],
        "language": "python",
        "test_command": f"python -m pytest {test_file}",
        "target_files": [f"{task['module']}.py"],
        "difficulty": task["difficulty"],
        "timeout": 30,
        "scripted_fix": task["scripted_fix"],
    }


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"

    for task in TASKS:
        task_dir = tasks_root / task["task_id"]
        repo_dir = task_dir / "repo"
        tests_dir = repo_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        (repo_dir / f"{task['module']}.py").write_text(task["buggy_code"], encoding="utf-8")
        (tests_dir / f"test_{task['module']}.py").write_text(task["test_code"], encoding="utf-8")
        (task_dir / "issue.md").write_text(f"# Bug Report\n\n{task['issue']}\n", encoding="utf-8")
        (task_dir / "metadata.json").write_text(
            json.dumps(build_metadata(task), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(f"Generated {len(TASKS)} tasks: {TASKS[0]['task_id']} .. {TASKS[-1]['task_id']}")


if __name__ == "__main__":
    main()
