"""Generate held-out tasks bugfix_230-250."""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    {
        "task_id": "bugfix_230",
        "bug_type": "list_mutation",
        "difficulty": "easy",
        "module": "list_clean",
        "buggy_code": '''def remove_none(lst):
    """Remove None values from list."""
    for item in lst:
        if item is None:
            lst.remove(item)
    return lst
''',
        "fixed_code": '''def remove_none(lst):
    """Remove None values from list."""
    return [item for item in lst if item is not None]
''',
        "test_code": '''from list_clean import remove_none


def test_basic():
    assert remove_none([1, None, 2, None, 3]) == [1, 2, 3]


def test_no_none():
    assert remove_none([1, 2, 3]) == [1, 2, 3]


def test_all_none():
    assert remove_none([None, None]) == []
''',
        "issue": "`remove_none([1, None, 2, None, 3])` may skip elements.\n\nModifying list while iterating.\n\nRun: `python -m pytest tests/test_list_clean.py`",
        "scripted_fix": {"path": "list_clean.py", "old": "def remove_none(lst):\n    \"\"\"Remove None values from list.\"\"\"\n    for item in lst:\n        if item is None:\n            lst.remove(item)\n    return lst", "new": "def remove_none(lst):\n    \"\"\"Remove None values from list.\"\"\"\n    return [item for item in lst if item is not None]"},
    },
    {
        "task_id": "bugfix_231",
        "bug_type": "set_operations",
        "difficulty": "easy",
        "module": "unique_util",
        "buggy_code": '''def get_unique(lst):
    """Get unique items preserving order."""
    return list(set(lst))
''',
        "fixed_code": '''def get_unique(lst):
    """Get unique items preserving order."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
''',
        "test_code": '''from unique_util import get_unique


def test_basic():
    assert get_unique([1, 2, 2, 3, 3, 3]) == [1, 2, 3]


def test_order():
    result = get_unique([3, 1, 2, 1, 3])
    assert result == [3, 1, 2]
''',
        "issue": "`get_unique([3, 1, 2, 1, 3])` doesn't preserve order.\n\n`set()` doesn't maintain insertion order.\n\nRun: `python -m pytest tests/test_unique_util.py`",
        "scripted_fix": {"path": "unique_util.py", "old": "def get_unique(lst):\n    \"\"\"Get unique items preserving order.\"\"\"\n    return list(set(lst))", "new": "def get_unique(lst):\n    \"\"\"Get unique items preserving order.\"\"\"\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result"},
    },
    {
        "task_id": "bugfix_232",
        "bug_type": "sorting_key",
        "difficulty": "easy",
        "module": "sort_util",
        "buggy_code": '''def sort_by_length(strings):
    """Sort strings by length."""
    return sorted(strings)
''',
        "fixed_code": '''def sort_by_length(strings):
    """Sort strings by length."""
    return sorted(strings, key=len)
''',
        "test_code": '''from sort_util import sort_by_length


def test_basic():
    assert sort_by_length(["hello", "hi", "hey"]) == ["hi", "hey", "hello"]


def test_same_length():
    result = sort_by_length(["abc", "def", "ghi"])
    assert result == ["abc", "def", "ghi"]
''',
        "issue": "`sort_by_length([\"hello\", \"hi\", \"hey\"])` returns `[\"hello\", \"hey\", \"hi\"]`.\n\nShould sort by length, not alphabetically.\n\nRun: `python -m pytest tests/test_sort_util.py`",
        "scripted_fix": {"path": "sort_util.py", "old": "return sorted(strings)", "new": "return sorted(strings, key=len)"},
    },
    {
        "task_id": "bugfix_233",
        "bug_type": "csv_parsing",
        "difficulty": "easy",
        "module": "csv_util",
        "buggy_code": '''def parse_csv_line(line):
    """Parse CSV line."""
    return line.split(",")
''',
        "fixed_code": '''import csv
import io


def parse_csv_line(line):
    """Parse CSV line."""
    reader = csv.reader(io.StringIO(line))
    return next(reader)
''',
        "test_code": '''from csv_util import parse_csv_line


def test_basic():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_quoted():
    assert parse_csv_line('"hello, world",b') == ["hello, world", "b"]
''',
        "issue": "`parse_csv_line('\"hello, world\",b')` doesn't handle quoted fields.\n\nShould use csv module.\n\nRun: `python -m pytest tests/test_csv_util.py`",
        "scripted_fix": {"path": "csv_util.py", "old": "def parse_csv_line(line):\n    \"\"\"Parse CSV line.\"\"\"\n    return line.split(\",\")", "new": "import csv\nimport io\n\n\ndef parse_csv_line(line):\n    \"\"\"Parse CSV line.\"\"\"\n    reader = csv.reader(io.StringIO(line))\n    return next(reader)"},
    },
    {
        "task_id": "bugfix_234",
        "bug_type": "url_parsing",
        "difficulty": "easy",
        "module": "url_util",
        "buggy_code": '''def get_path(url):
    """Get path from URL."""
    return url.split("//")[1].split("/", 1)[1]
''',
        "fixed_code": '''from urllib.parse import urlparse


def get_path(url):
    """Get path from URL."""
    parsed = urlparse(url)
    return parsed.path
''',
        "test_code": '''from url_util import get_path


def test_basic():
    assert get_path("https://example.com/path/to/page") == "/path/to/page"


def test_root():
    assert get_path("https://example.com") == ""
''',
        "issue": "`get_path(\"https://example.com\")` raises `IndexError`.\n\nShould handle URLs without path.\n\nRun: `python -m pytest tests/test_url_util.py`",
        "scripted_fix": {"path": "url_util.py", "old": "def get_path(url):\n    \"\"\"Get path from URL.\"\"\"\n    return url.split(\"//\")[1].split(\"/\", 1)[1]", "new": "from urllib.parse import urlparse\n\n\ndef get_path(url):\n    \"\"\"Get path from URL.\"\"\"\n    parsed = urlparse(url)\n    return parsed.path"},
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
