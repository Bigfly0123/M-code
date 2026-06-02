"""Generate benchmark tasks bugfix_196 .. bugfix_200.

Target: 5 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_196",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "abs_diff",
        "buggy_code":'''def absolute_difference(a, b):
    """Calculate absolute difference."""
    return a - b
''',
        "fixed_code":'''def absolute_difference(a, b):
    """Calculate absolute difference."""
    return abs(a - b)
''',
        "test_code":'''from abs_diff import absolute_difference


def test_positive():
    assert absolute_difference(5, 3) == 2


def test_negative():
    assert absolute_difference(3, 5) == 2


def test_equal():
    assert absolute_difference(5, 5) == 0
''',
        "issue": "`absolute_difference(3, 5)` returns `-2` instead of `2`.\n\nShould use `abs()`.\n\nRun: `python -m pytest tests/test_abs_diff.py`",
        "scripted_fix": {"path": "abs_diff.py", "old": "return a - b", "new": "return abs(a - b)"},
    },
    {
        "task_id": "bugfix_197",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_max",
        "buggy_code":'''def find_max(lst):
    """Find maximum value."""
    return max(lst)
''',
        "fixed_code":'''def find_max(lst):
    """Find maximum value."""
    if not lst:
        return None
    return max(lst)
''',
        "test_code":'''from safe_max import find_max


def test_basic():
    assert find_max([1, 3, 2]) == 3


def test_empty():
    assert find_max([]) is None


def test_none():
    assert find_max(None) is None
''',
        "issue": "`find_max([])` raises `ValueError`.\n\nShould handle empty list.\n\nRun: `python -m pytest tests/test_safe_max.py`",
        "scripted_fix": {"path": "safe_max.py", "old": "def find_max(lst):\n    \"\"\"Find maximum value.\"\"\"\n    return max(lst)", "new": "def find_max(lst):\n    \"\"\"Find maximum value.\"\"\"\n    if not lst:\n        return None\n    return max(lst)"},
    },
    {
        "task_id": "bugfix_198",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_popitem",
        "buggy_code":'''def pop_item(d):
    """Pop item from dict."""
    return d.popitem()
''',
        "fixed_code":'''def pop_item(d):
    """Pop item from dict."""
    if not d:
        return None
    return d.popitem()
''',
        "test_code":'''from safe_popitem import pop_item


def test_basic():
    d = {"a": 1}
    result = pop_item(d)
    assert result == ("a", 1)
    assert d == {}


def test_empty():
    assert pop_item({}) is None


def test_none():
    assert pop_item(None) is None
''',
        "issue": "`pop_item({})` raises `KeyError`.\n\nShould handle empty dict.\n\nRun: `python -m pytest tests/test_safe_popitem.py`",
        "scripted_fix": {"path": "safe_popitem.py", "old": "def pop_item(d):\n    \"\"\"Pop item from dict.\"\"\"\n    return d.popitem()", "new": "def pop_item(d):\n    \"\"\"Pop item from dict.\"\"\"\n    if not d:\n        return None\n    return d.popitem()"},
    },
    {
        "task_id": "bugfix_199",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "get_tail",
        "buggy_code":'''def get_tail(lst):
    """Get all but first element."""
    return lst[2:]
''',
        "fixed_code":'''def get_tail(lst):
    """Get all but first element."""
    return lst[1:]
''',
        "test_code":'''from get_tail import get_tail


def test_basic():
    assert get_tail([1, 2, 3]) == [2, 3]


def test_two():
    assert get_tail([1, 2]) == [2]


def test_empty():
    assert get_tail([]) == []
''',
        "issue": "`get_tail([1, 2, 3])` returns `[3]` instead of `[2, 3]`.\n\nOff-by-one: `[2:]` should be `[1:]`.\n\nRun: `python -m pytest tests/test_get_tail.py`",
        "scripted_fix": {"path": "get_tail.py", "old": "return lst[2:]", "new": "return lst[1:]"},
    },
    {
        "task_id": "bugfix_200",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "square_sum",
        "buggy_code":'''def sum_of_squares(n):
    """Calculate sum of squares from 1 to n."""
    return sum(i for i in range(n))
''',
        "fixed_code":'''def sum_of_squares(n):
    """Calculate sum of squares from 1 to n."""
    return sum(i * i for i in range(1, n + 1))
''',
        "test_code":'''from square_sum import sum_of_squares


def test_basic():
    assert sum_of_squares(3) == 14  # 1 + 4 + 9


def test_one():
    assert sum_of_squares(1) == 1


def test_zero():
    assert sum_of_squares(0) == 0
''',
        "issue": "`sum_of_squares(3)` returns `3` instead of `14`.\n\nShould square each number.\n\nRun: `python -m pytest tests/test_square_sum.py`",
        "scripted_fix": {"path": "square_sum.py", "old": "return sum(i for i in range(n))", "new": "return sum(i * i for i in range(1, n + 1))"},
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
