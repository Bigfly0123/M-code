"""Generate more held-out tasks (bugfix_219-250)."""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # More boundary_condition
    {
        "task_id": "bugfix_219",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "level_check",
        "buggy_code": '''def is_passing_level(score, threshold):
    """Check if score meets passing level."""
    return score > threshold
''',
        "fixed_code": '''def is_passing_level(score, threshold):
    """Check if score meets passing level."""
    return score >= threshold
''',
        "test_code": '''from level_check import is_passing_level


def test_above():
    assert is_passing_level(80, 70) is True


def test_at_threshold():
    assert is_passing_level(70, 70) is True


def test_below():
    assert is_passing_level(60, 70) is False
''',
        "issue": "`is_passing_level(70, 70)` should return `True` but returns `False`.\n\nBoundary error: uses `>` instead of `>=`.\n\nRun: `python -m pytest tests/test_level_check.py`",
        "scripted_fix": {"path": "level_check.py", "old": "return score > threshold", "new": "return score >= threshold"},
    },
    # More type_conversion
    {
        "task_id": "bugfix_220",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "str_len",
        "buggy_code": '''def total_length(str1, str2):
    """Calculate total length of two strings."""
    return str1 + str2
''',
        "fixed_code": '''def total_length(str1, str2):
    """Calculate total length of two strings."""
    return len(str1) + len(str2)
''',
        "test_code": '''from str_len import total_length


def test_basic():
    assert total_length("hello", "world") == 10


def test_empty():
    assert total_length("", "") == 0
''',
        "issue": "`total_length(\"hello\", \"world\")` returns `\"helloworld\"` instead of `10`.\n\nShould return length, not concatenation.\n\nRun: `python -m pytest tests/test_str_len.py`",
        "scripted_fix": {"path": "str_len.py", "old": "return str1 + str2", "new": "return len(str1) + len(str2)"},
    },
    # More dict_key
    {
        "task_id": "bugfix_221",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "student_grade",
        "buggy_code": '''def get_grade(student, course):
    """Get student grade for course."""
    return student["grades"][course]
''',
        "fixed_code": '''def get_grade(student, course, default="N/A"):
    """Get student grade for course."""
    return student.get("grades", {}).get(course, default)
''',
        "test_code": '''from student_grade import get_grade


def test_existing():
    assert get_grade({"grades": {"math": "A"}}, "math") == "A"


def test_missing_course():
    assert get_grade({"grades": {}}, "math") == "N/A"


def test_missing_grades():
    assert get_grade({}, "math") == "N/A"
''',
        "issue": "`get_grade({}, \"math\")` raises `KeyError`.\n\nShould handle missing keys.\n\nRun: `python -m pytest tests/test_student_grade.py`",
        "scripted_fix": {"path": "student_grade.py", "old": 'return student["grades"][course]', "new": 'return student.get("grades", {}).get(course, default)'},
    },
    # More off_by_one
    {
        "task_id": "bugfix_222",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "window_slide",
        "buggy_code": '''def get_window(data, center, radius):
    """Get data window around center."""
    start = center - radius
    end = center + radius - 1
    return data[start:end]
''',
        "fixed_code": '''def get_window(data, center, radius):
    """Get data window around center."""
    start = max(0, center - radius)
    end = min(len(data), center + radius + 1)
    return data[start:end]
''',
        "test_code": '''from window_slide import get_window


def test_center():
    assert get_window([1, 2, 3, 4, 5], 2, 1) == [2, 3, 4]


def test_start():
    assert get_window([1, 2, 3, 4, 5], 0, 1) == [1, 2]
''',
        "issue": "`get_window([1,2,3,4,5], 2, 1)` returns `[2, 3]` instead of `[2, 3, 4]`.\n\nOff-by-one error.\n\nRun: `python -m pytest tests/test_window_slide.py`",
        "scripted_fix": {"path": "window_slide.py", "old": "    start = center - radius\n    end = center + radius - 1\n    return data[start:end]", "new": "    start = max(0, center - radius)\n    end = min(len(data), center + radius + 1)\n    return data[start:end]"},
    },
    # More none_handling
    {
        "task_id": "bugfix_223",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_upper",
        "buggy_code": '''def to_upper(text):
    """Convert text to uppercase."""
    return text.upper()
''',
        "fixed_code": '''def to_upper(text):
    """Convert text to uppercase."""
    if text is None:
        return ""
    return text.upper()
''',
        "test_code": '''from safe_upper import to_upper


def test_normal():
    assert to_upper("hello") == "HELLO"


def test_none():
    assert to_upper(None) == ""


def test_empty():
    assert to_upper("") == ""
''',
        "issue": "`to_upper(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_upper.py`",
        "scripted_fix": {"path": "safe_upper.py", "old": "def to_upper(text):\n    \"\"\"Convert text to uppercase.\"\"\"\n    return text.upper()", "new": "def to_upper(text):\n    \"\"\"Convert text to uppercase.\"\"\"\n    if text is None:\n        return \"\"\n    return text.upper()"},
    },
    # More simple_algorithm
    {
        "task_id": "bugfix_224",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "max_finder",
        "buggy_code": '''def find_max(lst):
    """Find maximum value."""
    if not lst:
        return None
    max_val = 0
    for item in lst:
        if item > max_val:
            max_val = item
    return max_val
''',
        "fixed_code": '''def find_max(lst):
    """Find maximum value."""
    if not lst:
        return None
    max_val = lst[0]
    for item in lst[1:]:
        if item > max_val:
            max_val = item
    return max_val
''',
        "test_code": '''from max_finder import find_max


def test_positive():
    assert find_max([1, 3, 2]) == 3


def test_negative():
    assert find_max([-5, -2, -8]) == -2


def test_empty():
    assert find_max([]) is None
''',
        "issue": "`find_max([-5, -2, -8])` returns `0` instead of `-2`.\n\nInitial max_val should be `lst[0]`, not `0`.\n\nRun: `python -m pytest tests/test_max_finder.py`",
        "scripted_fix": {"path": "max_finder.py", "old": "    max_val = 0\n    for item in lst:", "new": "    max_val = lst[0]\n    for item in lst[1:]:"},
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
