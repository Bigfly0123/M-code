"""Generate held-out tasks bugfix_245-250."""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    {
        "task_id": "bugfix_245",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "str_rev",
        "buggy_code":'''def reverse_string(s):
    """Reverse a string."""
    return s.reverse()
''',
        "fixed_code":'''def reverse_string(s):
    """Reverse a string."""
    return s[::-1]
''',
        "test_code":'''from str_rev import reverse_string


def test_basic():
    assert reverse_string("hello") == "olleh"


def test_empty():
    assert reverse_string("") == ""
''',
        "issue": "`reverse_string(\"hello\")` raises `AttributeError`.\n\n`str.reverse()` doesn't exist.\n\nRun: `python -m pytest tests/test_str_rev.py`",
        "scripted_fix": {"path": "str_rev.py", "old": "return s.reverse()", "new": "return s[::-1]"},
    },
    {
        "task_id": "bugfix_246",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "is_pal",
        "buggy_code":'''def is_palindrome(s):
    """Check if string is palindrome."""
    return s == s.reverse()
''',
        "fixed_code":'''def is_palindrome(s):
    """Check if string is palindrome."""
    return s == s[::-1]
''',
        "test_code":'''from is_pal import is_palindrome


def test_palindrome():
    assert is_palindrome("racecar") is True


def test_not():
    assert is_palindrome("hello") is False
''',
        "issue": "`is_palindrome(\"racecar\")` raises `AttributeError`.\n\n`str.reverse()` doesn't exist.\n\nRun: `python -m pytest tests/test_is_pal.py`",
        "scripted_fix": {"path": "is_pal.py", "old": "return s == s.reverse()", "new": "return s == s[::-1]"},
    },
    {
        "task_id": "bugfix_247",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "count_v",
        "buggy_code":'''def count_vowels(s):
    """Count vowels in string."""
    vowels = "aeiou"
    return sum(1 for c in s if c in vowels)
''',
        "fixed_code":'''def count_vowels(s):
    """Count vowels in string."""
    vowels = "aeiouAEIOU"
    return sum(1 for c in s if c in vowels)
''',
        "test_code":'''from count_v import count_vowels


def test_lower():
    assert count_vowels("hello") == 2


def test_upper():
    assert count_vowels("HELLO") == 2


def test_mixed():
    assert count_vowels("HeLLo") == 2
''',
        "issue": "`count_vowels(\"HELLO\")` returns `0`.\n\nOnly checks lowercase vowels.\n\nRun: `python -m pytest tests/test_count_v.py`",
        "scripted_fix": {"path": "count_v.py", "old": 'vowels = "aeiou"', "new": 'vowels = "aeiouAEIOU"'},
    },
    {
        "task_id": "bugfix_248",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "list_rm",
        "buggy_code":'''def remove_item(lst, item):
    """Remove item from list."""
    lst.remove(item)
    return lst
''',
        "fixed_code":'''def remove_item(lst, item):
    """Remove item from list, return new list."""
    result = lst.copy()
    if item in result:
        result.remove(item)
    return result
''',
        "test_code":'''from list_rm import remove_item


def test_basic():
    assert remove_item([1, 2, 3], 2) == [1, 3]


def test_not_found():
    assert remove_item([1, 2, 3], 4) == [1, 2, 3]


def test_no_mutation():
    original = [1, 2, 3]
    remove_item(original, 2)
    assert original == [1, 2, 3]
''',
        "issue": "`remove_item` mutates the input list.\n\nShould return a new list.\n\nRun: `python -m pytest tests/test_list_rm.py`",
        "scripted_fix": {"path": "list_rm.py", "old": "def remove_item(lst, item):\n    \"\"\"Remove item from list.\"\"\"\n    lst.remove(item)\n    return lst", "new": "def remove_item(lst, item):\n    \"\"\"Remove item from list, return new list.\"\"\"\n    result = lst.copy()\n    if item in result:\n        result.remove(item)\n    return result"},
    },
    {
        "task_id": "bugfix_249",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "list_chunk",
        "buggy_code":'''def chunk_list(lst, size):
    """Split list into chunks."""
    return [lst[i:i+size] for i in range(0, len(lst), size)]
''',
        "fixed_code":'''def chunk_list(lst, size):
    """Split list into chunks."""
    if size <= 0:
        return [lst]
    return [lst[i:i+size] for i in range(0, len(lst), size)]
''',
        "test_code":'''from list_chunk import chunk_list


def test_basic():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_exact():
    assert chunk_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_zero_size():
    result = chunk_list([1, 2, 3], 0)
    assert isinstance(result, list)
''',
        "issue": "`chunk_list([1, 2, 3], 0)` raises `ValueError`.\n\nShould handle zero size.\n\nRun: `python -m pytest tests/test_list_chunk.py`",
        "scripted_fix": {"path": "list_chunk.py", "old": "def chunk_list(lst, size):\n    \"\"\"Split list into chunks.\"\"\"\n    return [lst[i:i+size] for i in range(0, len(lst), size)]", "new": "def chunk_list(lst, size):\n    \"\"\"Split list into chunks.\"\"\"\n    if size <= 0:\n        return [lst]\n    return [lst[i:i+size] for i in range(0, len(lst), size)]"},
    },
    {
        "task_id": "bugfix_250",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "str_count",
        "buggy_code":'''def count_substring(text, sub):
    """Count occurrences of substring."""
    return text.count(sub)
''',
        "fixed_code":'''def count_substring(text, sub):
    """Count occurrences of substring."""
    if not text or not sub:
        return 0
    return text.count(sub)
''',
        "test_code":'''from str_count import count_substring


def test_basic():
    assert count_substring("hello world", "o") == 2


def test_not_found():
    assert count_substring("hello", "xyz") == 0


def test_empty():
    assert count_substring("", "a") == 0


def test_none():
    assert count_substring(None, "a") == 0
''',
        "issue": "`count_substring(None, \"a\")` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_str_count.py`",
        "scripted_fix": {"path": "str_count.py", "old": "def count_substring(text, sub):\n    \"\"\"Count occurrences of substring.\"\"\"\n    return text.count(sub)", "new": "def count_substring(text, sub):\n    \"\"\"Count occurrences of substring.\"\"\"\n    if not text or not sub:\n        return 0\n    return text.count(sub)"},
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
