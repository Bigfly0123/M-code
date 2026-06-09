"""Generate held-out tasks bugfix_240-250."""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    {
        "task_id": "bugfix_240",
        "bug_type": "floating_precision",
        "difficulty": "easy",
        "module": "calc_float",
        "buggy_code": '''def multiply(a, b):
    """Multiply two values."""
    return a * b
''',
        "fixed_code": '''def multiply(a, b, precision=10):
    """Multiply two values with rounding."""
    return round(a * b, precision)
''',
        "test_code": '''from calc_float import multiply


def test_basic():
    assert multiply(0.1, 0.2) == 0.02


def test_integers():
    assert multiply(3, 4) == 12
''',
        "issue": "`multiply(0.1, 0.2)` returns `0.020000000000000004`.\n\nFloating point precision issue.\n\nRun: `python -m pytest tests/test_calc_float.py`",
        "scripted_fix": {"path": "calc_float.py", "old": "def multiply(a, b):\n    \"\"\"Multiply two values.\"\"\"\n    return a * b", "new": "def multiply(a, b, precision=10):\n    \"\"\"Multiply two values with rounding.\"\"\"\n    return round(a * b, precision)"},
    },
    {
        "task_id": "bugfix_241",
        "bug_type": "input_validation",
        "difficulty": "easy",
        "module": "num_check",
        "buggy_code": '''def is_positive(n):
    """Check if number is positive."""
    return n > 0
''',
        "fixed_code": '''def is_positive(n):
    """Check if number is positive."""
    if not isinstance(n, (int, float)):
        return False
    return n > 0
''',
        "test_code": '''from num_check import is_positive


def test_positive():
    assert is_positive(5) is True


def test_negative():
    assert is_positive(-5) is False


def test_string():
    assert is_positive("5") is False
''',
        "issue": "`is_positive(\"5\")` raises `TypeError`.\n\nShould validate input type.\n\nRun: `python -m pytest tests/test_num_check.py`",
        "scripted_fix": {"path": "num_check.py", "old": "def is_positive(n):\n    \"\"\"Check if number is positive.\"\"\"\n    return n > 0", "new": "def is_positive(n):\n    \"\"\"Check if number is positive.\"\"\"\n    if not isinstance(n, (int, float)):\n        return False\n    return n > 0"},
    },
    {
        "task_id": "bugfix_242",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "list_op",
        "buggy_code":'''def flatten(nested):
    """Flatten nested list."""
    result = []
    for item in nested:
        if isinstance(item, list):
            flatten(item)
        else:
            result.append(item)
    return result
''',
        "fixed_code":'''def flatten(nested):
    """Flatten nested list."""
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
''',
        "test_code":'''from list_op import flatten


def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]


def test_nested():
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def test_deep():
    assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]
''',
        "issue": "`flatten([1, [2, 3], 4])` returns `[1, 4]`.\n\nRecursive result not collected.\n\nRun: `python -m pytest tests/test_list_op.py`",
        "scripted_fix": {"path": "list_op.py", "old": "            flatten(item)", "new": "            result.extend(flatten(item))"},
    },
    {
        "task_id": "bugfix_243",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_func",
        "buggy_code":'''def apply_func(func, value):
    """Apply function to value."""
    return func(value)
''',
        "fixed_code":'''def apply_func(func, value):
    """Apply function to value."""
    if func is None:
        return value
    return func(value)
''',
        "test_code":'''from safe_func import apply_func


def test_with_func():
    assert apply_func(lambda x: x * 2, 5) == 10


def test_none_func():
    assert apply_func(None, 5) == 5
''',
        "issue": "`apply_func(None, 5)` raises `TypeError`.\n\nShould handle None function.\n\nRun: `python -m pytest tests/test_safe_func.py`",
        "scripted_fix": {"path": "safe_func.py", "old": "def apply_func(func, value):\n    \"\"\"Apply function to value.\"\"\"\n    return func(value)", "new": "def apply_func(func, value):\n    \"\"\"Apply function to value.\"\"\"\n    if func is None:\n        return value\n    return func(value)"},
    },
    {
        "task_id": "bugfix_244",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "deep_get",
        "buggy_code":'''def get_nested(data, keys):
    """Get nested value from dict."""
    for key in keys:
        data = data[key]
    return data
''',
        "fixed_code":'''def get_nested(data, keys, default=None):
    """Get nested value from dict."""
    for key in keys:
        if not isinstance(data, dict):
            return default
        data = data.get(key, default)
    return data
''',
        "test_code":'''from deep_get import get_nested


def test_basic():
    assert get_nested({"a": {"b": 1}}, ["a", "b"]) == 1


def test_missing():
    assert get_nested({}, ["a", "b"]) is None


def test_default():
    assert get_nested({}, ["a"], default=0) == 0
''',
        "issue": "`get_nested({}, [\"a\", \"b\"])` raises `KeyError`.\n\nShould handle missing keys.\n\nRun: `python -m pytest tests/test_deep_get.py`",
        "scripted_fix": {"path": "deep_get.py", "old": "def get_nested(data, keys):\n    \"\"\"Get nested value from dict.\"\"\"\n    for key in keys:\n        data = data[key]\n    return data", "new": "def get_nested(data, keys, default=None):\n    \"\"\"Get nested value from dict.\"\"\"\n    for key in keys:\n        if not isinstance(data, dict):\n            return default\n        data = data.get(key, default)\n    return data"},
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

    print(f"Generated {len(TASKS)} more held-out tasks: {TASKS[0]['task_id']} .. {TASKS[-1]['task_id']}")


if __name__ == "__main__":
    main()
