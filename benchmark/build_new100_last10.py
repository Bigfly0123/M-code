"""Build last 10 tasks (bugfix_341-350)."""
import json
from pathlib import Path

TASKS = [
    {"task_id": "bugfix_341", "bug_type": "regex", "difficulty": "medium", "module": "isbn_check",
     "buggy_code": 'import re\n\ndef is_isbn(s):\n    """Check ISBN."""\n    return bool(re.match(r"\\d{10,13}", s))\n',
     "fixed_code": 'import re\n\ndef is_isbn(s):\n    """Check ISBN."""\n    digits = re.sub(r"[^\\d]", "", s)\n    return len(digits) in (10, 13)\n',
     "test_code": 'from isbn_check import is_isbn\n\ndef test_10():\n    assert is_isbn("0131103628") is True\n\ndef test_13():\n    assert is_isbn("978-0131103627") is True\n\ndef test_short():\n    assert is_isbn("123") is False\n',
     "issue": '`is_isbn("978-0131103627")` returns False.\n\nRun: `python -m pytest tests/test_isbn_check.py`'},

    {"task_id": "bugfix_342", "bug_type": "date_time", "difficulty": "medium", "module": "quarter_util",
     "buggy_code": 'def get_quarter(month):\n    """Get quarter (0-indexed)."""\n    return (month - 1) // 3\n',
     "fixed_code": 'def get_quarter(month):\n    """Get quarter (1-indexed)."""\n    if not 1 <= month <= 12:\n        return None\n    return (month - 1) // 3 + 1\n',
     "test_code": 'from quarter_util import get_quarter\n\ndef test_q1():\n    assert get_quarter(3) == 1\n\ndef test_q2():\n    assert get_quarter(4) == 2\n\ndef test_q4():\n    assert get_quarter(12) == 4\n\ndef test_invalid():\n    assert get_quarter(13) is None\n',
     "issue": '`get_quarter(3)` returns 0 instead of 1.\n\nRun: `python -m pytest tests/test_quarter_util.py`'},

    {"task_id": "bugfix_343", "bug_type": "nested_condition", "difficulty": "medium", "module": "bmi_util",
     "buggy_code": 'def bmi_category(bmi):\n    """Classify BMI."""\n    if bmi < 18.5:\n        return "underweight"\n    if bmi < 25:\n        return "normal"\n    if bmi < 30:\n        return "overweight"\n    return "obese"\n',
     "fixed_code": 'def bmi_category(bmi):\n    """Classify BMI."""\n    if bmi <= 0:\n        return None\n    if bmi < 18.5:\n        return "underweight"\n    if bmi < 25:\n        return "normal"\n    if bmi < 30:\n        return "overweight"\n    return "obese"\n',
     "test_code": 'from bmi_util import bmi_category\n\ndef test_normal():\n    assert bmi_category(22) == "normal"\n\ndef test_obese():\n    assert bmi_category(35) == "obese"\n\ndef test_negative():\n    assert bmi_category(-1) is None\n\ndef test_zero():\n    assert bmi_category(0) is None\n',
     "issue": '`bmi_category(-1)` returns "underweight" instead of None.\n\nRun: `python -m pytest tests/test_bmi_util.py`'},

    {"task_id": "bugfix_344", "bug_type": "type_conversion", "difficulty": "easy", "module": "bool_list",
     "buggy_code": 'def any_true(values):\n    """Check if any value is truthy."""\n    return any(values)\n\ndef all_true(values):\n    """Check if all values are truthy."""\n    return all(values)\n',
     "fixed_code": 'def any_true(values):\n    """Check if any value is truthy."""\n    return any(bool(v) for v in values)\n\ndef all_true(values):\n    """Check if all values are truthy."""\n    return all(bool(v) for v in values)\n',
     "test_code": 'from bool_list import any_true, all_true\n\ndef test_any():\n    assert any_true([0, False, "hello"]) is True\n\ndef test_all():\n    assert all_true([1, True, "yes"]) is True\n\ndef test_all_false():\n    assert all_true([0, "", False]) is False\n',
     "issue": '`all_true(["", "hello"])` returns True.\n\nRun: `python -m pytest tests/test_bool_list.py`'},

    {"task_id": "bugfix_345", "bug_type": "list_mutation", "difficulty": "medium", "module": "sort_util",
     "buggy_code": 'def sort_by_key(items, key):\n    """Sort list of dicts by key."""\n    return sorted(items, key=lambda x: x[key])\n',
     "fixed_code": 'def sort_by_key(items, key):\n    """Sort list of dicts by key."""\n    return sorted(items, key=lambda x: x.get(key, ""))\n',
     "test_code": 'from sort_util import sort_by_key\n\ndef test_basic():\n    r = sort_by_key([{"n": 2}, {"n": 1}], "n")\n    assert r[0]["n"] == 1\n\ndef test_missing_key():\n    r = sort_by_key([{"a": 2}, {"n": 1}], "n")\n    assert len(r) == 2\n',
     "issue": '`sort_by_key([{"a": 2}, {"n": 1}], "n")` raises KeyError.\n\nRun: `python -m pytest tests/test_sort_util.py`'},

    {"task_id": "bugfix_346", "bug_type": "off_by_one", "difficulty": "medium", "module": "matrix_idx",
     "buggy_code": 'def get_row(matrix, idx):\n    """Get row by index."""\n    return matrix[idx]\n\ndef get_col(matrix, idx):\n    """Get column by index."""\n    return [row[idx] for row in matrix]\n',
     "fixed_code": 'def get_row(matrix, idx):\n    """Get row by index."""\n    if not matrix or idx < 0 or idx >= len(matrix):\n        return []\n    return matrix[idx]\n\ndef get_col(matrix, idx):\n    """Get column by index."""\n    if not matrix or idx < 0 or idx >= len(matrix[0]):\n        return []\n    return [row[idx] for row in matrix]\n',
     "test_code": 'import pytest\nfrom matrix_idx import get_row, get_col\n\ndef test_row():\n    assert get_row([[1,2],[3,4]], 0) == [1,2]\n\ndef test_col():\n    assert get_col([[1,2],[3,4]], 1) == [2,4]\n\ndef test_out_row():\n    assert get_row([[1,2]], 5) == []\n\ndef test_out_col():\n    assert get_col([[1,2]], 5) == []\n',
     "issue": '`get_row([[1,2]], 5)` raises IndexError.\n\nRun: `python -m pytest tests/test_matrix_idx.py`'},

    {"task_id": "bugfix_347", "bug_type": "exception_handling", "difficulty": "easy", "module": "parse_util",
     "buggy_code": 'def parse_int_list(s):\n    """Parse comma-separated integers."""\n    return [int(x) for x in s.split(",")]\n',
     "fixed_code": 'def parse_int_list(s):\n    """Parse comma-separated integers."""\n    result = []\n    for x in s.split(","):\n        try:\n            result.append(int(x.strip()))\n        except ValueError:\n            continue\n    return result\n',
     "test_code": 'from parse_util import parse_int_list\n\ndef test_basic():\n    assert parse_int_list("1,2,3") == [1,2,3]\n\ndef test_spaces():\n    assert parse_int_list(" 1 , 2 , 3 ") == [1,2,3]\n\ndef test_invalid():\n    assert parse_int_list("1,abc,3") == [1,3]\n',
     "issue": '`parse_int_list("1,abc,3")` raises ValueError.\n\nRun: `python -m pytest tests/test_parse_util.py`'},

    {"task_id": "bugfix_348", "bug_type": "boundary_empty", "difficulty": "medium", "module": "lcp_util",
     "buggy_code": 'def longest_common_prefix(strs):\n    """Find longest common prefix."""\n    if not strs:\n        return ""\n    prefix = strs[0]\n    for s in strs[1:]:\n        while not s.startswith(prefix):\n            prefix = prefix[:-1]\n    return prefix\n',
     "fixed_code": 'def longest_common_prefix(strs):\n    """Find longest common prefix."""\n    if not strs:\n        return ""\n    prefix = strs[0]\n    for s in strs[1:]:\n        while prefix and not s.startswith(prefix):\n            prefix = prefix[:-1]\n    return prefix\n',
     "test_code": 'from lcp_util import longest_common_prefix\n\ndef test_basic():\n    assert longest_common_prefix(["flower","flow","flight"]) == "fl"\n\ndef test_none():\n    assert longest_common_prefix(["dog","cat"]) == ""\n\ndef test_empty():\n    assert longest_common_prefix([]) == ""\n',
     "issue": '`longest_common_prefix(["dog","cat"])` may infinite loop.\n\nRun: `python -m pytest tests/test_lcp_util.py`'},

    {"task_id": "bugfix_349", "bug_type": "multi_branch", "difficulty": "medium", "module": "leap_year",
     "buggy_code": 'def is_leap_year(year):\n    """Check leap year."""\n    return year % 4 == 0\n',
     "fixed_code": 'def is_leap_year(year):\n    """Check leap year."""\n    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n',
     "test_code": 'from leap_year import is_leap_year\n\ndef test_leap():\n    assert is_leap_year(2024) is True\n\ndef test_not():\n    assert is_leap_year(2023) is False\n\ndef test_century():\n    assert is_leap_year(1900) is False\n\ndef test_400():\n    assert is_leap_year(2000) is True\n',
     "issue": '`is_leap_year(1900)` returns True (century years need divisible by 400).\n\nRun: `python -m pytest tests/test_leap_year.py`'},

    {"task_id": "bugfix_350", "bug_type": "stateful_counter", "difficulty": "medium", "module": "id_gen",
     "buggy_code": 'class IDGenerator:\n    _counter = 0\n\n    def next(self):\n        """Generate next ID."""\n        self._counter += 1\n        return self._counter\n',
     "fixed_code": 'class IDGenerator:\n    def __init__(self, start=0):\n        self._counter = start\n\n    def next(self):\n        """Generate next ID."""\n        self._counter += 1\n        return self._counter\n',
     "test_code": 'from id_gen import IDGenerator\n\ndef test_basic():\n    g = IDGenerator()\n    assert g.next() == 1\n    assert g.next() == 2\n\ndef test_separate():\n    g1 = IDGenerator()\n    g2 = IDGenerator()\n    g1.next()\n    assert g2.next() == 1\n',
     "issue": 'Two IDGenerator instances share counter.\n`g1.next()` then `g2.next()` returns 2 instead of 1.\n\nRun: `python -m pytest tests/test_id_gen.py`'},
]


def build_task_dir(root, task):
    task_dir = root / task["task_id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = task_dir / "repo"
    repo_dir.mkdir(exist_ok=True)
    (repo_dir / f"{task['module']}.py").write_text(task["buggy_code"], encoding="utf-8")
    tests_dir = repo_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    test_filename = f"test_{task['module']}.py"
    (tests_dir / test_filename).write_text(task["test_code"], encoding="utf-8")
    (task_dir / "issue.md").write_text(task["issue"], encoding="utf-8")
    meta = {
        "task_id": task["task_id"], "bug_type": task["bug_type"], "language": "python",
        "test_command": f"python -m pytest tests/{test_filename}",
        "target_files": [f"{task['module']}.py"], "difficulty": task["difficulty"],
        "timeout": 30,
        "scripted_fix": {"path": f"{task['module']}.py", "old": task["buggy_code"].strip(), "new": task["fixed_code"].strip()},
    }
    (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    print(f"Building {len(TASKS)} final tasks...")
    for task in TASKS:
        build_task_dir(tasks_root, task)
        print(f"  {task['task_id']}: {task['bug_type']}")

    all_new = sorted([p.name for p in tasks_root.iterdir()
                     if p.is_dir() and p.name.startswith("bugfix_")
                     and int(p.name.split("_")[1]) >= 251])
    splits_dir = root / "outputs" / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    (splits_dir / "new100_heldout_tasks.txt").write_text("\n".join(all_new) + "\n", encoding="utf-8")
    print(f"\nTotal new100 tasks: {len(all_new)}")


if __name__ == "__main__":
    main()
