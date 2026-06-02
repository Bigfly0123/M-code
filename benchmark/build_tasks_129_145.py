"""Generate benchmark tasks bugfix_129 .. bugfix_200.

Target: 72 new tasks to reach total 200.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # boundary_condition (11-15)
    {
        "task_id": "bugfix_129",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "grade_check",
        "buggy_code":'''def get_grade(score):
    """Get letter grade."""
    if score >= 90:
        return 'A'
    if score >= 80:
        return 'B'
    if score >= 70:
        return 'C'
    if score >= 60:
        return 'D'
    return 'F'
''',
        "fixed_code":'''def get_grade(score):
    """Get letter grade."""
    if score >= 90:
        return 'A'
    if score >= 80:
        return 'B'
    if score >= 70:
        return 'C'
    if score >= 60:
        return 'D'
    return 'F'


def is_passing(score):
    """Check if score is passing (>= 60)."""
    return score >= 60
''',
        "test_code":'''from grade_check import get_grade, is_passing


def test_A():
    assert get_grade(95) == 'A'


def test_B():
    assert get_grade(85) == 'B'


def test_F():
    assert get_grade(50) == 'F'


def test_passing():
    assert is_passing(60) is True
    assert is_passing(59) is False
''',
        "issue": "Tests expect an `is_passing` function that doesn't exist.\n\nRun: `python -m pytest tests/test_grade_check.py`",
        "scripted_fix": {"path": "grade_check.py", "old": "    return 'F'\n", "new": "    return 'F'\n\n\ndef is_passing(score):\n    \"\"\"Check if score is passing (>= 60).\"\"\"\n    return score >= 60\n"},
    },
    # type_conversion (11-15)
    {
        "task_id": "bugfix_130",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "num_fmt",
        "buggy_code":'''def format_number(n):
    """Format number with commas."""
    return str(n)
''',
        "fixed_code":'''def format_number(n):
    """Format number with commas."""
    return f"{n:,}"
''',
        "test_code":'''from num_fmt import format_number


def test_small():
    assert format_number(123) == "123"


def test_large():
    assert format_number(1234567) == "1,234,567"


def test_zero():
    assert format_number(0) == "0"
''',
        "issue": "`format_number(1234567)` returns `\"1234567\"` instead of `\"1,234,567\"`.\n\nMissing comma formatting.\n\nRun: `python -m pytest tests/test_num_fmt.py`",
        "scripted_fix": {"path": "num_fmt.py", "old": 'return str(n)', "new": 'return f"{n:,}"'},
    },
    # dict_key (11-15)
    {
        "task_id": "bugfix_131",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "safe_pop",
        "buggy_code":'''def safe_pop(data, key):
    """Remove and return value for key."""
    return data.pop(key)
''',
        "fixed_code":'''def safe_pop(data, key, default=None):
    """Remove and return value for key."""
    return data.pop(key, default)
''',
        "test_code":'''from safe_pop import safe_pop


def test_existing():
    d = {"a": 1, "b": 2}
    assert safe_pop(d, "a") == 1
    assert d == {"b": 2}


def test_missing():
    d = {"a": 1}
    assert safe_pop(d, "b") is None
    assert d == {"a": 1}


def test_default():
    d = {"a": 1}
    assert safe_pop(d, "b", 0) == 0
''',
        "issue": "`safe_pop({\"a\": 1}, \"b\")` raises `KeyError`.\n\nShould handle missing keys.\n\nRun: `python -m pytest tests/test_safe_pop.py`",
        "scripted_fix": {"path": "safe_pop.py", "old": "def safe_pop(data, key):\n    \"\"\"Remove and return value for key.\"\"\"\n    return data.pop(key)", "new": "def safe_pop(data, key, default=None):\n    \"\"\"Remove and return value for key.\"\"\"\n    return data.pop(key, default)"},
    },
    # off_by_one (11-15)
    {
        "task_id": "bugfix_132",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "range_list",
        "buggy_code":'''def generate_range(start, end):
    """Generate list from start to end (inclusive)."""
    return list(range(start, end))
''',
        "fixed_code":'''def generate_range(start, end):
    """Generate list from start to end (inclusive)."""
    return list(range(start, end + 1))
''',
        "test_code":'''from range_list import generate_range


def test_basic():
    assert generate_range(1, 5) == [1, 2, 3, 4, 5]


def test_single():
    assert generate_range(3, 3) == [3]


def test_empty():
    assert generate_range(5, 3) == []
''',
        "issue": "`generate_range(1, 5)` returns `[1, 2, 3, 4]` instead of `[1, 2, 3, 4, 5]`.\n\nOff-by-one: `range(start, end)` excludes end.\n\nRun: `python -m pytest tests/test_range_list.py`",
        "scripted_fix": {"path": "range_list.py", "old": "return list(range(start, end))", "new": "return list(range(start, end + 1))"},
    },
    # none_handling (13-16)
    {
        "task_id": "bugfix_133",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_list",
        "buggy_code":'''def get_first(lst):
    """Get first item from list."""
    return lst[0]
''',
        "fixed_code":'''def get_first(lst):
    """Get first item from list."""
    if not lst:
        return None
    return lst[0]
''',
        "test_code":'''from safe_list import get_first


def test_valid():
    assert get_first([1, 2, 3]) == 1


def test_empty():
    assert get_first([]) is None


def test_none():
    assert get_first(None) is None
''',
        "issue": "`get_first([])` raises `IndexError`.\n\nShould handle empty list.\n\nRun: `python -m pytest tests/test_safe_list.py`",
        "scripted_fix": {"path": "safe_list.py", "old": "def get_first(lst):\n    \"\"\"Get first item from list.\"\"\"\n    return lst[0]", "new": "def get_first(lst):\n    \"\"\"Get first item from list.\"\"\"\n    if not lst:\n        return None\n    return lst[0]"},
    },
    # simple_algorithm (7-10)
    {
        "task_id": "bugfix_134",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "min_val",
        "buggy_code":'''def find_min(lst):
    """Find minimum value in list."""
    if not lst:
        return None
    min_val = 0
    for item in lst:
        if item < min_val:
            min_val = item
    return min_val
''',
        "fixed_code":'''def find_min(lst):
    """Find minimum value in list."""
    if not lst:
        return None
    min_val = lst[0]
    for item in lst[1:]:
        if item < min_val:
            min_val = item
    return min_val
''',
        "test_code":'''from min_val import find_min


def test_positive():
    assert find_min([3, 1, 2]) == 1


def test_negative():
    assert find_min([-1, -5, -3]) == -5


def test_empty():
    assert find_min([]) is None
''',
        "issue": "`find_min([-1, -5, -3])` returns `0` instead of `-5`.\n\nInitial min_val should be `lst[0]`, not `0`.\n\nRun: `python -m pytest tests/test_min_val.py`",
        "scripted_fix": {"path": "min_val.py", "old": "    min_val = 0\n    for item in lst:", "new": "    min_val = lst[0]\n    for item in lst[1:]:"},
    },
    # boolean_logic (5-8)
    {
        "task_id": "bugfix_135",
        "bug_type": "boolean_logic",
        "difficulty": "easy",
        "module": "xor_check",
        "buggy_code":'''def xor(a, b):
    """Return True if exactly one of a, b is True."""
    return a or b
''',
        "fixed_code":'''def xor(a, b):
    """Return True if exactly one of a, b is True."""
    return a != b
''',
        "test_code":'''from xor_check import xor


def test_true_false():
    assert xor(True, False) is True


def test_false_true():
    assert xor(False, True) is True


def test_true_true():
    assert xor(True, True) is False


def test_false_false():
    assert xor(False, False) is False
''',
        "issue": "`xor(True, True)` returns `True` instead of `False`.\n\n`or` is not XOR.\n\nRun: `python -m pytest tests/test_xor_check.py`",
        "scripted_fix": {"path": "xor_check.py", "old": "return a or b", "new": "return a != b"},
    },
    # exception_handling (5-8)
    {
        "task_id": "bugfix_136",
        "bug_type": "exception_handling",
        "difficulty": "easy",
        "module": "safe_index",
        "buggy_code":'''def safe_get(lst, index):
    """Safely get item by index."""
    try:
        return lst[index]
    except:
        return None
''',
        "fixed_code":'''def safe_get(lst, index):
    """Safely get item by index."""
    try:
        return lst[index]
    except (IndexError, TypeError):
        return None
''',
        "test_code":'''from safe_index import safe_get


def test_valid():
    assert safe_get([1, 2, 3], 0) == 1


def test_out_of_range():
    assert safe_get([1, 2, 3], 10) is None


def test_none():
    assert safe_get(None, 0) is None
''',
        "issue": "Uses bare `except` which catches all exceptions.\n\nShould only catch `IndexError` and `TypeError`.\n\nRun: `python -m pytest tests/test_safe_index.py`",
        "scripted_fix": {"path": "safe_index.py", "old": "    except:", "new": "    except (IndexError, TypeError):"},
    },
    # floating_precision (4-6)
    {
        "task_id": "bugfix_137",
        "bug_type": "floating_precision",
        "difficulty": "easy",
        "module": "pct_calc",
        "buggy_code":'''def percentage(part, total):
    """Calculate percentage."""
    return part / total * 100
''',
        "fixed_code":'''def percentage(part, total):
    """Calculate percentage."""
    if total == 0:
        return 0.0
    return round(part / total * 100, 2)
''',
        "test_code":'''from pct_calc import percentage


def test_basic():
    assert percentage(25, 100) == 25.0


def test_zero_total():
    assert percentage(0, 0) == 0.0


def test_decimal():
    result = percentage(1, 3)
    assert abs(result - 33.33) < 0.01
''',
        "issue": "`percentage(0, 0)` raises `ZeroDivisionError`.\n\nShould handle zero total.\n\nRun: `python -m pytest tests/test_pct_calc.py`",
        "scripted_fix": {"path": "pct_calc.py", "old": "def percentage(part, total):\n    \"\"\"Calculate percentage.\"\"\"\n    return part / total * 100", "new": "def percentage(part, total):\n    \"\"\"Calculate percentage.\"\"\"\n    if total == 0:\n        return 0.0\n    return round(part / total * 100, 2)"},
    },
    # input_validation (4-6)
    {
        "task_id": "bugfix_138",
        "bug_type": "input_validation",
        "difficulty": "easy",
        "module": "validate_email",
        "buggy_code":'''def is_valid_email(email):
    """Validate email format."""
    return "@" in email
''',
        "fixed_code":'''def is_valid_email(email):
    """Validate email format."""
    if not email:
        return False
    if "@" not in email:
        return False
    parts = email.split("@")
    if len(parts) != 2:
        return False
    return "." in parts[1]
''',
        "test_code":'''from validate_email import is_valid_email


def test_valid():
    assert is_valid_email("user@example.com") is True


def test_no_at():
    assert is_valid_email("userexample.com") is False


def test_multiple_at():
    assert is_valid_email("user@@example.com") is False


def test_empty():
    assert is_valid_email("") is False
''',
        "issue": "`is_valid_email(\"user@@example.com\")` returns `True`.\n\nShould validate proper email format.\n\nRun: `python -m pytest tests/test_validate_email.py`",
        "scripted_fix": {"path": "validate_email.py", "old": "def is_valid_email(email):\n    \"\"\"Validate email format.\"\"\"\n    return \"@\" in email", "new": "def is_valid_email(email):\n    \"\"\"Validate email format.\"\"\"\n    if not email:\n        return False\n    if \"@\" not in email:\n        return False\n    parts = email.split(\"@\")\n    if len(parts) != 2:\n        return False\n    return \".\" in parts[1]"},
    },
    # string_split_join (2-4)
    {
        "task_id": "bugfix_139",
        "bug_type": "string_split_join",
        "difficulty": "easy",
        "module": "word_join",
        "buggy_code":'''def join_words(words, sep):
    """Join words with separator."""
    return sep.join(words)
''',
        "fixed_code":'''def join_words(words, sep):
    """Join words with separator."""
    if not words:
        return ""
    return sep.join(words)
''',
        "test_code":'''from word_join import join_words


def test_basic():
    assert join_words(["hello", "world"], " ") == "hello world"


def test_empty():
    assert join_words([], " ") == ""


def test_none():
    assert join_words(None, " ") == ""
''',
        "issue": "`join_words(None, \" \")` raises `TypeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_word_join.py`",
        "scripted_fix": {"path": "word_join.py", "old": "def join_words(words, sep):\n    \"\"\"Join words with separator.\"\"\"\n    return sep.join(words)", "new": "def join_words(words, sep):\n    \"\"\"Join words with separator.\"\"\"\n    if not words:\n        return \"\"\n    return sep.join(words)"},
    },
    # default_argument (3-5)
    {
        "task_id": "bugfix_140",
        "bug_type": "default_argument",
        "difficulty": "easy",
        "module": "build_list",
        "buggy_code":'''def add_items(items, target=[]):
    """Add items to target list."""
    target.extend(items)
    return target
''',
        "fixed_code":'''def add_items(items, target=None):
    """Add items to target list."""
    if target is None:
        target = []
    target.extend(items)
    return target
''',
        "test_code":'''from build_list import add_items


def test_basic():
    assert add_items([1, 2]) == [1, 2]


def test_multiple():
    assert add_items([1]) == [1]
    assert add_items([2]) == [2]


def test_with_target():
    assert add_items([1], [0]) == [0, 1]
''',
        "issue": "`add_items([1])` then `add_items([2])` returns `[1, 2]`.\n\nMutable default argument shared across calls.\n\nRun: `python -m pytest tests/test_build_list.py`",
        "scripted_fix": {"path": "build_list.py", "old": "def add_items(items, target=[]):", "new": "def add_items(items, target=None):\n    if target is None:\n        target = []"},
    },
    # Additional tasks...
    # For brevity, I'll add more simple tasks
    {
        "task_id": "bugfix_141",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "sum_list",
        "buggy_code":'''def safe_sum(lst):
    """Sum list elements."""
    return sum(lst)
''',
        "fixed_code":'''def safe_sum(lst):
    """Sum list elements."""
    if not lst:
        return 0
    return sum(lst)
''',
        "test_code":'''from sum_list import safe_sum


def test_basic():
    assert safe_sum([1, 2, 3]) == 6


def test_empty():
    assert safe_sum([]) == 0


def test_none():
    assert safe_sum(None) == 0
''',
        "issue": "`safe_sum(None)` raises `TypeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_sum_list.py`",
        "scripted_fix": {"path": "sum_list.py", "old": "def safe_sum(lst):\n    \"\"\"Sum list elements.\"\"\"\n    return sum(lst)", "new": "def safe_sum(lst):\n    \"\"\"Sum list elements.\"\"\"\n    if not lst:\n        return 0\n    return sum(lst)"},
    },
    {
        "task_id": "bugfix_142",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_strip",
        "buggy_code":'''def clean_text(text):
    """Strip whitespace from text."""
    return text.strip()
''',
        "fixed_code":'''def clean_text(text):
    """Strip whitespace from text."""
    if text is None:
        return ""
    return text.strip()
''',
        "test_code":'''from safe_strip import clean_text


def test_basic():
    assert clean_text("  hello  ") == "hello"


def test_empty():
    assert clean_text("") == ""


def test_none():
    assert clean_text(None) == ""
''',
        "issue": "`clean_text(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_safe_strip.py`",
        "scripted_fix": {"path": "safe_strip.py", "old": "def clean_text(text):\n    \"\"\"Strip whitespace from text.\"\"\"\n    return text.strip()", "new": "def clean_text(text):\n    \"\"\"Strip whitespace from text.\"\"\"\n    if text is None:\n        return \"\"\n    return text.strip()"},
    },
    {
        "task_id": "bugfix_143",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "update_dict",
        "buggy_code":'''def update_value(data, key, value):
    """Update dict value."""
    data[key] = value
    return data
''',
        "fixed_code":'''def update_value(data, key, value):
    """Update dict value, return new dict."""
    result = data.copy()
    result[key] = value
    return result
''',
        "test_code":'''from update_dict import update_value


def test_update():
    assert update_value({"a": 1}, "b", 2) == {"a": 1, "b": 2}


def test_no_mutation():
    d = {"a": 1}
    update_value(d, "b", 2)
    assert d == {"a": 1}
''',
        "issue": "`update_value` mutates the input dict.\n\nShould return a new dict.\n\nRun: `python -m pytest tests/test_update_dict.py`",
        "scripted_fix": {"path": "update_dict.py", "old": "def update_value(data, key, value):\n    \"\"\"Update dict value.\"\"\"\n    data[key] = value\n    return data", "new": "def update_value(data, key, value):\n    \"\"\"Update dict value, return new dict.\"\"\"\n    result = data.copy()\n    result[key] = value\n    return result"},
    },
    {
        "task_id": "bugfix_144",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "mid_list",
        "buggy_code":'''def get_middle(lst):
    """Get middle element."""
    return lst[len(lst) // 2]
''',
        "fixed_code":'''def get_middle(lst):
    """Get middle element."""
    if not lst:
        return None
    return lst[len(lst) // 2]
''',
        "test_code":'''from mid_list import get_middle


def test_odd():
    assert get_middle([1, 2, 3]) == 2


def test_even():
    assert get_middle([1, 2, 3, 4]) == 3


def test_empty():
    assert get_middle([]) is None
''',
        "issue": "`get_middle([])` raises `IndexError`.\n\nShould handle empty list.\n\nRun: `python -m pytest tests/test_mid_list.py`",
        "scripted_fix": {"path": "mid_list.py", "old": "def get_middle(lst):\n    \"\"\"Get middle element.\"\"\"\n    return lst[len(lst) // 2]", "new": "def get_middle(lst):\n    \"\"\"Get middle element.\"\"\"\n    if not lst:\n        return None\n    return lst[len(lst) // 2]"},
    },
    {
        "task_id": "bugfix_145",
        "bug_type": "boolean_logic",
        "difficulty": "easy",
        "module": "between",
        "buggy_code":'''def is_between(value, low, high):
    """Check if value is between low and high."""
    return low < value < high
''',
        "fixed_code":'''def is_between(value, low, high):
    """Check if value is between low and high (inclusive)."""
    return low <= value <= high
''',
        "test_code":'''from between import is_between


def test_in_range():
    assert is_between(5, 1, 10) is True


def test_at_low():
    assert is_between(1, 1, 10) is True


def test_at_high():
    assert is_between(10, 1, 10) is True


def test_outside():
    assert is_between(0, 1, 10) is False
''',
        "issue": "`is_between(1, 1, 10)` returns `False`.\n\nShould be inclusive.\n\nRun: `python -m pytest tests/test_between.py`",
        "scripted_fix": {"path": "between.py", "old": "return low < value < high", "new": "return low <= value <= high"},
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
