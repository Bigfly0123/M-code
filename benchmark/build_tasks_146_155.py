"""Generate benchmark tasks bugfix_146 .. bugfix_200.

Target: 55 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # Continue with more simple tasks
    {
        "task_id": "bugfix_146",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "avg_list",
        "buggy_code":'''def calculate_average(lst):
    """Calculate average of list."""
    return sum(lst) / len(lst)
''',
        "fixed_code":'''def calculate_average(lst):
    """Calculate average of list."""
    if not lst:
        return 0.0
    return sum(lst) / len(lst)
''',
        "test_code":'''from avg_list import calculate_average


def test_basic():
    assert calculate_average([1, 2, 3]) == 2.0


def test_empty():
    assert calculate_average([]) == 0.0


def test_single():
    assert calculate_average([5]) == 5.0
''',
        "issue": "`calculate_average([])` raises `ZeroDivisionError`.\n\nShould handle empty list.\n\nRun: `python -m pytest tests/test_avg_list.py`",
        "scripted_fix": {"path": "avg_list.py", "old": "def calculate_average(lst):\n    \"\"\"Calculate average of list.\"\"\"\n    return sum(lst) / len(lst)", "new": "def calculate_average(lst):\n    \"\"\"Calculate average of list.\"\"\"\n    if not lst:\n        return 0.0\n    return sum(lst) / len(lst)"},
    },
    {
        "task_id": "bugfix_147",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_replace",
        "buggy_code":'''def replace_char(text, old, new):
    """Replace character in text."""
    return text.replace(old, new)
''',
        "fixed_code":'''def replace_char(text, old, new):
    """Replace character in text."""
    if text is None:
        return ""
    return text.replace(old, new)
''',
        "test_code":'''from safe_replace import replace_char


def test_basic():
    assert replace_char("hello", "l", "r") == "herro"


def test_none():
    assert replace_char(None, "a", "b") == ""


def test_empty():
    assert replace_char("", "a", "b") == ""
''',
        "issue": "`replace_char(None, \"a\", \"b\")` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_replace.py`",
        "scripted_fix": {"path": "safe_replace.py", "old": "def replace_char(text, old, new):\n    \"\"\"Replace character in text.\"\"\"\n    return text.replace(old, new)", "new": "def replace_char(text, old, new):\n    \"\"\"Replace character in text.\"\"\"\n    if text is None:\n        return \"\"\n    return text.replace(old, new)"},
    },
    {
        "task_id": "bugfix_148",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "count_list",
        "buggy_code":'''def count_items(lst):
    """Count occurrences of each item."""
    counts = {}
    for item in lst:
        counts[item] += 1
    return counts
''',
        "fixed_code":'''def count_items(lst):
    """Count occurrences of each item."""
    counts = {}
    for item in lst:
        counts[item] = counts.get(item, 0) + 1
    return counts
''',
        "test_code":'''from count_list import count_items


def test_basic():
    assert count_items(["a", "b", "a"]) == {"a": 2, "b": 1}


def test_empty():
    assert count_items([]) == {}


def test_single():
    assert count_items(["a"]) == {"a": 1}
''',
        "issue": "`count_items([\"a\", \"b\", \"a\"])` raises `KeyError`.\n\nShould use `.get()` for missing keys.\n\nRun: `python -m pytest tests/test_count_list.py`",
        "scripted_fix": {"path": "count_list.py", "old": "counts[item] += 1", "new": "counts[item] = counts.get(item, 0) + 1"},
    },
    {
        "task_id": "bugfix_149",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "last_n",
        "buggy_code":'''def get_last_n(lst, n):
    """Get last n items."""
    return lst[-n:]
''',
        "fixed_code":'''def get_last_n(lst, n):
    """Get last n items."""
    if n <= 0:
        return []
    return lst[-n:]
''',
        "test_code":'''from last_n import get_last_n


def test_basic():
    assert get_last_n([1, 2, 3, 4, 5], 3) == [3, 4, 5]


def test_all():
    assert get_last_n([1, 2, 3], 5) == [1, 2, 3]


def test_zero():
    assert get_last_n([1, 2, 3], 0) == []
''',
        "issue": "`get_last_n([1, 2, 3], 0)` returns `[1, 2, 3]` instead of `[]`.\n\nShould handle n=0.\n\nRun: `python -m pytest tests/test_last_n.py`",
        "scripted_fix": {"path": "last_n.py", "old": "def get_last_n(lst, n):\n    \"\"\"Get last n items.\"\"\"\n    return lst[-n:]", "new": "def get_last_n(lst, n):\n    \"\"\"Get last n items.\"\"\"\n    if n <= 0:\n        return []\n    return lst[-n:]"},
    },
    {
        "task_id": "bugfix_150",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "unique_list",
        "buggy_code":'''def get_unique(lst):
    """Get unique items."""
    return list(set(lst))
''',
        "fixed_code":'''def get_unique(lst):
    """Get unique items preserving order."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
''',
        "test_code":'''from unique_list import get_unique


def test_basic():
    assert get_unique([1, 2, 2, 3, 3, 3]) == [1, 2, 3]


def test_order():
    assert get_unique([3, 1, 2, 1, 3]) == [3, 1, 2]


def test_empty():
    assert get_unique([]) == []
''',
        "issue": "`get_unique([3, 1, 2, 1, 3])` doesn't preserve order.\n\n`set()` doesn't maintain insertion order.\n\nRun: `python -m pytest tests/test_unique_list.py`",
        "scripted_fix": {"path": "unique_list.py", "old": "def get_unique(lst):\n    \"\"\"Get unique items.\"\"\"\n    return list(set(lst))", "new": "def get_unique(lst):\n    \"\"\"Get unique items preserving order.\"\"\"\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result"},
    },
    # Add more tasks to reach 200
    {
        "task_id": "bugfix_151",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_lower",
        "buggy_code":'''def to_lower(text):
    """Convert to lowercase."""
    return text.lower()
''',
        "fixed_code":'''def to_lower(text):
    """Convert to lowercase."""
    if text is None:
        return ""
    return text.lower()
''',
        "test_code":'''from safe_lower import to_lower


def test_basic():
    assert to_lower("HELLO") == "hello"


def test_none():
    assert to_lower(None) == ""


def test_empty():
    assert to_lower("") == ""
''',
        "issue": "`to_lower(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_lower.py`",
        "scripted_fix": {"path": "safe_lower.py", "old": "def to_lower(text):\n    \"\"\"Convert to lowercase.\"\"\"\n    return text.lower()", "new": "def to_lower(text):\n    \"\"\"Convert to lowercase.\"\"\"\n    if text is None:\n        return \"\"\n    return text.lower()"},
    },
    {
        "task_id": "bugfix_152",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "flatten_dict",
        "buggy_code":'''def flatten(d, parent_key="", sep="."):
    """Flatten nested dict."""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
''',
        "fixed_code":'''def flatten(d, parent_key="", sep="."):
    """Flatten nested dict."""
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten(d, sep="."):
    """Unflatten dict."""
    result = {}
    for key, value in d.items():
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result
''',
        "test_code":'''from flatten_dict import flatten


def test_flat():
    assert flatten({"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_nested():
    assert flatten({"a": {"b": 1}}) == {"a.b": 1}


def test_deep():
    assert flatten({"a": {"b": {"c": 1}}}) == {"a.b.c": 1}
''',
        "issue": "Tests expect `unflatten` function that doesn't exist.\n\nRun: `python -m pytest tests/test_flatten_dict.py`",
        "scripted_fix": {"path": "flatten_dict.py", "old": "    return dict(items)\n", "new": "    return dict(items)\n\n\ndef unflatten(d, sep=\".\"):\n    \"\"\"Unflatten dict.\"\"\"\n    result = {}\n    for key, value in d.items():\n        parts = key.split(sep)\n        current = result\n        for part in parts[:-1]:\n            if part not in current:\n                current[part] = {}\n            current = current[part]\n        current[parts[-1]] = value\n    return result\n"},
    },
    {
        "task_id": "bugfix_153",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "zip_list",
        "buggy_code":'''def zip_lists(keys, values):
    """Zip two lists into dict."""
    return dict(zip(keys, values))
''',
        "fixed_code":'''def zip_lists(keys, values):
    """Zip two lists into dict."""
    if not keys or not values:
        return {}
    return dict(zip(keys, values))
''',
        "test_code":'''from zip_list import zip_lists


def test_basic():
    assert zip_lists(["a", "b"], [1, 2]) == {"a": 1, "b": 2}


def test_empty_keys():
    assert zip_lists([], [1, 2]) == {}


def test_empty_values():
    assert zip_lists(["a", "b"], []) == {}
''',
        "issue": "Tests expect empty dict for empty inputs.\n\nRun: `python -m pytest tests/test_zip_list.py`",
        "scripted_fix": {"path": "zip_list.py", "old": "def zip_lists(keys, values):\n    \"\"\"Zip two lists into dict.\"\"\"\n    return dict(zip(keys, values))", "new": "def zip_lists(keys, values):\n    \"\"\"Zip two lists into dict.\"\"\"\n    if not keys or not values:\n        return {}\n    return dict(zip(keys, values))"},
    },
    {
        "task_id": "bugfix_154",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_split",
        "buggy_code":'''def split_words(text):
    """Split text into words."""
    return text.split()
''',
        "fixed_code":'''def split_words(text):
    """Split text into words."""
    if not text:
        return []
    return text.split()
''',
        "test_code":'''from safe_split import split_words


def test_basic():
    assert split_words("hello world") == ["hello", "world"]


def test_empty():
    assert split_words("") == []


def test_none():
    assert split_words(None) == []
''',
        "issue": "`split_words(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_split.py`",
        "scripted_fix": {"path": "safe_split.py", "old": "def split_words(text):\n    \"\"\"Split text into words.\"\"\"\n    return text.split()", "new": "def split_words(text):\n    \"\"\"Split text into words.\"\"\"\n    if not text:\n        return []\n    return text.split()"},
    },
    {
        "task_id": "bugfix_155",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "clamp_val",
        "buggy_code":'''def clamp(value, min_val, max_val):
    """Clamp value to range."""
    return max(min_val, min(value, max_val))
''',
        "fixed_code":'''def clamp(value, min_val, max_val):
    """Clamp value to range."""
    return max(min_val, min(value, max_val))


def is_in_range(value, min_val, max_val):
    """Check if value is in range."""
    return min_val <= value <= max_val
''',
        "test_code":'''from clamp_val import clamp


def test_in_range():
    assert clamp(5, 1, 10) == 5


def test_below():
    assert clamp(0, 1, 10) == 1


def test_above():
    assert clamp(15, 1, 10) == 10
''',
        "issue": "Tests pass. Need to add `is_in_range` function.\n\nRun: `python -m pytest tests/test_clamp_val.py`",
        "scripted_fix": {"path": "clamp_val.py", "old": "    return max(min_val, min(value, max_val))\n", "new": "    return max(min_val, min(value, max_val))\n\n\ndef is_in_range(value, min_val, max_val):\n    \"\"\"Check if value is in range.\"\"\"\n    return min_val <= value <= max_val\n"},
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
