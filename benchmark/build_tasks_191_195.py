"""Generate benchmark tasks bugfix_191 .. bugfix_200.

Target: 10 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_191",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "increment",
        "buggy_code":'''def increment(n):
    """Increment number."""
    return n
''',
        "fixed_code":'''def increment(n):
    """Increment number."""
    return n + 1
''',
        "test_code":'''from increment import increment


def test_basic():
    assert increment(5) == 6


def test_zero():
    assert increment(0) == 1


def test_negative():
    assert increment(-1) == 0
''',
        "issue": "`increment(5)` returns `5` instead of `6`.\n\nShould add 1.\n\nRun: `python -m pytest tests/test_increment.py`",
        "scripted_fix": {"path": "increment.py", "old": "return n", "new": "return n + 1"},
    },
    {
        "task_id": "bugfix_192",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_reverse",
        "buggy_code":'''def reverse_list(lst):
    """Reverse list."""
    return lst.reverse()
''',
        "fixed_code":'''def reverse_list(lst):
    """Reverse list."""
    if not lst:
        return []
    return lst[::-1]
''',
        "test_code":'''from safe_reverse import reverse_list


def test_basic():
    assert reverse_list([1, 2, 3]) == [3, 2, 1]


def test_empty():
    assert reverse_list([]) == []


def test_none():
    assert reverse_list(None) == []
''',
        "issue": "`reverse_list([1,2,3])` returns `None`.\n\n`list.reverse()` returns None.\n\nRun: `python -m pytest tests/test_safe_reverse.py`",
        "scripted_fix": {"path": "safe_reverse.py", "old": "def reverse_list(lst):\n    \"\"\"Reverse list.\"\"\"\n    return lst.reverse()", "new": "def reverse_list(lst):\n    \"\"\"Reverse list.\"\"\"\n    if not lst:\n        return []\n    return lst[::-1]"},
    },
    {
        "task_id": "bugfix_193",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_copy",
        "buggy_code":'''def copy_dict(d):
    """Copy dict."""
    return d
''',
        "fixed_code":'''def copy_dict(d):
    """Copy dict."""
    if not d:
        return {}
    return d.copy()
''',
        "test_code":'''from safe_copy import copy_dict


def test_basic():
    original = {"a": 1}
    copied = copy_dict(original)
    copied["b"] = 2
    assert original == {"a": 1}


def test_empty():
    assert copy_dict({}) == {}


def test_none():
    assert copy_dict(None) == {}
''',
        "issue": "`copy_dict` returns same reference, not a copy.\n\nShould return a new dict.\n\nRun: `python -m pytest tests/test_safe_copy.py`",
        "scripted_fix": {"path": "safe_copy.py", "old": "def copy_dict(d):\n    \"\"\"Copy dict.\"\"\"\n    return d", "new": "def copy_dict(d):\n    \"\"\"Copy dict.\"\"\"\n    if not d:\n        return {}\n    return d.copy()"},
    },
    {
        "task_id": "bugfix_194",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "skip_last",
        "buggy_code":'''def skip_last(lst):
    """Skip last element."""
    return lst[:-2]
''',
        "fixed_code":'''def skip_last(lst):
    """Skip last element."""
    return lst[:-1]
''',
        "test_code":'''from skip_last import skip_last


def test_basic():
    assert skip_last([1, 2, 3]) == [1, 2]


def test_two():
    assert skip_last([1, 2]) == [1]


def test_empty():
    assert skip_last([]) == []
''',
        "issue": "`skip_last([1, 2, 3])` returns `[1]` instead of `[1, 2]`.\n\nOff-by-one: `[:-2]` should be `[:-1]`.\n\nRun: `python -m pytest tests/test_skip_last.py`",
        "scripted_fix": {"path": "skip_last.py", "old": "return lst[:-2]", "new": "return lst[:-1]"},
    },
    {
        "task_id": "bugfix_195",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "decrement",
        "buggy_code":'''def decrement(n):
    """Decrement number."""
    return n
''',
        "fixed_code":'''def decrement(n):
    """Decrement number."""
    return n - 1
''',
        "test_code":'''from decrement import decrement


def test_basic():
    assert decrement(5) == 4


def test_zero():
    assert decrement(0) == -1


def test_negative():
    assert decrement(-1) == -2
''',
        "issue": "`decrement(5)` returns `5` instead of `4`.\n\nShould subtract 1.\n\nRun: `python -m pytest tests/test_decrement.py`",
        "scripted_fix": {"path": "decrement.py", "old": "return n", "new": "return n - 1"},
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
