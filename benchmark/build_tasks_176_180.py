"""Generate benchmark tasks bugfix_176 .. bugfix_200.

Target: 25 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_176",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "double",
        "buggy_code":'''def double(n):
    """Double the number."""
    return n + n
''',
        "fixed_code":'''def double(n):
    """Double the number."""
    return n * 2
''',
        "test_code":'''from double import double


def test_basic():
    assert double(5) == 10


def test_negative():
    assert double(-3) == -6


def test_zero():
    assert double(0) == 0
''',
        "issue": "Should use multiplication for clarity.\n\nRun: `python -m pytest tests/test_double.py`",
        "scripted_fix": {"path": "double.py", "old": "return n + n", "new": "return n * 2"},
    },
    {
        "task_id": "bugfix_177",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_find",
        "buggy_code":'''def find_index(text, sub):
    """Find index of substring."""
    return text.index(sub)
''',
        "fixed_code":'''def find_index(text, sub):
    """Find index of substring."""
    if not text:
        return -1
    try:
        return text.index(sub)
    except ValueError:
        return -1
''',
        "test_code":'''from safe_find import find_index


def test_found():
    assert find_index("hello", "ll") == 2


def test_not_found():
    assert find_index("hello", "xyz") == -1


def test_none():
    assert find_index(None, "ll") == -1
''',
        "issue": "`find_index(\"hello\", \"xyz\")` raises `ValueError`.\n\nShould return -1 for not found.\n\nRun: `python -m pytest tests/test_safe_find.py`",
        "scripted_fix": {"path": "safe_find.py", "old": "def find_index(text, sub):\n    \"\"\"Find index of substring.\"\"\"\n    return text.index(sub)", "new": "def find_index(text, sub):\n    \"\"\"Find index of substring.\"\"\"\n    if not text:\n        return -1\n    try:\n        return text.index(sub)\n    except ValueError:\n        return -1"},
    },
    {
        "task_id": "bugfix_178",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_values",
        "buggy_code":'''def get_values(d):
    """Get dict values."""
    return list(d.values())
''',
        "fixed_code":'''def get_values(d):
    """Get dict values."""
    if not d:
        return []
    return list(d.values())
''',
        "test_code":'''from safe_values import get_values


def test_basic():
    assert get_values({"a": 1, "b": 2}) == [1, 2]


def test_empty():
    assert get_values({}) == []


def test_none():
    assert get_values(None) == []
''',
        "issue": "`get_values(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_values.py`",
        "scripted_fix": {"path": "safe_values.py", "old": "def get_values(d):\n    \"\"\"Get dict values.\"\"\"\n    return list(d.values())", "new": "def get_values(d):\n    \"\"\"Get dict values.\"\"\"\n    if not d:\n        return []\n    return list(d.values())"},
    },
    {
        "task_id": "bugfix_179",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "insert_end",
        "buggy_code":'''def insert_at_end(lst, value):
    """Insert value at end."""
    lst.insert(len(lst) + 1, value)
    return lst
''',
        "fixed_code":'''def insert_at_end(lst, value):
    """Insert value at end."""
    lst.append(value)
    return lst
''',
        "test_code":'''from insert_end import insert_at_end


def test_basic():
    assert insert_at_end([1, 2, 3], 4) == [1, 2, 3, 4]


def test_empty():
    assert insert_at_end([], 1) == [1]
''',
        "issue": "`insert_at_end([1,2,3], 4)` may not work correctly.\n\nShould use `append`.\n\nRun: `python -m pytest tests/test_insert_end.py`",
        "scripted_fix": {"path": "insert_end.py", "old": "def insert_at_end(lst, value):\n    \"\"\"Insert value at end.\"\"\"\n    lst.insert(len(lst) + 1, value)\n    return lst", "new": "def insert_at_end(lst, value):\n    \"\"\"Insert value at end.\"\"\"\n    lst.append(value)\n    return lst"},
    },
    {
        "task_id": "bugfix_180",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "negate",
        "buggy_code":'''def negate(n):
    """Negate number."""
    return -n
''',
        "fixed_code":'''def negate(n):
    """Negate number."""
    return -n


def is_negative(n):
    """Check if number is negative."""
    return n < 0
''',
        "test_code":'''from negate import negate, is_negative


def test_positive():
    assert negate(5) == -5


def test_negative():
    assert negate(-5) == 5


def test_is_negative():
    assert is_negative(-5) is True
    assert is_negative(5) is False
    assert is_negative(0) is False
''',
        "issue": "Tests expect `is_negative` function that doesn't exist.\n\nRun: `python -m pytest tests/test_negate.py`",
        "scripted_fix": {"path": "negate.py", "old": "    return -n\n", "new": "    return -n\n\n\ndef is_negative(n):\n    \"\"\"Check if number is negative.\"\"\"\n    return n < 0\n"},
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
