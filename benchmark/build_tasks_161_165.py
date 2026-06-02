"""Generate benchmark tasks bugfix_161 .. bugfix_200.

Target: 40 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_161",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "count_char",
        "buggy_code":'''def count_character(text, char):
    """Count occurrences of character."""
    return text.count(char)
''',
        "fixed_code":'''def count_character(text, char):
    """Count occurrences of character."""
    if not text:
        return 0
    return text.count(char)
''',
        "test_code":'''from count_char import count_character


def test_basic():
    assert count_character("hello", "l") == 2


def test_none():
    assert count_character(None, "a") == 0


def test_empty():
    assert count_character("", "a") == 0
''',
        "issue": "`count_character(None, \"a\")` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_count_char.py`",
        "scripted_fix": {"path": "count_char.py", "old": "def count_character(text, char):\n    \"\"\"Count occurrences of character.\"\"\"\n    return text.count(char)", "new": "def count_character(text, char):\n    \"\"\"Count occurrences of character.\"\"\"\n    if not text:\n        return 0\n    return text.count(char)"},
    },
    {
        "task_id": "bugfix_162",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_startswith",
        "buggy_code":'''def starts_with(text, prefix):
    """Check if text starts with prefix."""
    return text.startswith(prefix)
''',
        "fixed_code":'''def starts_with(text, prefix):
    """Check if text starts with prefix."""
    if not text:
        return False
    return text.startswith(prefix)
''',
        "test_code":'''from safe_startswith import starts_with


def test_basic():
    assert starts_with("hello", "he") is True


def test_false():
    assert starts_with("hello", "wo") is False


def test_none():
    assert starts_with(None, "he") is False
''',
        "issue": "`starts_with(None, \"he\")` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_startswith.py`",
        "scripted_fix": {"path": "safe_startswith.py", "old": "def starts_with(text, prefix):\n    \"\"\"Check if text starts with prefix.\"\"\"\n    return text.startswith(prefix)", "new": "def starts_with(text, prefix):\n    \"\"\"Check if text starts with prefix.\"\"\"\n    if not text:\n        return False\n    return text.startswith(prefix)"},
    },
    {
        "task_id": "bugfix_163",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_setdefault",
        "buggy_code":'''def get_or_create(data, key, default):
    """Get value or create with default."""
    if key not in data:
        data[key] = default
    return data[key]
''',
        "fixed_code":'''def get_or_create(data, key, default):
    """Get value or create with default."""
    return data.setdefault(key, default)
''',
        "test_code":'''from safe_setdefault import get_or_create


def test_existing():
    d = {"a": 1}
    assert get_or_create(d, "a", 0) == 1


def test_new():
    d = {}
    assert get_or_create(d, "a", 0) == 0
    assert d == {"a": 0}
''',
        "issue": "Should use `setdefault` for cleaner code.\n\nRun: `python -m pytest tests/test_safe_setdefault.py`",
        "scripted_fix": {"path": "safe_setdefault.py", "old": "def get_or_create(data, key, default):\n    \"\"\"Get value or create with default.\"\"\"\n    if key not in data:\n        data[key] = default\n    return data[key]", "new": "def get_or_create(data, key, default):\n    \"\"\"Get value or create with default.\"\"\"\n    return data.setdefault(key, default)"},
    },
    {
        "task_id": "bugfix_164",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "drop_first",
        "buggy_code":'''def drop_first_n(lst, n):
    """Drop first n items."""
    return lst[n+1:]
''',
        "fixed_code":'''def drop_first_n(lst, n):
    """Drop first n items."""
    return lst[n:]
''',
        "test_code":'''from drop_first import drop_first_n


def test_basic():
    assert drop_first_n([1, 2, 3, 4, 5], 2) == [3, 4, 5]


def test_all():
    assert drop_first_n([1, 2, 3], 3) == []


def test_zero():
    assert drop_first_n([1, 2, 3], 0) == [1, 2, 3]
''',
        "issue": "`drop_first_n([1,2,3,4,5], 2)` returns `[4, 5]` instead of `[3, 4, 5]`.\n\nOff-by-one: `n+1` should be `n`.\n\nRun: `python -m pytest tests/test_drop_first.py`",
        "scripted_fix": {"path": "drop_first.py", "old": "return lst[n+1:]", "new": "return lst[n:]"},
    },
    {
        "task_id": "bugfix_165",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "repeat_char",
        "buggy_code":'''def repeat_character(char, times):
    """Repeat character n times."""
    return char * times
''',
        "fixed_code":'''def repeat_character(char, times):
    """Repeat character n times."""
    if times < 0:
        return ""
    return char * times
''',
        "test_code":'''from repeat_char import repeat_character


def test_basic():
    assert repeat_character("a", 3) == "aaa"


def test_zero():
    assert repeat_character("a", 0) == ""


def test_negative():
    assert repeat_character("a", -1) == ""
''',
        "issue": "`repeat_character(\"a\", -1)` returns `\"\"` but should explicitly handle negative.\n\nRun: `python -m pytest tests/test_repeat_char.py`",
        "scripted_fix": {"path": "repeat_char.py", "old": "def repeat_character(char, times):\n    \"\"\"Repeat character n times.\"\"\"\n    return char * times", "new": "def repeat_character(char, times):\n    \"\"\"Repeat character n times.\"\"\"\n    if times < 0:\n        return \"\"\n    return char * times"},
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
