"""Generate benchmark tasks bugfix_186 .. bugfix_200.

Target: 15 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_186",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "quadruple",
        "buggy_code":'''def quadruple(n):
    """Quadruple the number."""
    return n * 2
''',
        "fixed_code":'''def quadruple(n):
    """Quadruple the number."""
    return n * 4
''',
        "test_code":'''from quadruple import quadruple


def test_basic():
    assert quadruple(5) == 20


def test_negative():
    assert quadruple(-3) == -12


def test_zero():
    assert quadruple(0) == 0
''',
        "issue": "`quadruple(5)` returns `10` instead of `20`.\n\nShould multiply by 4.\n\nRun: `python -m pytest tests/test_quadruple.py`",
        "scripted_fix": {"path": "quadruple.py", "old": "return n * 2", "new": "return n * 4"},
    },
    {
        "task_id": "bugfix_187",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_index_of",
        "buggy_code":'''def index_of(lst, item):
    """Find index of item in list."""
    return lst.index(item)
''',
        "fixed_code":'''def index_of(lst, item):
    """Find index of item in list."""
    if not lst:
        return -1
    try:
        return lst.index(item)
    except ValueError:
        return -1
''',
        "test_code":'''from safe_index_of import index_of


def test_found():
    assert index_of([1, 2, 3], 2) == 1


def test_not_found():
    assert index_of([1, 2, 3], 4) == -1


def test_none():
    assert index_of(None, 1) == -1
''',
        "issue": "`index_of([1,2,3], 4)` raises `ValueError`.\n\nShould return -1 for not found.\n\nRun: `python -m pytest tests/test_safe_index_of.py`",
        "scripted_fix": {"path": "safe_index_of.py", "old": "def index_of(lst, item):\n    \"\"\"Find index of item in list.\"\"\"\n    return lst.index(item)", "new": "def index_of(lst, item):\n    \"\"\"Find index of item in list.\"\"\"\n    if not lst:\n        return -1\n    try:\n        return lst.index(item)\n    except ValueError:\n        return -1"},
    },
    {
        "task_id": "bugfix_188",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_get_nested",
        "buggy_code":'''def get_nested_value(data, keys):
    """Get nested value from dict."""
    for key in keys:
        data = data[key]
    return data
''',
        "fixed_code":'''def get_nested_value(data, keys, default=None):
    """Get nested value from dict."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    return data
''',
        "test_code":'''from safe_get_nested import get_nested_value


def test_basic():
    assert get_nested_value({"a": {"b": 1}}, ["a", "b"]) == 1


def test_missing():
    assert get_nested_value({}, ["a", "b"]) is None


def test_default():
    assert get_nested_value({}, ["a"], default=0) == 0
''',
        "issue": "`get_nested_value({}, [\"a\", \"b\"])` raises `KeyError`.\n\nShould handle missing keys.\n\nRun: `python -m pytest tests/test_safe_get_nested.py`",
        "scripted_fix": {"path": "safe_get_nested.py", "old": "def get_nested_value(data, keys):\n    \"\"\"Get nested value from dict.\"\"\"\n    for key in keys:\n        data = data[key]\n    return data", "new": "def get_nested_value(data, keys, default=None):\n    \"\"\"Get nested value from dict.\"\"\"\n    for key in keys:\n        if not isinstance(data, dict):\n            return default\n        data = data.get(key, default)\n    return data"},
    },
    {
        "task_id": "bugfix_189",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "keep_first",
        "buggy_code":'''def keep_first_n(lst, n):
    """Keep first n items."""
    return lst[:n-1]
''',
        "fixed_code":'''def keep_first_n(lst, n):
    """Keep first n items."""
    return lst[:n]
''',
        "test_code":'''from keep_first import keep_first_n


def test_basic():
    assert keep_first_n([1, 2, 3, 4, 5], 3) == [1, 2, 3]


def test_all():
    assert keep_first_n([1, 2, 3], 5) == [1, 2, 3]


def test_zero():
    assert keep_first_n([1, 2, 3], 0) == []
''',
        "issue": "`keep_first_n([1,2,3,4,5], 3)` returns `[1, 2]` instead of `[1, 2, 3]`.\n\nOff-by-one: `n-1` should be `n`.\n\nRun: `python -m pytest tests/test_keep_first.py`",
        "scripted_fix": {"path": "keep_first.py", "old": "return lst[:n-1]", "new": "return lst[:n]"},
    },
    {
        "task_id": "bugfix_190",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "modulus",
        "buggy_code":'''def mod(a, b):
    """Calculate modulus."""
    return a % b
''',
        "fixed_code":'''def mod(a, b):
    """Calculate modulus."""
    if b == 0:
        return None
    return a % b
''',
        "test_code":'''from modulus import mod


def test_basic():
    assert mod(10, 3) == 1


def test_zero():
    assert mod(10, 0) is None


def test_exact():
    assert mod(10, 5) == 0
''',
        "issue": "`mod(10, 0)` raises `ZeroDivisionError`.\n\nShould handle zero divisor.\n\nRun: `python -m pytest tests/test_modulus.py`",
        "scripted_fix": {"path": "modulus.py", "old": "def mod(a, b):\n    \"\"\"Calculate modulus.\"\"\"\n    return a % b", "new": "def mod(a, b):\n    \"\"\"Calculate modulus.\"\"\"\n    if b == 0:\n        return None\n    return a % b"},
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
