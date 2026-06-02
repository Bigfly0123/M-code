"""Generate benchmark tasks bugfix_171 .. bugfix_200.

Target: 30 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_171",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "cube",
        "buggy_code":'''def cube(n):
    """Calculate cube."""
    return n * n
''',
        "fixed_code":'''def cube(n):
    """Calculate cube."""
    return n * n * n
''',
        "test_code":'''from cube import cube


def test_basic():
    assert cube(3) == 27


def test_negative():
    assert cube(-2) == -8


def test_zero():
    assert cube(0) == 0
''',
        "issue": "`cube(3)` returns `9` instead of `27`.\n\nShould multiply three times.\n\nRun: `python -m pytest tests/test_cube.py`",
        "scripted_fix": {"path": "cube.py", "old": "return n * n", "new": "return n * n * n"},
    },
    {
        "task_id": "bugfix_172",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_contains",
        "buggy_code":'''def contains(text, sub):
    """Check if text contains substring."""
    return sub in text
''',
        "fixed_code":'''def contains(text, sub):
    """Check if text contains substring."""
    if not text:
        return False
    return sub in text
''',
        "test_code":'''from safe_contains import contains


def test_basic():
    assert contains("hello world", "world") is True


def test_false():
    assert contains("hello", "xyz") is False


def test_none():
    assert contains(None, "hello") is False
''',
        "issue": "`contains(None, \"hello\")` raises `TypeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_contains.py`",
        "scripted_fix": {"path": "safe_contains.py", "old": "def contains(text, sub):\n    \"\"\"Check if text contains substring.\"\"\"\n    return sub in text", "new": "def contains(text, sub):\n    \"\"\"Check if text contains substring.\"\"\"\n    if not text:\n        return False\n    return sub in text"},
    },
    {
        "task_id": "bugfix_173",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_keys",
        "buggy_code":'''def get_keys(d):
    """Get dict keys."""
    return list(d.keys())
''',
        "fixed_code":'''def get_keys(d):
    """Get dict keys."""
    if not d:
        return []
    return list(d.keys())
''',
        "test_code":'''from safe_keys import get_keys


def test_basic():
    assert get_keys({"a": 1, "b": 2}) == ["a", "b"]


def test_empty():
    assert get_keys({}) == []


def test_none():
    assert get_keys(None) == []
''',
        "issue": "`get_keys(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_keys.py`",
        "scripted_fix": {"path": "safe_keys.py", "old": "def get_keys(d):\n    \"\"\"Get dict keys.\"\"\"\n    return list(d.keys())", "new": "def get_keys(d):\n    \"\"\"Get dict keys.\"\"\"\n    if not d:\n        return []\n    return list(d.keys())"},
    },
    {
        "task_id": "bugfix_174",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "remove_at",
        "buggy_code":'''def remove_at(lst, index):
    """Remove item at index."""
    return lst[:index] + lst[index+2:]
''',
        "fixed_code":'''def remove_at(lst, index):
    """Remove item at index."""
    return lst[:index] + lst[index+1:]
''',
        "test_code":'''from remove_at import remove_at


def test_basic():
    assert remove_at([1, 2, 3, 4], 1) == [1, 3, 4]


def test_first():
    assert remove_at([1, 2, 3], 0) == [2, 3]


def test_last():
    assert remove_at([1, 2, 3], 2) == [1, 2]
''',
        "issue": "`remove_at([1,2,3,4], 1)` returns `[1, 4]` instead of `[1, 3, 4]`.\n\nOff-by-one: `index+2` should be `index+1`.\n\nRun: `python -m pytest tests/test_remove_at.py`",
        "scripted_fix": {"path": "remove_at.py", "old": "return lst[:index] + lst[index+2:]", "new": "return lst[:index] + lst[index+1:]"},
    },
    {
        "task_id": "bugfix_175",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "power",
        "buggy_code":'''def power(base, exp):
    """Calculate power."""
    return base ** exp
''',
        "fixed_code":'''def power(base, exp):
    """Calculate power."""
    if exp < 0:
        return 1 / (base ** abs(exp))
    return base ** exp
''',
        "test_code":'''from power import power


def test_basic():
    assert power(2, 3) == 8


def test_zero():
    assert power(5, 0) == 1


def test_negative():
    assert power(2, -1) == 0.5
''',
        "issue": "`power(2, -1)` returns `0.5` but test expects explicit handling.\n\nRun: `python -m pytest tests/test_power.py`",
        "scripted_fix": {"path": "power.py", "old": "def power(base, exp):\n    \"\"\"Calculate power.\"\"\"\n    return base ** exp", "new": "def power(base, exp):\n    \"\"\"Calculate power.\"\"\"\n    if exp < 0:\n        return 1 / (base ** abs(exp))\n    return base ** exp"},
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
