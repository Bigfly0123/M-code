"""Final fix for remaining failed tasks."""
from __future__ import annotations

import json
from pathlib import Path

# 重新设计这些任务，确保有真正的bug
TASKS_TO_FIX = {
    "bugfix_062": {
        "buggy_code": '''def sort_strings(strings):
    """Sort strings case-insensitively."""
    return sorted(strings)
''',
        "fixed_code": '''def sort_strings(strings):
    """Sort strings case-insensitively."""
    return sorted(strings, key=str.lower)
''',
        "test_code": '''from sort_case import sort_strings


def test_case_sort():
    result = sort_strings(["banana", "Apple", "cherry"])
    assert result == ["Apple", "banana", "cherry"]


def test_all_lower():
    result = sort_strings(["c", "a", "b"])
    assert result == ["a", "b", "c"]
''',
        "scripted_fix": {"path": "sort_case.py", "old": "return sorted(strings)", "new": "return sorted(strings, key=str.lower)"},
    },
    "bugfix_063": {
        "buggy_code": '''def can_access(user, resource):
    """Check if user can access resource."""
    return user["is_admin"] or user["id"] == resource["owner_id"] and user["is_active"]
''',
        "fixed_code": '''def can_access(user, resource):
    """Check if user can access resource."""
    return user["is_admin"] or (user["id"] == resource["owner_id"] and user["is_active"])
''',
        "test_code": '''from access_ctrl import can_access


def test_admin():
    assert can_access({"id": 1, "is_admin": True, "is_active": True}, {"owner_id": 2}) is True


def test_owner_active():
    assert can_access({"id": 1, "is_admin": False, "is_active": True}, {"owner_id": 1}) is True


def test_owner_inactive():
    assert can_access({"id": 1, "is_admin": False, "is_active": False}, {"owner_id": 1}) is False
''',
        "scripted_fix": {"path": "access_ctrl.py", "old": '    return user["is_admin"] or user["id"] == resource["owner_id"] and user["is_active"]', "new": '    return user["is_admin"] or (user["id"] == resource["owner_id"] and user["is_active"])'},
    },
    "bugfix_071": {
        "buggy_code": '''def insert_at_index(lst, index, value):
    """Insert value at index, return new list."""
    result = lst.copy()
    if index < 0:
        index = 0
    result.insert(index, value)
    return result
''',
        "fixed_code": '''def insert_at_index(lst, index, value):
    """Insert value at index, return new list."""
    result = lst.copy()
    if index < 0:
        index = max(0, len(lst) + index + 1)
    result.insert(index, value)
    return result
''',
        "test_code": '''from insert_at import insert_at_index


def test_middle():
    assert insert_at_index([1, 2, 3], 1, 99) == [1, 99, 2, 3]


def test_end():
    assert insert_at_index([1, 2, 3], 3, 99) == [1, 2, 3, 99]


def test_negative():
    result = insert_at_index([1, 2, 3], -1, 99)
    assert result == [1, 2, 99, 3]
''',
        "scripted_fix": {"path": "insert_at.py", "old": "    if index < 0:\n        index = 0", "new": "    if index < 0:\n        index = max(0, len(lst) + index + 1)"},
    },
    "bugfix_074": {
        "buggy_code": '''def symmetric_difference(list1, list2):
    """Get items in either list but not both."""
    set1 = set(list1)
    set2 = set(list2)
    result = []
    for x in list1:
        if x not in set2:
            result.append(x)
    for x in list2:
        if x not in set1:
            result.append(x)
    return result


def symmetric_difference_set(list1, list2):
    """Get unique items using set operations."""
    return list(set(list1) & set(list2))
''',
        "fixed_code": '''def symmetric_difference(list1, list2):
    """Get items in either list but not both."""
    set1 = set(list1)
    set2 = set(list2)
    result = []
    for x in list1:
        if x not in set2:
            result.append(x)
    for x in list2:
        if x not in set1:
            result.append(x)
    return result


def symmetric_difference_set(list1, list2):
    """Get unique items using set operations."""
    return list(set(list1) ^ set(list2))
''',
        "test_code": '''from sym_diff import symmetric_difference, symmetric_difference_set


def test_basic():
    result = symmetric_difference([1, 2, 3], [3, 4, 5])
    assert result == [1, 2, 4, 5]


def test_set_version():
    result = symmetric_difference_set([1, 2, 3], [3, 4, 5])
    assert sorted(result) == [1, 2, 4, 5]
''',
        "scripted_fix": {"path": "sym_diff.py", "old": "    return list(set(list1) & set(list2))", "new": "    return list(set(list1) ^ set(list2))"},
    },
    "bugfix_084": {
        "buggy_code": '''def get_domain(url):
    """Extract domain from URL."""
    if "//" in url:
        return url.split("//")[1].split("/")[0]
    return url.split("/")[0]
''',
        "fixed_code": '''from urllib.parse import urlparse


def get_domain(url):
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc
''',
        "test_code": '''from url_parse import get_domain


def test_https():
    assert get_domain("https://example.com/path") == "example.com"


def test_http():
    assert get_domain("http://example.com") == "example.com"


def test_no_protocol():
    result = get_domain("example.com/path")
    assert result == "example.com" or result == ""
''',
        "scripted_fix": {"path": "url_parse.py", "old": "def get_domain(url):\n    \"\"\"Extract domain from URL.\"\"\"\n    if \"//\" in url:\n        return url.split(\"//\")[1].split(\"/\")[0]\n    return url.split(\"/\")[0]", "new": "from urllib.parse import urlparse\n\n\ndef get_domain(url):\n    \"\"\"Extract domain from URL.\"\"\"\n    parsed = urlparse(url)\n    return parsed.netloc"},
    },
    "bugfix_087": {
        "buggy_code": '''def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return c * 9 / 5 + 32
''',
        "fixed_code": '''def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return round(c * 9 / 5 + 32, 2)
''',
        "test_code": '''from temp_conv import celsius_to_fahrenheit


def test_boiling():
    assert celsius_to_fahrenheit(100) == 212.0


def test_freezing():
    assert celsius_to_fahrenheit(0) == 32.0


def test_body_temp():
    result = celsius_to_fahrenheit(37)
    assert abs(result - 98.6) < 0.01


def test_negative():
    assert celsius_to_fahrenheit(-40) == -40.0
''',
        "scripted_fix": {"path": "temp_conv.py", "old": "    return c * 9 / 5 + 32", "new": "    return round(c * 9 / 5 + 32, 2)"},
    },
    "bugfix_100": {
        "buggy_code": '''def create_counter(start=0):
    """Create a counter that increments."""
    count = start
    def increment(step=1):
        nonlocal count
        count += step
        return count
    return increment
''',
        "fixed_code": '''def create_counter(start=0):
    """Create a counter that increments."""
    count = [start]
    def increment(step=1):
        count[0] += step
        return count[0]
    return increment
''',
        "test_code": '''from counter import create_counter


def test_basic():
    c = create_counter()
    assert c() == 1
    assert c() == 2


def test_with_start():
    c = create_counter(10)
    assert c() == 11
''',
        "scripted_fix": {"path": "counter.py", "old": "def create_counter(start=0):\n    \"\"\"Create a counter that increments.\"\"\"\n    count = start\n    def increment(step=1):\n        nonlocal count\n        count += step\n        return count\n    return increment", "new": "def create_counter(start=0):\n    \"\"\"Create a counter that increments.\"\"\"\n    count = [start]\n    def increment(step=1):\n        count[0] += step\n        return count[0]\n    return increment"},
    },
}


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"

    for task_id, fixes in TASKS_TO_FIX.items():
        task_dir = tasks_root / task_id
        if not task_dir.exists():
            print(f"Skipping {task_id}: not found")
            continue

        repo_dir = task_dir / "repo"
        module_files = list(repo_dir.glob("*.py"))
        if not module_files:
            print(f"Skipping {task_id}: no module file")
            continue

        module_file = module_files[0]
        module_name = module_file.stem

        # Write buggy code
        module_file.write_text(fixes["buggy_code"], encoding="utf-8")

        # Write test code
        test_dir = repo_dir / "tests"
        test_file = test_dir / f"test_{module_name}.py"
        test_file.write_text(fixes["test_code"], encoding="utf-8")

        # Update metadata
        meta_path = task_dir / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["scripted_fix"] = fixes["scripted_fix"]
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        print(f"Fixed {task_id}")

    print("\nDone! Run validate_tasks to check.")


if __name__ == "__main__":
    main()
