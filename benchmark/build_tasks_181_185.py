"""Generate benchmark tasks bugfix_181 .. bugfix_200.

Target: 20 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_181",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "triple",
        "buggy_code":'''def triple(n):
    """Triple the number."""
    return n * 2
''',
        "fixed_code":'''def triple(n):
    """Triple the number."""
    return n * 3
''',
        "test_code":'''from triple import triple


def test_basic():
    assert triple(5) == 15


def test_negative():
    assert triple(-3) == -9


def test_zero():
    assert triple(0) == 0
''',
        "issue": "`triple(5)` returns `10` instead of `15`.\n\nShould multiply by 3.\n\nRun: `python -m pytest tests/test_triple.py`",
        "scripted_fix": {"path": "triple.py", "old": "return n * 2", "new": "return n * 3"},
    },
    {
        "task_id": "bugfix_182",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_count",
        "buggy_code":'''def count_items(lst):
    """Count items in list."""
    return len(lst)
''',
        "fixed_code":'''def count_items(lst):
    """Count items in list."""
    if not lst:
        return 0
    return len(lst)
''',
        "test_code":'''from safe_count import count_items


def test_basic():
    assert count_items([1, 2, 3]) == 3


def test_empty():
    assert count_items([]) == 0


def test_none():
    assert count_items(None) == 0
''',
        "issue": "`count_items(None)` raises `TypeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_count.py`",
        "scripted_fix": {"path": "safe_count.py", "old": "def count_items(lst):\n    \"\"\"Count items in list.\"\"\"\n    return len(lst)", "new": "def count_items(lst):\n    \"\"\"Count items in list.\"\"\"\n    if not lst:\n        return 0\n    return len(lst)"},
    },
    {
        "task_id": "bugfix_183",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_items",
        "buggy_code":'''def get_items(d):
    """Get dict items."""
    return list(d.items())
''',
        "fixed_code":'''def get_items(d):
    """Get dict items."""
    if not d:
        return []
    return list(d.items())
''',
        "test_code":'''from safe_items import get_items


def test_basic():
    assert get_items({"a": 1}) == [("a", 1)]


def test_empty():
    assert get_items({}) == []


def test_none():
    assert get_items(None) == []
''',
        "issue": "`get_items(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_items.py`",
        "scripted_fix": {"path": "safe_items.py", "old": "def get_items(d):\n    \"\"\"Get dict items.\"\"\"\n    return list(d.items())", "new": "def get_items(d):\n    \"\"\"Get dict items.\"\"\"\n    if not d:\n        return []\n    return list(d.items())"},
    },
    {
        "task_id": "bugfix_184",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "drop_last",
        "buggy_code":'''def drop_last(lst):
    """Drop last element."""
    return lst[:-2]
''',
        "fixed_code":'''def drop_last(lst):
    """Drop last element."""
    return lst[:-1]
''',
        "test_code":'''from drop_last import drop_last


def test_basic():
    assert drop_last([1, 2, 3]) == [1, 2]


def test_two():
    assert drop_last([1, 2]) == [1]


def test_empty():
    assert drop_last([]) == []
''',
        "issue": "`drop_last([1, 2, 3])` returns `[1]` instead of `[1, 2]`.\n\nOff-by-one: `[:-2]` should be `[:-1]`.\n\nRun: `python -m pytest tests/test_drop_last.py`",
        "scripted_fix": {"path": "drop_last.py", "old": "return lst[:-2]", "new": "return lst[:-1]"},
    },
    {
        "task_id": "bugfix_185",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "half",
        "buggy_code":'''def half(n):
    """Calculate half."""
    return n / 2
''',
        "fixed_code":'''def half(n):
    """Calculate half."""
    return n / 2


def is_odd(n):
    """Check if number is odd."""
    return n % 2 != 0
''',
        "test_code":'''from half import half, is_odd


def test_basic():
    assert half(10) == 5.0


def test_odd():
    assert half(7) == 3.5


def test_is_odd():
    assert is_odd(3) is True
    assert is_odd(4) is False
''',
        "issue": "Tests expect `is_odd` function that doesn't exist.\n\nRun: `python -m pytest tests/test_half.py`",
        "scripted_fix": {"path": "half.py", "old": "    return n / 2\n", "new": "    return n / 2\n\n\ndef is_odd(n):\n    \"\"\"Check if number is odd.\"\"\"\n    return n % 2 != 0\n"},
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
