"""Generate benchmark tasks bugfix_156 .. bugfix_200.

Target: 45 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Add more simple tasks
    {
        "task_id": "bugfix_156",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "reverse_str",
        "buggy_code":'''def reverse_string(text):
    """Reverse a string."""
    return text.reverse()
''',
        "fixed_code":'''def reverse_string(text):
    """Reverse a string."""
    return text[::-1]
''',
        "test_code":'''from reverse_str import reverse_string


def test_basic():
    assert reverse_string("hello") == "olleh"


def test_empty():
    assert reverse_string("") == ""


def test_single():
    assert reverse_string("a") == "a"
''',
        "issue": "`reverse_string(\"hello\")` raises `AttributeError`.\n\n`str.reverse()` doesn't exist.\n\nRun: `python -m pytest tests/test_reverse_str.py`",
        "scripted_fix": {"path": "reverse_str.py", "old": "return text.reverse()", "new": "return text[::-1]"},
    },
    {
        "task_id": "bugfix_157",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_join",
        "buggy_code":'''def join_path(parts):
    """Join path parts."""
    return "/".join(parts)
''',
        "fixed_code":'''def join_path(parts):
    """Join path parts."""
    if not parts:
        return ""
    return "/".join(parts)
''',
        "test_code":'''from safe_join import join_path


def test_basic():
    assert join_path(["home", "user", "file"]) == "home/user/file"


def test_empty():
    assert join_path([]) == ""


def test_none():
    assert join_path(None) == ""
''',
        "issue": "`join_path(None)` raises `TypeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_join.py`",
        "scripted_fix": {"path": "safe_join.py", "old": "def join_path(parts):\n    \"\"\"Join path parts.\"\"\"\n    return \"/\".join(parts)", "new": "def join_path(parts):\n    \"\"\"Join path parts.\"\"\"\n    if not parts:\n        return \"\"\n    return \"/\".join(parts)"},
    },
    {
        "task_id": "bugfix_158",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "get_default",
        "buggy_code":'''def get_config(config, key):
    """Get config value."""
    return config[key]
''',
        "fixed_code":'''def get_config(config, key, default=None):
    """Get config value."""
    return config.get(key, default)
''',
        "test_code":'''from get_default import get_config


def test_existing():
    assert get_config({"host": "localhost"}, "host") == "localhost"


def test_missing():
    assert get_config({}, "host") is None


def test_default():
    assert get_config({}, "host", "0.0.0.0") == "0.0.0.0"
''',
        "issue": "`get_config({}, \"host\")` raises `KeyError`.\n\nShould handle missing keys.\n\nRun: `python -m pytest tests/test_get_default.py`",
        "scripted_fix": {"path": "get_default.py", "old": "def get_config(config, key):\n    \"\"\"Get config value.\"\"\"\n    return config[key]", "new": "def get_config(config, key, default=None):\n    \"\"\"Get config value.\"\"\"\n    return config.get(key, default)"},
    },
    {
        "task_id": "bugfix_159",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "take_n",
        "buggy_code":'''def take_first(lst, n):
    """Take first n items."""
    return lst[:n+1]
''',
        "fixed_code":'''def take_first(lst, n):
    """Take first n items."""
    return lst[:n]
''',
        "test_code":'''from take_n import take_first


def test_basic():
    assert take_first([1, 2, 3, 4, 5], 3) == [1, 2, 3]


def test_all():
    assert take_first([1, 2, 3], 5) == [1, 2, 3]


def test_zero():
    assert take_first([1, 2, 3], 0) == []
''',
        "issue": "`take_first([1,2,3,4,5], 3)` returns `[1, 2, 3, 4]` instead of `[1, 2, 3]`.\n\nOff-by-one: `n+1` should be `n`.\n\nRun: `python -m pytest tests/test_take_n.py`",
        "scripted_fix": {"path": "take_n.py", "old": "return lst[:n+1]", "new": "return lst[:n]"},
    },
    {
        "task_id": "bugfix_160",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "palindrome",
        "buggy_code":'''def is_palindrome(text):
    """Check if text is palindrome."""
    return text == text.reverse()
''',
        "fixed_code":'''def is_palindrome(text):
    """Check if text is palindrome."""
    return text == text[::-1]
''',
        "test_code":'''from palindrome import is_palindrome


def test_palindrome():
    assert is_palindrome("racecar") is True


def test_not():
    assert is_palindrome("hello") is False


def test_empty():
    assert is_palindrome("") is True
''',
        "issue": "`is_palindrome(\"racecar\")` raises `AttributeError`.\n\n`str.reverse()` doesn't exist.\n\nRun: `python -m pytest tests/test_palindrome.py`",
        "scripted_fix": {"path": "palindrome.py", "old": "return text == text.reverse()", "new": "return text == text[::-1]"},
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
