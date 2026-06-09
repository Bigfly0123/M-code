"""Generate held-out evaluation tasks (bugfix_201-250).

These tasks are completely separate from training data.
File names, function names, and bug types are varied.
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # ═══════════════════════════════════════════════════════
    # boundary_condition (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_201",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "sensor_read",
        "buggy_code": '''def is_valid_reading(value, min_val, max_val):
    """Check if sensor reading is within valid range."""
    return min_val < value < max_val
''',
        "fixed_code": '''def is_valid_reading(value, min_val, max_val):
    """Check if sensor reading is within valid range."""
    return min_val <= value <= max_val
''',
        "test_code":'''from sensor_read import is_valid_reading


def test_within_range():
    assert is_valid_reading(50, 0, 100) is True


def test_at_min():
    assert is_valid_reading(0, 0, 100) is True


def test_at_max():
    assert is_valid_reading(100, 0, 100) is True


def test_below_min():
    assert is_valid_reading(-1, 0, 100) is False
''',
        "issue": "Sensor readings at boundary values (0 or 100) are rejected as invalid.\n\n`is_valid_reading(0, 0, 100)` should return `True`.\n\nRun: `python -m pytest tests/test_sensor_read.py`",
        "scripted_fix": {"path": "sensor_read.py", "old": "return min_val < value < max_val", "new": "return min_val <= value <= max_val"},
    },
    {
        "task_id": "bugfix_202",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "seat_booking",
        "buggy_code": '''def is_valid_seat(row, col, max_row, max_col):
    """Check if seat position is valid."""
    return 0 < row <= max_row and 0 < col <= max_col
''',
        "fixed_code": '''def is_valid_seat(row, col, max_row, max_col):
    """Check if seat position is valid."""
    return 1 <= row <= max_row and 1 <= col <= max_col
''',
        "test_code":'''from seat_booking import is_valid_seat


def test_valid_seat():
    assert is_valid_seat(1, 1, 10, 5) is True


def test_last_seat():
    assert is_valid_seat(10, 5, 10, 5) is True


def test_zero_row():
    assert is_valid_seat(0, 1, 10, 5) is False
''',
        "issue": "Seat (1, 1) is rejected as invalid.\n\n`is_valid_seat(1, 1, 10, 5)` should return `True`.\n\nRun: `python -m pytest tests/test_seat_booking.py`",
        "scripted_fix": {"path": "seat_booking.py", "old": "return 0 < row <= max_row and 0 < col <= max_col", "new": "return 1 <= row <= max_row and 1 <= col <= max_col"},
    },
    # ═══════════════════════════════════════════════════════
    # type_conversion (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_203",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "order_total",
        "buggy_code":'''def calculate_total(price_str, quantity_str):
    """Calculate order total from string inputs."""
    return price_str * quantity_str
''',
        "fixed_code":'''def calculate_total(price_str, quantity_str):
    """Calculate order total from string inputs."""
    return float(price_str) * int(quantity_str)
''',
        "test_code":'''from order_total import calculate_total


def test_basic():
    assert calculate_total("9.99", "3") == 29.97


def test_single():
    assert calculate_total("5.50", "1") == 5.50
''',
        "issue": "`calculate_total(\"9.99\", \"3\")` returns `\"9.999.999.99\"` instead of `29.97`.\n\nString repetition instead of numeric multiplication.\n\nRun: `python -m pytest tests/test_order_total.py`",
        "scripted_fix": {"path": "order_total.py", "old": "return price_str * quantity_str", "new": "return float(price_str) * int(quantity_str)"},
    },
    {
        "task_id": "bugfix_204",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "config_value",
        "buggy_code":'''def get_timeout(config):
    """Get timeout value as integer."""
    return config["timeout"]
''',
        "fixed_code":'''def get_timeout(config):
    """Get timeout value as integer."""
    return int(config["timeout"])
''',
        "test_code":'''from config_value import get_timeout


def test_string_timeout():
    assert get_timeout({"timeout": "30"}) == 30


def test_int_timeout():
    assert get_timeout({"timeout": 30}) == 30
''',
        "issue": "`get_timeout({\"timeout\": \"30\"})` returns `\"30\"` instead of `30`.\n\nShould convert to integer.\n\nRun: `python -m pytest tests/test_config_value.py`",
        "scripted_fix": {"path": "config_value.py", "old": 'return config[\"timeout\"]', "new": 'return int(config[\"timeout\"])'},
    },
    # ═══════════════════════════════════════════════════════
    # dict_key (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_205",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "user_profile",
        "buggy_code":'''def get_display_name(user):
    """Get user display name."""
    return user["first_name"] + " " + user["last_name"]
''',
        "fixed_code":'''def get_display_name(user):
    """Get user display name."""
    return user.get("first_name", "") + " " + user.get("last_name", "")
''',
        "test_code":'''from user_profile import get_display_name


def test_full_name():
    assert get_display_name({"first_name": "John", "last_name": "Doe"}) == "John Doe"


def test_missing_last():
    assert get_display_name({"first_name": "John"}) == "John "


def test_empty():
    assert get_display_name({}) == " "
''',
        "issue": "`get_display_name({\"first_name\": \"John\"})` raises `KeyError`.\n\nShould handle missing keys.\n\nRun: `python -m pytest tests/test_user_profile.py`",
        "scripted_fix": {"path": "user_profile.py", "old": 'return user[\"first_name\"] + \" \" + user[\"last_name\"]', "new": 'return user.get(\"first_name\", \"\") + \" \" + user.get(\"last_name\", \"\")'},
    },
    {
        "task_id": "bugfix_206",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "settings_mgr",
        "buggy_code":'''def get_setting(settings, key, default=None):
    """Get setting value with default."""
    return settings[key]
''',
        "fixed_code":'''def get_setting(settings, key, default=None):
    """Get setting value with default."""
    return settings.get(key, default)
''',
        "test_code":'''from settings_mgr import get_setting


def test_existing():
    assert get_setting({"debug": True}, "debug") is True


def test_missing():
    assert get_setting({}, "debug") is None


def test_with_default():
    assert get_setting({}, "debug", False) is False
''',
        "issue": "`get_setting({}, \"debug\", False)` raises `KeyError`.\n\nShould return default value.\n\nRun: `python -m pytest tests/test_settings_mgr.py`",
        "scripted_fix": {"path": "settings_mgr.py", "old": "return settings[key]", "new": "return settings.get(key, default)"},
    },
    # ═══════════════════════════════════════════════════════
    # off_by_one (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_207",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "buffer_mgr",
        "buggy_code":'''def get_buffer_slice(buffer, start, length):
    """Get a slice of buffer."""
    return buffer[start:start + length - 1]
''',
        "fixed_code":'''def get_buffer_slice(buffer, start, length):
    """Get a slice of buffer."""
    return buffer[start:start + length]
''',
        "test_code":'''from buffer_mgr import get_buffer_slice


def test_basic():
    assert get_buffer_slice([1, 2, 3, 4, 5], 1, 3) == [2, 3, 4]


def test_from_start():
    assert get_buffer_slice([1, 2, 3], 0, 2) == [1, 2]
''',
        "issue": "`get_buffer_slice([1,2,3,4,5], 1, 3)` returns `[2, 3]` instead of `[2, 3, 4]`.\n\nOff-by-one error.\n\nRun: `python -m pytest tests/test_buffer_mgr.py`",
        "scripted_fix": {"path": "buffer_mgr.py", "old": "return buffer[start:start + length - 1]", "new": "return buffer[start:start + length]"},
    },
    {
        "task_id": "bugfix_208",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "page_util",
        "buggy_code":'''def get_page_items(items, page_num, page_size):
    """Get items for a specific page (1-indexed)."""
    start = (page_num - 1) * page_size
    end = start + page_size - 1
    return items[start:end]
''',
        "fixed_code":'''def get_page_items(items, page_num, page_size):
    """Get items for a specific page (1-indexed)."""
    start = (page_num - 1) * page_size
    end = start + page_size
    return items[start:end]
''',
        "test_code":'''from page_util import get_page_items


def test_first_page():
    assert get_page_items([1, 2, 3, 4, 5], 1, 2) == [1, 2]


def test_second_page():
    assert get_page_items([1, 2, 3, 4, 5], 2, 2) == [3, 4]


def test_last_page():
    assert get_page_items([1, 2, 3, 4, 5], 3, 2) == [5]
''',
        "issue": "`get_page_items([1,2,3,4,5], 1, 2)` returns `[1]` instead of `[1, 2]`.\n\nOff-by-one in end index.\n\nRun: `python -m pytest tests/test_page_util.py`",
        "scripted_fix": {"path": "page_util.py", "old": "end = start + page_size - 1", "new": "end = start + page_size"},
    },
    # ═══════════════════════════════════════════════════════
    # none_handling (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_209",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "text_proc",
        "buggy_code":'''def clean_text(text):
    """Clean and normalize text."""
    return text.strip().lower()
''',
        "fixed_code":'''def clean_text(text):
    """Clean and normalize text."""
    if text is None:
        return ""
    return text.strip().lower()
''',
        "test_code":'''from text_proc import clean_text


def test_normal():
    assert clean_text("  Hello  ") == "hello"


def test_none():
    assert clean_text(None) == ""


def test_empty():
    assert clean_text("") == ""
''',
        "issue": "`clean_text(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_text_proc.py`",
        "scripted_fix": {"path": "text_proc.py", "old": "def clean_text(text):\n    \"\"\"Clean and normalize text.\"\"\"\n    return text.strip().lower()", "new": "def clean_text(text):\n    \"\"\"Clean and normalize text.\"\"\"\n    if text is None:\n        return \"\"\n    return text.strip().lower()"},
    },
    {
        "task_id": "bugfix_210",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "data_proc",
        "buggy_code":'''def process_items(items):
    """Process list of items."""
    return [item.strip() for item in items]
''',
        "fixed_code":'''def process_items(items):
    """Process list of items."""
    if not items:
        return []
    return [item.strip() for item in items]
''',
        "test_code":'''from data_proc import process_items


def test_normal():
    assert process_items([" hello ", " world "]) == ["hello", "world"]


def test_empty():
    assert process_items([]) == []


def test_none():
    assert process_items(None) == []
''',
        "issue": "`process_items(None)` raises `TypeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_data_proc.py`",
        "scripted_fix": {"path": "data_proc.py", "old": "def process_items(items):\n    \"\"\"Process list of items.\"\"\"\n    return [item.strip() for item in items]", "new": "def process_items(items):\n    \"\"\"Process list of items.\"\"\"\n    if not items:\n        return []\n    return [item.strip() for item in items]"},
    },
    # ═══════════════════════════════════════════════════════
    # simple_algorithm (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_211",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "calc_util",
        "buggy_code":'''def average(numbers):
    """Calculate average of numbers."""
    return sum(numbers) / len(numbers)
''',
        "fixed_code":'''def average(numbers):
    """Calculate average of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
''',
        "test_code":'''from calc_util import average


def test_normal():
    assert average([1, 2, 3]) == 2.0


def test_empty():
    assert average([]) == 0.0


def test_single():
    assert average([5]) == 5.0
''',
        "issue": "`average([])` raises `ZeroDivisionError`.\n\nShould handle empty list.\n\nRun: `python -m pytest tests/test_calc_util.py`",
        "scripted_fix": {"path": "calc_util.py", "old": "def average(numbers):\n    \"\"\"Calculate average of numbers.\"\"\"\n    return sum(numbers) / len(numbers)", "new": "def average(numbers):\n    \"\"\"Calculate average of numbers.\"\"\"\n    if not numbers:\n        return 0.0\n    return sum(numbers) / len(numbers)"},
    },
    {
        "task_id": "bugfix_212",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "string_util",
        "buggy_code":'''def count_words(text):
    """Count words in text."""
    return len(text.split())
''',
        "fixed_code":'''def count_words(text):
    """Count words in text."""
    if not text:
        return 0
    return len(text.split())
''',
        "test_code":'''from string_util import count_words


def test_normal():
    assert count_words("hello world") == 2


def test_empty():
    assert count_words("") == 0


def test_none():
    assert count_words(None) == 0
''',
        "issue": "`count_words(None)` raises `AttributeError`.\n\nShould handle None input.\n\nRun: `python -m pytest tests/test_string_util.py`",
        "scripted_fix": {"path": "string_util.py", "old": "def count_words(text):\n    \"\"\"Count words in text.\"\"\"\n    return len(text.split())", "new": "def count_words(text):\n    \"\"\"Count words in text.\"\"\"\n    if not text:\n        return 0\n    return len(text.split())"},
    },
    # ═══════════════════════════════════════════════════════
    # regex (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_213",
        "bug_type": "regex",
        "difficulty": "easy",
        "module": "zip_validate",
        "buggy_code":'''import re


def is_valid_zip(zip_code):
    """Check if zip code is valid (5 digits)."""
    pattern = r"\d{5}"
    return bool(re.match(pattern, zip_code))
''',
        "fixed_code":'''import re


def is_valid_zip(zip_code):
    """Check if zip code is valid (5 digits)."""
    pattern = r"^\d{5}$"
    return bool(re.match(pattern, zip_code))
''',
        "test_code":'''from zip_validate import is_valid_zip


def test_valid():
    assert is_valid_zip("12345") is True


def test_invalid():
    assert is_valid_zip("1234") is False


def test_partial():
    assert is_valid_zip("123456") is False
''',
        "issue": "`is_valid_zip(\"123456\")` returns `True`.\n\nMissing anchors for exact match.\n\nRun: `python -m pytest tests/test_zip_validate.py`",
        "scripted_fix": {"path": "zip_validate.py", "old": 'pattern = r"\\d{5}"', "new": 'pattern = r"^\\d{5}$"'},
    },
    {
        "task_id": "bugfix_214",
        "bug_type": "regex",
        "difficulty": "easy",
        "module": "time_validate",
        "buggy_code":'''import re


def is_valid_time(time_str):
    """Check if time is valid (HH:MM format)."""
    pattern = r"\d{2}:\d{2}"
    return bool(re.match(pattern, time_str))
''',
        "fixed_code":'''import re


def is_valid_time(time_str):
    """Check if time is valid (HH:MM format)."""
    pattern = r"^[0-2]\d:[0-5]\d$"
    return bool(re.match(pattern, time_str))
''',
        "test_code":'''from time_validate import is_valid_time


def test_valid():
    assert is_valid_time("14:30") is True


def test_invalid_hour():
    assert is_valid_time("25:30") is False


def test_invalid_format():
    assert is_valid_time("1430") is False
''',
        "issue": "`is_valid_time(\"25:30\")` returns `True`.\n\nShould validate hour range (0-23).\n\nRun: `python -m pytest tests/test_time_validate.py`",
        "scripted_fix": {"path": "time_validate.py", "old": 'pattern = r"\\d{2}:\\d{2}"', "new": 'pattern = r"^[0-2]\\d:[0-5]\\d$"'},
    },
    # ═══════════════════════════════════════════════════════
    # boolean_logic (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_215",
        "bug_type": "boolean_logic",
        "difficulty": "easy",
        "module": "perm_check",
        "buggy_code":'''def has_permission(user, action):
    """Check if user has permission for action."""
    return user["is_admin"] and action in user["permissions"]
''',
        "fixed_code":'''def has_permission(user, action):
    """Check if user has permission for action."""
    return user["is_admin"] or action in user["permissions"]
''',
        "test_code":'''from perm_check import has_permission


def test_admin():
    assert has_permission({"is_admin": True, "permissions": []}, "read") is True


def test_user_with_perm():
    assert has_permission({"is_admin": False, "permissions": ["read"]}, "read") is True


def test_user_no_perm():
    assert has_permission({"is_admin": False, "permissions": []}, "read") is False
''',
        "issue": "Admin users are denied access to actions not in their permissions list.\n\n`has_permission({\"is_admin\": True, \"permissions\": []}, \"read\")` should return `True`.\n\nRun: `python -m pytest tests/test_perm_check.py`",
        "scripted_fix": {"path": "perm_check.py", "old": 'return user["is_admin"] and action in user["permissions"]', "new": 'return user["is_admin"] or action in user["permissions"]'},
    },
    # ═══════════════════════════════════════════════════════
    # exception_handling (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_216",
        "bug_type": "exception_handling",
        "difficulty": "easy",
        "module": "json_util",
        "buggy_code":'''def parse_json(json_str):
    """Parse JSON string."""
    import json
    return json.loads(json_str)
''',
        "fixed_code":'''def parse_json(json_str):
    """Parse JSON string."""
    import json
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None
''',
        "test_code":'''from json_util import parse_json


def test_valid():
    assert parse_json('{"key": "value"}') == {"key": "value"}


def test_invalid():
    assert parse_json("not json") is None


def test_none():
    assert parse_json(None) is None
''',
        "issue": "`parse_json(\"not json\")` raises `JSONDecodeError`.\n\nShould handle invalid JSON gracefully.\n\nRun: `python -m pytest tests/test_json_util.py`",
        "scripted_fix": {"path": "json_util.py", "old": "def parse_json(json_str):\n    \"\"\"Parse JSON string.\"\"\"\n    import json\n    return json.loads(json_str)", "new": "def parse_json(json_str):\n    \"\"\"Parse JSON string.\"\"\"\n    import json\n    try:\n        return json.loads(json_str)\n    except (json.JSONDecodeError, TypeError):\n        return None"},
    },
    # ═══════════════════════════════════════════════════════
    # floating_precision (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_217",
        "bug_type": "floating_precision",
        "difficulty": "easy",
        "module": "math_util",
        "buggy_code":'''def add_values(a, b):
    """Add two values."""
    return a + b
''',
        "fixed_code":'''def add_values(a, b, precision=10):
    """Add two values with rounding."""
    return round(a + b, precision)
''',
        "test_code":'''from math_util import add_values


def test_basic():
    assert add_values(1.1, 2.2) == 3.3


def test_precision():
    assert add_values(0.1, 0.2) == 0.3
''',
        "issue": "`add_values(0.1, 0.2)` returns `0.30000000000000004` instead of `0.3`.\n\nFloating point precision issue.\n\nRun: `python -m pytest tests/test_math_util.py`",
        "scripted_fix": {"path": "math_util.py", "old": "def add_values(a, b):\n    \"\"\"Add two values.\"\"\"\n    return a + b", "new": "def add_values(a, b, precision=10):\n    \"\"\"Add two values with rounding.\"\"\"\n    return round(a + b, precision)"},
    },
    # ═══════════════════════════════════════════════════════
    # input_validation (unseen tasks)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_218",
        "bug_type": "input_validation",
        "difficulty": "easy",
        "module": "email_util",
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
    return len(parts) == 2 and "." in parts[1]
''',
        "test_code":'''from email_util import is_valid_email


def test_valid():
    assert is_valid_email("user@example.com") is True


def test_no_at():
    assert is_valid_email("userexample.com") is False


def test_empty():
    assert is_valid_email("") is False
''',
        "issue": "`is_valid_email(\"\")` returns `True` because `\"@\" in \"\"` is `False` but empty string should be invalid.\n\nAlso needs proper format validation.\n\nRun: `python -m pytest tests/test_email_util.py`",
        "scripted_fix": {"path": "email_util.py", "old": "def is_valid_email(email):\n    \"\"\"Validate email format.\"\"\"\n    return \"@\" in email", "new": "def is_valid_email(email):\n    \"\"\"Validate email format.\"\"\"\n    if not email:\n        return False\n    if \"@\" not in email:\n        return False\n    parts = email.split(\"@\")\n    return len(parts) == 2 and \".\" in parts[1]"},
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

    print(f"Generated {len(TASKS)} held-out tasks: {TASKS[0]['task_id']} .. {TASKS[-1]['task_id']}")


if __name__ == "__main__":
    main()
