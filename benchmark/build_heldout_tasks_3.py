"""Generate held-out tasks bugfix_225-250."""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    {
        "task_id": "bugfix_225",
        "bug_type": "string_split_join",
        "difficulty": "easy",
        "module": "name_join",
        "buggy_code": '''def join_names(names):
    """Join names with comma."""
    return ",".join(names)
''',
        "fixed_code": '''def join_names(names):
    """Join names with comma and space."""
    if not names:
        return ""
    return ", ".join(names)
''',
        "test_code": '''from name_join import join_names


def test_basic():
    assert join_names(["Alice", "Bob"]) == "Alice, Bob"


def test_empty():
    assert join_names([]) == ""
''',
        "issue": "`join_names([\"Alice\", \"Bob\"])` returns `\"Alice,Bob\"` instead of `\"Alice, Bob\"`.\n\nMissing space after comma.\n\nRun: `python -m pytest tests/test_name_join.py`",
        "scripted_fix": {"path": "name_join.py", "old": 'return ",".join(names)', "new": 'return ", ".join(names)'},
    },
    {
        "task_id": "bugfix_226",
        "bug_type": "default_argument",
        "difficulty": "easy",
        "module": "list_builder",
        "buggy_code": '''def add_item(item, lst=[]):
    """Add item to list."""
    lst.append(item)
    return lst
''',
        "fixed_code": '''def add_item(item, lst=None):
    """Add item to list."""
    if lst is None:
        lst = []
    lst.append(item)
    return lst
''',
        "test_code": '''from list_builder import add_item


def test_basic():
    assert add_item(1) == [1]


def test_multiple():
    assert add_item(1) == [1]
    assert add_item(2) == [2]
''',
        "issue": "`add_item(1)` then `add_item(2)` returns `[1, 2]` instead of `[2]`.\n\nMutable default argument.\n\nRun: `python -m pytest tests/test_list_builder.py`",
        "scripted_fix": {"path": "list_builder.py", "old": "def add_item(item, lst=[]):", "new": "def add_item(item, lst=None):\n    if lst is None:\n        lst = []"},
    },
    {
        "task_id": "bugfix_227",
        "bug_type": "case_sensitivity",
        "difficulty": "easy",
        "module": "str_cmp",
        "buggy_code": '''def is_equal(str1, str2):
    """Check if strings are equal."""
    return str1 == str2
''',
        "fixed_code": '''def is_equal(str1, str2, case_sensitive=True):
    """Check if strings are equal."""
    if case_sensitive:
        return str1 == str2
    return str1.lower() == str2.lower()
''',
        "test_code": '''from str_cmp import is_equal


def test_equal():
    assert is_equal("hello", "hello") is True


def test_not_equal():
    assert is_equal("hello", "world") is False


def test_case_insensitive():
    assert is_equal("Hello", "hello", case_sensitive=False) is True
''',
        "issue": "Test expects case-insensitive comparison option.\n\nRun: `python -m pytest tests/test_str_cmp.py`",
        "scripted_fix": {"path": "str_cmp.py", "old": "def is_equal(str1, str2):\n    \"\"\"Check if strings are equal.\"\"\"\n    return str1 == str2", "new": "def is_equal(str1, str2, case_sensitive=True):\n    \"\"\"Check if strings are equal.\"\"\"\n    if case_sensitive:\n        return str1 == str2\n    return str1.lower() == str2.lower()"},
    },
    {
        "task_id": "bugfix_228",
        "bug_type": "path_handling",
        "difficulty": "easy",
        "module": "path_util",
        "buggy_code": '''def join_paths(base, *parts):
    """Join path parts."""
    result = base
    for part in parts:
        result = result + "/" + part
    return result
''',
        "fixed_code": '''import os


def join_paths(base, *parts):
    """Join path parts."""
    return os.path.join(base, *parts)
''',
        "test_code": '''from path_util import join_paths


def test_basic():
    assert join_paths("home", "user", "file") == "home/user/file"


def test_trailing_slash():
    assert join_paths("home/", "user") == "home/user"
''',
        "issue": "`join_paths(\"home/\", \"user\")` returns `\"home//user\"` instead of `\"home/user\"`.\n\nShould handle trailing slashes.\n\nRun: `python -m pytest tests/test_path_util.py`",
        "scripted_fix": {"path": "path_util.py", "old": "def join_paths(base, *parts):\n    \"\"\"Join path parts.\"\"\"\n    result = base\n    for part in parts:\n        result = result + \"/\" + part\n    return result", "new": "import os\n\n\ndef join_paths(base, *parts):\n    \"\"\"Join path parts.\"\"\"\n    return os.path.join(base, *parts)"},
    },
    {
        "task_id": "bugfix_229",
        "bug_type": "rounding",
        "difficulty": "easy",
        "module": "price_fmt",
        "buggy_code": '''def format_price(amount):
    """Format price with 2 decimal places."""
    return str(amount)
''',
        "fixed_code": '''def format_price(amount):
    """Format price with 2 decimal places."""
    return f"{amount:.2f}"
''',
        "test_code": '''from price_fmt import format_price


def test_basic():
    assert format_price(10) == "10.00"


def test_decimal():
    assert format_price(9.9) == "9.90"


def test_round():
    assert format_price(9.999) == "10.00"
''',
        "issue": "`format_price(10)` returns `\"10\"` instead of `\"10.00\"`.\n\nShould format with 2 decimal places.\n\nRun: `python -m pytest tests/test_price_fmt.py`",
        "scripted_fix": {"path": "price_fmt.py", "old": "return str(amount)", "new": 'return f"{amount:.2f}"'},
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
