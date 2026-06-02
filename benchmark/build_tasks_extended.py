"""Generate benchmark tasks bugfix_031 .. bugfix_100.

Covers 30 bug types with at least 5 variants each.
Target: 70 new tasks (total 100 with existing 30).
"""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # ═══════════════════════════════════════════════════════
    # boundary_condition (variants 3-5)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_031",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "age_check",
        "buggy_code": '''def is_adult(age):
    """Return True if age >= 18."""
    return age > 18
''',
        "fixed_code": '''def is_adult(age):
    """Return True if age >= 18."""
    return age >= 18
''',
        "test_code": '''from age_check import is_adult


def test_adult_exactly_18():
    assert is_adult(18) is True


def test_adult_17():
    assert is_adult(17) is False


def test_adult_25():
    assert is_adult(25) is True
''',
        "issue": "`is_adult(18)` should return `True` but returns `False`.\n\nBoundary condition error: uses `>` instead of `>=`.\n\nRun: `python -m pytest tests/test_age_check.py`",
        "scripted_fix": {"path": "age_check.py", "old": "return age > 18", "new": "return age >= 18"},
    },
    {
        "task_id": "bugfix_032",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "percentage",
        "buggy_code": '''def clamp_percentage(value):
    """Clamp value to 0-100 range."""
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value
''',
        "fixed_code": '''def clamp_percentage(value):
    """Clamp value to 0-100 inclusive."""
    if value < 0:
        return 0
    if value > 100:
        return 100
    return value


def is_valid_percentage(value):
    """Check if value is a valid percentage (0-100 inclusive)."""
    return 0 <= value <= 100
''',
        "test_code": '''from percentage import clamp_percentage


def test_clamp_zero():
    assert clamp_percentage(0) == 0


def test_clamp_100():
    assert clamp_percentage(100) == 100


def test_clamp_50():
    assert clamp_percentage(50) == 50


def test_clamp_negative():
    assert clamp_percentage(-5) == 0


def test_clamp_over_100():
    assert clamp_percentage(150) == 100
''',
        "issue": "Tests expect an `is_valid_percentage` function that doesn't exist.\n\nRun: `python -m pytest tests/test_percentage.py`",
        "scripted_fix": {"path": "percentage.py", "old": "    return value\n", "new": "    return value\n\n\ndef is_valid_percentage(value):\n    \"\"\"Check if value is a valid percentage (0-100 inclusive).\"\"\"\n    return 0 <= value <= 100\n"},
    },
    {
        "task_id": "bugfix_033",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "port_check",
        "buggy_code": '''def is_valid_port(port):
    """Check if port number is valid (1-65535)."""
    return 0 < port < 65535
''',
        "fixed_code": '''def is_valid_port(port):
    """Check if port number is valid (1-65535)."""
    return 1 <= port <= 65535
''',
        "test_code": '''from port_check import is_valid_port


def test_valid_port_80():
    assert is_valid_port(80) is True


def test_valid_port_65535():
    assert is_valid_port(65535) is True


def test_valid_port_1():
    assert is_valid_port(1) is True


def test_invalid_port_0():
    assert is_valid_port(0) is False


def test_invalid_port_65536():
    assert is_valid_port(65536) is False
''',
        "issue": "`is_valid_port(65535)` returns `False` but port 65535 is valid.\n\nBoundary error: uses `<` instead of `<=` for upper bound.\n\nRun: `python -m pytest tests/test_port_check.py`",
        "scripted_fix": {"path": "port_check.py", "old": "return 0 < port < 65535", "new": "return 1 <= port <= 65535"},
    },

    # ═══════════════════════════════════════════════════════
    # type_conversion (variants 3-5)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_034",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "add_nums",
        "buggy_code": '''def add_strings(a, b):
    """Add two numbers passed as strings."""
    return a + b
''',
        "fixed_code": '''def add_strings(a, b):
    """Add two numbers passed as strings."""
    return int(a) + int(b)
''',
        "test_code": '''from add_nums import add_strings


def test_add_positive():
    assert add_strings("3", "5") == 8


def test_add_zero():
    assert add_strings("0", "0") == 0


def test_add_negative():
    assert add_strings("-2", "3") == 1
''',
        "issue": "`add_strings(\"3\", \"5\")` returns `\"35\"` instead of `8`.\n\nString concatenation instead of numeric addition.\n\nRun: `python -m pytest tests/test_add_nums.py`",
        "scripted_fix": {"path": "add_nums.py", "old": "return a + b", "new": "return int(a) + int(b)"},
    },
    {
        "task_id": "bugfix_035",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "price_calc",
        "buggy_code": '''def calculate_total(price_str, quantity):
    """Calculate total price from string price and int quantity."""
    return price_str * quantity
''',
        "fixed_code": '''def calculate_total(price_str, quantity):
    """Calculate total price from string price and int quantity."""
    return float(price_str) * quantity
''',
        "test_code": '''from price_calc import calculate_total


def test_basic_total():
    assert calculate_total("9.99", 3) == 29.97


def test_zero_quantity():
    assert calculate_total("10.00", 0) == 0.0


def test_single_item():
    assert calculate_total("5.50", 1) == 5.50
''',
        "issue": "`calculate_total(\"9.99\", 3)` returns `\"9.999.999.99\"` instead of `29.97`.\n\nType error: string repetition instead of float multiplication.\n\nRun: `python -m pytest tests/test_price_calc.py`",
        "scripted_fix": {"path": "price_calc.py", "old": "return price_str * quantity", "new": "return float(price_str) * quantity"},
    },
    {
        "task_id": "bugfix_036",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "bool_convert",
        "buggy_code": '''def is_truthy(value):
    """Return True if value is truthy."""
    return value == "True"
''',
        "fixed_code": '''def is_truthy(value):
    """Return True if value is truthy."""
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)
''',
        "test_code": '''from bool_convert import is_truthy


def test_true_string():
    assert is_truthy("True") is True


def test_true_lower():
    assert is_truthy("true") is True


def test_one():
    assert is_truthy("1") is True


def test_empty():
    assert is_truthy("") is False


def test_none():
    assert is_truthy(None) is False
''',
        "issue": "`is_truthy(\"true\")` returns `False` because comparison is case-sensitive.\n\nAlso doesn't handle `\"1\"`, `\"yes\"`, `None`, or empty string.\n\nRun: `python -m pytest tests/test_bool_convert.py`",
        "scripted_fix": {"path": "bool_convert.py", "old": "    return value == \"True\"", "new": "    if isinstance(value, str):\n        return value.lower() in (\"true\", \"1\", \"yes\")\n    return bool(value)"},
    },

    # ═══════════════════════════════════════════════════════
    # dict_key (variants 3-5)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_037",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "user_info",
        "buggy_code": '''def get_display_name(user):
    """Get user display name."""
    return user["firstName"] + " " + user["lastName"]
''',
        "fixed_code": '''def get_display_name(user):
    """Get user display name."""
    return user.get("firstName", "") + " " + user.get("lastName", "")
''',
        "test_code": '''from user_info import get_display_name


def test_full_name():
    assert get_display_name({"firstName": "John", "lastName": "Doe"}) == "John Doe"


def test_missing_last():
    assert get_display_name({"firstName": "John"}) == "John "


def test_empty():
    assert get_display_name({}) == " "
''',
        "issue": "`get_display_name({\"firstName\": \"John\"})` raises `KeyError`.\n\nMissing key handling with `.get()`.\n\nRun: `python -m pytest tests/test_user_info.py`",
        "scripted_fix": {"path": "user_info.py", "old": "return user[\"firstName\"] + \" \" + user[\"lastName\"]", "new": "return user.get(\"firstName\", \"\") + \" \" + user.get(\"lastName\", \"\")"},
    },
    {
        "task_id": "bugfix_038",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "config_val",
        "buggy_code": '''def get_config_value(config, key, default=None):
    """Get config value with default."""
    return config[key]
''',
        "fixed_code": '''def get_config_value(config, key, default=None):
    """Get config value with default."""
    return config.get(key, default)
''',
        "test_code": '''from config_val import get_config_value


def test_existing_key():
    assert get_config_value({"host": "localhost"}, "host") == "localhost"


def test_missing_key():
    assert get_config_value({}, "host") is None


def test_missing_with_default():
    assert get_config_value({}, "host", "0.0.0.0") == "0.0.0.0"
''',
        "issue": "`get_config_value({}, \"host\", \"0.0.0.0\")` raises `KeyError` instead of returning default.\n\nIgnores the `default` parameter.\n\nRun: `python -m pytest tests/test_config_val.py`",
        "scripted_fix": {"path": "config_val.py", "old": "return config[key]", "new": "return config.get(key, default)"},
    },
    {
        "task_id": "bugfix_039",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "stats_dict",
        "buggy_code":'''def merge_stats(base, update):
    """Merge update into base stats."""
    result = base.copy()
    for key, val in update.items():
        result[key] = result[key] + val
    return result
''',
        "fixed_code":'''def merge_stats(base, update):
    """Merge update into base stats."""
    result = base.copy()
    for key, val in update.items():
        result[key] = result.get(key, 0) + val
    return result
''',
        "test_code":'''from stats_dict import merge_stats


def test_merge_existing():
    assert merge_stats({"a": 1}, {"a": 2}) == {"a": 3}


def test_merge_new_key():
    assert merge_stats({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}


def test_merge_empty():
    assert merge_stats({}, {"x": 5}) == {"x": 5}
''',
        "issue": "`merge_stats({}, {\"x\": 5})` raises `KeyError`.\n\nShould use `.get(key, 0)` for missing keys.\n\nRun: `python -m pytest tests/test_stats_dict.py`",
        "scripted_fix": {"path": "stats_dict.py", "old": "result[key] = result[key] + val", "new": "result[key] = result.get(key, 0) + val"},
    },

    # ═══════════════════════════════════════════════════════
    # off_by_one (variants 3-5)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_040",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "chunk_list",
        "buggy_code":'''def get_chunk(lst, chunk_size, chunk_index):
    """Get a chunk of a list by index."""
    start = chunk_index * chunk_size
    end = start + chunk_size - 1
    return lst[start:end]
''',
        "fixed_code":'''def get_chunk(lst, chunk_size, chunk_index):
    """Get a chunk of a list by index."""
    start = chunk_index * chunk_size
    end = start + chunk_size
    return lst[start:end]
''',
        "test_code":'''from chunk_list import get_chunk


def test_first_chunk():
    assert get_chunk([1, 2, 3, 4, 5, 6], 2, 0) == [1, 2]


def test_second_chunk():
    assert get_chunk([1, 2, 3, 4, 5, 6], 2, 1) == [3, 4]


def test_partial_chunk():
    assert get_chunk([1, 2, 3, 4, 5], 3, 1) == [4, 5]
''',
        "issue": "`get_chunk([1,2,3,4,5,6], 2, 0)` returns `[1]` instead of `[1, 2]`.\n\nOff-by-one: `end` should be `start + chunk_size`, not `start + chunk_size - 1`.\n\nRun: `python -m pytest tests/test_chunk_list.py`",
        "scripted_fix": {"path": "chunk_list.py", "old": "end = start + chunk_size - 1", "new": "end = start + chunk_size"},
    },
    {
        "task_id": "bugfix_041",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "sliding_window",
        "buggy_code":'''def get_windows(lst, size):
    """Get all sliding windows of given size."""
    result = []
    for i in range(len(lst) - size):
        result.append(lst[i:i + size])
    return result
''',
        "fixed_code":'''def get_windows(lst, size):
    """Get all sliding windows of given size."""
    result = []
    for i in range(len(lst) - size + 1):
        result.append(lst[i:i + size])
    return result
''',
        "test_code":'''from sliding_window import get_windows


def test_windows_basic():
    assert get_windows([1, 2, 3, 4], 2) == [[1, 2], [2, 3], [3, 4]]


def test_windows_size_3():
    assert get_windows([1, 2, 3, 4, 5], 3) == [[1, 2, 3], [2, 3, 4], [3, 4, 5]]


def test_windows_full_size():
    assert get_windows([1, 2, 3], 3) == [[1, 2, 3]]
''',
        "issue": "`get_windows([1,2,3,4], 2)` returns `[[1,2], [2,3]]` missing `[3,4]`.\n\nOff-by-one in range: should be `len(lst) - size + 1`.\n\nRun: `python -m pytest tests/test_sliding_window.py`",
        "scripted_fix": {"path": "sliding_window.py", "old": "for i in range(len(lst) - size):", "new": "for i in range(len(lst) - size + 1):"},
    },
    {
        "task_id": "bugfix_042",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "pagination",
        "buggy_code":'''def get_page_range(total_items, page_size, page_num):
    """Get start and end index for a page (0-indexed)."""
    start = page_num * page_size
    end = start + page_size
    if end > total_items:
        end = total_items
    return start, end
''',
        "fixed_code":'''def get_page_range(total_items, page_size, page_num):
    """Get start and end index for a page (0-indexed)."""
    start = page_num * page_size
    end = min(start + page_size, total_items)
    return start, end
''',
        "test_code":'''from pagination import get_page_range


def test_first_page():
    assert get_page_range(10, 3, 0) == (0, 3)


def test_second_page():
    assert get_page_range(10, 3, 1) == (3, 6)


def test_last_partial_page():
    assert get_page_range(10, 3, 3) == (9, 10)


def test_single_page():
    assert get_page_range(5, 10, 0) == (0, 5)
''',
        "issue": "`get_page_range(10, 3, 3)` returns `(9, 12)` instead of `(9, 10)`.\n\nBoundary check missing for last page.\n\nRun: `python -m pytest tests/test_pagination.py`",
        "scripted_fix": {"path": "pagination.py", "old": "    end = start + page_size\n    if end > total_items:\n        end = total_items\n    return start, end", "new": "    end = min(start + page_size, total_items)\n    return start, end"},
    },

    # ═══════════════════════════════════════════════════════
    # none_handling (variants 5-8)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_043",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_upper",
        "buggy_code":'''def safe_upper(text):
    """Convert to uppercase, handle None."""
    return text.upper()
''',
        "fixed_code":'''def safe_upper(text):
    """Convert to uppercase, handle None."""
    if text is None:
        return ""
    return text.upper()
''',
        "test_code":'''from safe_upper import safe_upper


def test_normal():
    assert safe_upper("hello") == "HELLO"


def test_none():
    assert safe_upper(None) == ""


def test_empty():
    assert safe_upper("") == ""
''',
        "issue": "`safe_upper(None)` raises `AttributeError`.\n\nMissing None check.\n\nRun: `python -m pytest tests/test_safe_upper.py`",
        "scripted_fix": {"path": "safe_upper.py", "old": "    return text.upper()", "new": "    if text is None:\n        return \"\"\n    return text.upper()"},
    },
    {
        "task_id": "bugfix_044",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_len",
        "buggy_code":'''def safe_length(items):
    """Get length of items, return 0 for None."""
    return len(items)
''',
        "fixed_code":'''def safe_length(items):
    """Get length of items, return 0 for None."""
    if items is None:
        return 0
    return len(items)
''',
        "test_code":'''from safe_len import safe_length


def test_list():
    assert safe_length([1, 2, 3]) == 3


def test_none():
    assert safe_length(None) == 0


def test_empty():
    assert safe_length([]) == 0
''',
        "issue": "`safe_length(None)` raises `TypeError`.\n\nMissing None check before `len()`.\n\nRun: `python -m pytest tests/test_safe_len.py`",
        "scripted_fix": {"path": "safe_len.py", "old": "    return len(items)", "new": "    if items is None:\n        return 0\n    return len(items)"},
    },
    {
        "task_id": "bugfix_045",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_join",
        "buggy_code":'''def join_names(names):
    """Join list of names with comma."""
    return ", ".join(names)
''',
        "fixed_code":'''def join_names(names):
    """Join list of names with comma."""
    if not names:
        return ""
    return ", ".join(names)
''',
        "test_code":'''from safe_join import join_names


def test_normal():
    assert join_names(["Alice", "Bob"]) == "Alice, Bob"


def test_empty():
    assert join_names([]) == ""


def test_none():
    assert join_names(None) == ""


def test_single():
    assert join_names(["Alice"]) == "Alice"
''',
        "issue": "`join_names(None)` raises `TypeError`.\n\nMissing None/empty check.\n\nRun: `python -m pytest tests/test_safe_join.py`",
        "scripted_fix": {"path": "safe_join.py", "old": "    return \", \".join(names)", "new": "    if not names:\n        return \"\"\n    return \", \".join(names)"},
    },
    {
        "task_id": "bugfix_046",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "safe_sum",
        "buggy_code":'''def safe_sum(numbers):
    """Sum a list of numbers, handle None input."""
    return sum(numbers)
''',
        "fixed_code":'''def safe_sum(numbers):
    """Sum a list of numbers, handle None input."""
    if numbers is None:
        return 0
    return sum(numbers)
''',
        "test_code":'''from safe_sum import safe_sum


def test_normal():
    assert safe_sum([1, 2, 3]) == 6


def test_none():
    assert safe_sum(None) == 0


def test_empty():
    assert safe_sum([]) == 0
''',
        "issue": "`safe_sum(None)` raises `TypeError`.\n\nMissing None check.\n\nRun: `python -m pytest tests/test_safe_sum.py`",
        "scripted_fix": {"path": "safe_sum.py", "old": "    return sum(numbers)", "new": "    if numbers is None:\n        return 0\n    return sum(numbers)"},
    },

    # ═══════════════════════════════════════════════════════
    # regex (variants 4-6)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_047",
        "bug_type": "regex",
        "difficulty": "easy",
        "module": "phone_val",
        "buggy_code":'''import re


def is_valid_phone(phone):
    """Check if phone matches XXX-XXX-XXXX format."""
    pattern = r"\d{3}-\d{3}-\d{4}"
    return bool(re.match(pattern, phone))
''',
        "fixed_code":'''import re


def is_valid_phone(phone):
    """Check if phone matches XXX-XXX-XXXX format."""
    pattern = r"^\d{3}-\d{3}-\d{4}$"
    return bool(re.match(pattern, phone))
''',
        "test_code":'''from phone_val import is_valid_phone


def test_valid():
    assert is_valid_phone("123-456-7890") is True


def test_invalid_no_dash():
    assert is_valid_phone("1234567890") is False


def test_partial_match():
    assert is_valid_phone("123-456-7890extra") is False
''',
        "issue": "`is_valid_phone(\"123-456-7890extra\")` returns `True`.\n\nMissing `^` and `$` anchors for exact match.\n\nRun: `python -m pytest tests/test_phone_val.py`",
        "scripted_fix": {"path": "phone_val.py", "old": 'pattern = r"\\d{3}-\\d{3}-\\d{4}"', "new": 'pattern = r"^\\d{3}-\\d{3}-\\d{4}$"'},
    },
    {
        "task_id": "bugfix_048",
        "bug_type": "regex",
        "difficulty": "easy",
        "module": "email_check",
        "buggy_code":'''import re


def is_valid_email(email):
    """Basic email validation."""
    pattern = r".+@.+\..+"
    return bool(re.match(pattern, email))
''',
        "fixed_code":'''import re


def is_valid_email(email):
    """Basic email validation."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.match(pattern, email))
''',
        "test_code":'''from email_check import is_valid_email


def test_valid():
    assert is_valid_email("user@example.com") is True


def test_no_at():
    assert is_valid_email("userexample.com") is False


def test_spaces():
    assert is_valid_email("user @example.com") is False


def test_double_at():
    assert is_valid_email("user@@example.com") is False
''',
        "issue": "`is_valid_email(\"user @example.com\")` returns `True`.\n\nRegex too permissive, allows spaces and multiple @.\n\nRun: `python -m pytest tests/test_email_check.py`",
        "scripted_fix": {"path": "email_check.py", "old": 'pattern = r".+@.+\\..+"', "new": 'pattern = r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"'},
    },
    {
        "task_id": "bugfix_049",
        "bug_type": "regex",
        "difficulty": "easy",
        "module": "hex_check",
        "buggy_code":'''import re


def is_valid_hex(color):
    """Check if string is valid hex color (#RRGGBB)."""
    pattern = r"#[0-9a-fA-F]{6}"
    return bool(re.match(pattern, color))
''',
        "fixed_code":'''import re


def is_valid_hex(color):
    """Check if string is valid hex color (#RRGGBB)."""
    pattern = r"^#[0-9a-fA-F]{6}$"
    return bool(re.match(pattern, color))
''',
        "test_code":'''from hex_check import is_valid_hex


def test_valid():
    assert is_valid_hex("#FF00FF") is True


def test_invalid_short():
    assert is_valid_hex("#FFF") is False


def test_no_hash():
    assert is_valid_hex("FF00FF") is False


def test_partial():
    assert is_valid_hex("#FF00FFextra") is False
''',
        "issue": "`is_valid_hex(\"#FF00FFextra\")` returns `True`.\n\nMissing anchors for exact match.\n\nRun: `python -m pytest tests/test_hex_check.py`",
        "scripted_fix": {"path": "hex_check.py", "old": 'pattern = r"#[0-9a-fA-F]{6}"', "new": 'pattern = r"^#[0-9a-fA-F]{6}$"'},
    },

    # ═══════════════════════════════════════════════════════
    # return_format (variants 3-5)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_050",
        "bug_type": "return_format",
        "difficulty": "easy",
        "module": "status_resp",
        "buggy_code":'''def create_response(success, data=None, error=None):
    """Create API response dict."""
    if success:
        return {"status": "ok", "data": data}
    return {"status": "error"}
''',
        "fixed_code":'''def create_response(success, data=None, error=None):
    """Create API response dict."""
    if success:
        return {"status": "ok", "data": data}
    return {"status": "error", "error": error}
''',
        "test_code":'''from status_resp import create_response


def test_success():
    resp = create_response(True, data={"id": 1})
    assert resp == {"status": "ok", "data": {"id": 1}}


def test_error():
    resp = create_response(False, error="not found")
    assert resp == {"status": "error", "error": "not found"}


def test_error_keys():
    resp = create_response(False, error="fail")
    assert "error" in resp
''',
        "issue": "`create_response(False, error=\"not found\")` returns `{\"status\": \"error\"}` without error message.\n\nMissing error field in response.\n\nRun: `python -m pytest tests/test_status_resp.py`",
        "scripted_fix": {"path": "status_resp.py", "old": 'return {"status": "error"}', "new": 'return {"status": "error", "error": error}'},
    },
    {
        "task_id": "bugfix_051",
        "bug_type": "return_format",
        "difficulty": "easy",
        "module": "list_resp",
        "buggy_code":'''def get_items_paginated(items, page, size):
    """Return paginated items."""
    start = page * size
    end = start + size
    return items[start:end]
''',
        "fixed_code":'''def get_items_paginated(items, page, size):
    """Return paginated items with metadata."""
    start = page * size
    end = start + size
    return {
        "items": items[start:end],
        "page": page,
        "total": len(items),
    }
''',
        "test_code":'''from list_resp import get_items_paginated


def test_basic():
    result = get_items_paginated([1, 2, 3, 4, 5], 0, 2)
    assert result["items"] == [1, 2]
    assert result["page"] == 0
    assert result["total"] == 5


def test_second_page():
    result = get_items_paginated([1, 2, 3, 4, 5], 1, 2)
    assert result["items"] == [3, 4]
''',
        "issue": "Tests expect a dict with `items`, `page`, `total` keys.\n\nFunction returns raw list instead.\n\nRun: `python -m pytest tests/test_list_resp.py`",
        "scripted_fix": {"path": "list_resp.py", "old": "    return items[start:end]", "new": "    return {\n        \"items\": items[start:end],\n        \"page\": page,\n        \"total\": len(items),\n    }"},
    },
    {
        "task_id": "bugfix_052",
        "bug_type": "return_format",
        "difficulty": "easy",
        "module": "error_resp",
        "buggy_code":'''def divide(a, b):
    """Divide a by b, return result or error."""
    if b == 0:
        return None
    return a / b
''',
        "fixed_code":'''def divide(a, b):
    """Divide a by b, return result or error."""
    if b == 0:
        return {"error": "Division by zero"}
    return {"result": a / b}
''',
        "test_code":'''from error_resp import divide


def test_normal():
    result = divide(10, 2)
    assert result["result"] == 5.0


def test_division_by_zero():
    result = divide(10, 0)
    assert "error" in result
    assert result["error"] == "Division by zero"


def test_result_key():
    result = divide(6, 3)
    assert "result" in result
''',
        "issue": "Tests expect dict return format `{\"result\": ...}` or `{\"error\": ...}`.\n\nFunction returns raw number or None.\n\nRun: `python -m pytest tests/test_error_resp.py`",
        "scripted_fix": {"path": "error_resp.py", "old": "    if b == 0:\n        return None\n    return a / b", "new": "    if b == 0:\n        return {\"error\": \"Division by zero\"}\n    return {\"result\": a / b}"},
    },

    # ═══════════════════════════════════════════════════════
    # argument_order (variants 3-5)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_053",
        "bug_type": "argument_order",
        "difficulty": "easy",
        "module": "substr_check",
        "buggy_code":'''def is_substring(short, long):
    """Check if short is a substring of long."""
    return short in long
''',
        "fixed_code":'''def is_substring(short, long):
    """Check if short is a substring of long."""
    return short in long


def contains(text, pattern):
    """Check if pattern is in text."""
    return pattern in text
''',
        "test_code":'''from substr_check import is_substring


def test_is_substring():
    assert is_substring("hello", "say hello world") is True


def test_not_substring():
    assert is_substring("xyz", "hello world") is False


def test_exact():
    assert is_substring("hello", "hello") is True
''',
        "issue": "Tests pass with current code. Need to add `contains` function.\n\nRun: `python -m pytest tests/test_substr_check.py`",
        "scripted_fix": {"path": "substr_check.py", "old": "    return short in long\n", "new": "    return short in long\n\n\ndef contains(text, pattern):\n    \"\"\"Check if pattern is in text.\"\"\"\n    return pattern in text\n"},
    },
    {
        "task_id": "bugfix_054",
        "bug_type": "argument_order",
        "difficulty": "easy",
        "module": "math_ops",
        "buggy_code":'''def subtract(a, b):
    """Return a - b."""
    return b - a
''',
        "fixed_code":'''def subtract(a, b):
    """Return a - b."""
    return a - b
''',
        "test_code":'''from math_ops import subtract


def test_positive():
    assert subtract(10, 3) == 7


def test_negative():
    assert subtract(3, 10) == -7


def test_zero():
    assert subtract(5, 5) == 0
''',
        "issue": "`subtract(10, 3)` returns `-7` instead of `7`.\n\nArgument order swapped: returns `b - a` instead of `a - b`.\n\nRun: `python -m pytest tests/test_math_ops.py`",
        "scripted_fix": {"path": "math_ops.py", "old": "return b - a", "new": "return a - b"},
    },
    {
        "task_id": "bugfix_055",
        "bug_type": "argument_order",
        "difficulty": "easy",
        "module": "str_repeat",
        "buggy_code":'''def repeat_string(text, times):
    """Repeat text N times."""
    return text * times


def repeat_with_sep(text, sep, times):
    """Repeat text N times with separator."""
    return (text + sep) * times
''',
        "fixed_code":'''def repeat_string(text, times):
    """Repeat text N times."""
    return text * times


def repeat_with_sep(text, sep, times):
    """Repeat text N times with separator."""
    result = []
    for i in range(times):
        result.append(text)
    return sep.join(result)
''',
        "test_code":'''from str_repeat import repeat_string, repeat_with_sep


def test_repeat():
    assert repeat_string("ab", 3) == "ababab"


def test_with_sep():
    assert repeat_with_sep("a", ",", 3) == "a,a,a"


def test_with_sep_two():
    assert repeat_with_sep("hello", "-", 2) == "hello-hello"
''',
        "issue": "`repeat_with_sep(\"a\", \",\", 3)` returns `\"a,a,a,\"` instead of `\"a,a,a\"`.\n\nImplementation adds trailing separator.\n\nRun: `python -m pytest tests/test_str_repeat.py`",
        "scripted_fix": {"path": "str_repeat.py", "old": "    return (text + sep) * times", "new": "    result = []\n    for i in range(times):\n        result.append(text)\n    return sep.join(result)"},
    },

    # ═══════════════════════════════════════════════════════
    # simple_algorithm (variants 3-6)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_056",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "max_val",
        "buggy_code":'''def find_max(lst):
    """Find maximum value in list."""
    if not lst:
        return None
    max_val = 0
    for item in lst:
        if item > max_val:
            max_val = item
    return max_val
''',
        "fixed_code":'''def find_max(lst):
    """Find maximum value in list."""
    if not lst:
        return None
    max_val = lst[0]
    for item in lst[1:]:
        if item > max_val:
            max_val = item
    return max_val
''',
        "test_code":'''from max_val import find_max


def test_positive():
    assert find_max([1, 3, 2]) == 3


def test_all_negative():
    assert find_max([-5, -2, -8]) == -2


def test_single():
    assert find_max([42]) == 42


def test_empty():
    assert find_max([]) is None
''',
        "issue": "`find_max([-5, -2, -8])` returns `0` instead of `-2`.\n\nInitial max_val should be `lst[0]`, not `0`.\n\nRun: `python -m pytest tests/test_max_val.py`",
        "scripted_fix": {"path": "max_val.py", "old": "    max_val = 0\n    for item in lst:", "new": "    max_val = lst[0]\n    for item in lst[1:]:"},
    },
    {
        "task_id": "bugfix_057",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "count_chars",
        "buggy_code":'''def count_vowels(text):
    """Count vowels in text."""
    vowels = "aeiou"
    count = 0
    for char in text:
        if char in vowels:
            count += 1
    return count
''',
        "fixed_code":'''def count_vowels(text):
    """Count vowels in text."""
    vowels = "aeiouAEIOU"
    count = 0
    for char in text:
        if char in vowels:
            count += 1
    return count
''',
        "test_code":'''from count_chars import count_vowels


def test_lower():
    assert count_vowels("hello") == 2


def test_upper():
    assert count_vowels("HELLO") == 2


def test_mixed():
    assert count_vowels("HeLLo") == 2


def test_no_vowels():
    assert count_vowels("rhythm") == 0
''',
        "issue": "`count_vowels(\"HELLO\")` returns `0` instead of `2`.\n\nOnly checks lowercase vowels.\n\nRun: `python -m pytest tests/test_count_chars.py`",
        "scripted_fix": {"path": "count_chars.py", "old": 'vowels = "aeiou"', "new": 'vowels = "aeiouAEIOU"'},
    },
    {
        "task_id": "bugfix_058",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "list_reverse",
        "buggy_code":'''def reverse_list(lst):
    """Return a reversed copy of the list."""
    return lst.reverse()
''',
        "fixed_code":'''def reverse_list(lst):
    """Return a reversed copy of the list."""
    return lst[::-1]
''',
        "test_code":'''from list_reverse import reverse_list


def test_basic():
    assert reverse_list([1, 2, 3]) == [3, 2, 1]


def test_single():
    assert reverse_list([1]) == [1]


def test_empty():
    assert reverse_list([]) == []


def test_original_unchanged():
    original = [1, 2, 3]
    reverse_list(original)
    assert original == [1, 2, 3]
''',
        "issue": "`reverse_list([1, 2, 3])` returns `None`.\n\n`list.reverse()` modifies in-place and returns None.\n\nRun: `python -m pytest tests/test_list_reverse.py`",
        "scripted_fix": {"path": "list_reverse.py", "old": "return lst.reverse()", "new": "return lst[::-1]"},
    },
    {
        "task_id": "bugfix_059",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "flatten_list",
        "buggy_code":'''def flatten(nested):
    """Flatten a nested list."""
    result = []
    for item in nested:
        if isinstance(item, list):
            flatten(item)
        else:
            result.append(item)
    return result
''',
        "fixed_code":'''def flatten(nested):
    """Flatten a nested list."""
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result
''',
        "test_code":'''from flatten_list import flatten


def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]


def test_nested():
    assert flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def test_deep_nested():
    assert flatten([1, [2, [3, 4]], 5]) == [1, 2, 3, 4, 5]
''',
        "issue": "`flatten([1, [2, 3], 4])` returns `[1, 4]`.\n\nRecursive result not being collected.\n\nRun: `python -m pytest tests/test_flatten_list.py`",
        "scripted_fix": {"path": "flatten_list.py", "old": "            flatten(item)", "new": "            result.extend(flatten(item))"},
    },

    # ═══════════════════════════════════════════════════════
    # sorting_key (variants 2-4)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_060",
        "bug_type": "sorting_key",
        "difficulty": "easy",
        "module": "sort_names",
        "buggy_code":'''def sort_by_last_name(people):
    """Sort people by last name."""
    return sorted(people, key=lambda p: p["name"])
''',
        "fixed_code":'''def sort_by_last_name(people):
    """Sort people by last name."""
    return sorted(people, key=lambda p: p["name"].split()[-1])
''',
        "test_code":'''from sort_names import sort_by_last_name


def test_sort():
    people = [
        {"name": "John Smith"},
        {"name": "Alice Brown"},
        {"name": "Bob Anderson"},
    ]
    result = sort_by_last_name(people)
    assert [p["name"] for p in result] == ["Bob Anderson", "Alice Brown", "John Smith"]
''',
        "issue": "Sorts by full name instead of last name.\n\n`Anderson` should come before `Brown`.\n\nRun: `python -m pytest tests/test_sort_names.py`",
        "scripted_fix": {"path": "sort_names.py", "old": 'return sorted(people, key=lambda p: p["name"])', "new": 'return sorted(people, key=lambda p: p["name"].split()[-1])'},
    },
    {
        "task_id": "bugfix_061",
        "bug_type": "sorting_key",
        "difficulty": "easy",
        "module": "sort_items",
        "buggy_code":'''def sort_by_price(items):
    """Sort items by price."""
    return sorted(items, key=lambda x: x["price"])
''',
        "fixed_code":'''def sort_by_price(items, reverse=False):
    """Sort items by price."""
    return sorted(items, key=lambda x: x["price"], reverse=reverse)
''',
        "test_code":'''from sort_items import sort_by_price


def test_ascending():
    items = [{"name": "b", "price": 20}, {"name": "a", "price": 10}]
    result = sort_by_price(items)
    assert result[0]["name"] == "a"


def test_descending():
    items = [{"name": "a", "price": 10}, {"name": "b", "price": 20}]
    result = sort_by_price(items, reverse=True)
    assert result[0]["name"] == "b"
''',
        "issue": "Tests expect `reverse` parameter for descending sort.\n\nFunction doesn't support it.\n\nRun: `python -m pytest tests/test_sort_items.py`",
        "scripted_fix": {"path": "sort_items.py", "old": "def sort_by_price(items):\n    \"\"\"Sort items by price.\"\"\"\n    return sorted(items, key=lambda x: x[\"price\"])", "new": "def sort_by_price(items, reverse=False):\n    \"\"\"Sort items by price.\"\"\"\n    return sorted(items, key=lambda x: x[\"price\"], reverse=reverse)"},
    },
    {
        "task_id": "bugfix_062",
        "bug_type": "sorting_key",
        "difficulty": "easy",
        "module": "sort_case",
        "buggy_code":'''def sort_strings(strings):
    """Sort strings case-insensitively."""
    return sorted(strings)
''',
        "fixed_code":'''def sort_strings(strings):
    """Sort strings case-insensitively."""
    return sorted(strings, key=str.lower)
''',
        "test_code":'''from sort_case import sort_strings


def test_case_sort():
    result = sort_strings(["banana", "Apple", "cherry"])
    assert result == ["Apple", "banana", "cherry"]


def test_all_lower():
    result = sort_strings(["c", "a", "b"])
    assert result == ["a", "b", "c"]
''',
        "issue": "`sort_strings([\"banana\", \"Apple\", \"cherry\"])` returns `[\"Apple\", \"banana\", \"cherry\"]` which is wrong.\n\nDefault sort is case-sensitive: uppercase sorts before lowercase.\n\nRun: `python -m pytest tests/test_sort_case.py`",
        "scripted_fix": {"path": "sort_case.py", "old": "return sorted(strings)", "new": "return sorted(strings, key=str.lower)"},
    },

    # ═══════════════════════════════════════════════════════
    # boolean_logic (variants 2-4)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_063",
        "bug_type": "boolean_logic",
        "difficulty": "easy",
        "module": "access_ctrl",
        "buggy_code":'''def can_access(user, resource):
    """Check if user can access resource."""
    return user["is_admin"] or user["id"] == resource["owner_id"] and user["is_active"]
''',
        "fixed_code":'''def can_access(user, resource):
    """Check if user can access resource."""
    return user["is_admin"] or (user["id"] == resource["owner_id"] and user["is_active"])
''',
        "test_code":'''from access_ctrl import can_access


def test_admin():
    assert can_access({"id": 1, "is_admin": True, "is_active": True}, {"owner_id": 2}) is True


def test_owner_active():
    assert can_access({"id": 1, "is_admin": False, "is_active": True}, {"owner_id": 1}) is True


def test_owner_inactive():
    assert can_access({"id": 1, "is_admin": False, "is_active": False}, {"owner_id": 1}) is False


def test_non_owner():
    assert can_access({"id": 1, "is_admin": False, "is_active": True}, {"owner_id": 2}) is False
''',
        "issue": "`can_access({\"id\": 1, \"is_admin\": False, \"is_active\": False}, {\"owner_id\": 1})` returns `True`.\n\nOperator precedence: `and` binds tighter than `or`.\n\nRun: `python -m pytest tests/test_access_ctrl.py`",
        "scripted_fix": {"path": "access_ctrl.py", "old": '    return user["is_admin"] or user["id"] == resource["owner_id"] and user["is_active"]', "new": '    return user["is_admin"] or (user["id"] == resource["owner_id"] and user["is_active"])'},
    },
    {
        "task_id": "bugfix_064",
        "bug_type": "boolean_logic",
        "difficulty": "easy",
        "module": "flag_check",
        "buggy_code":'''def check_flags(flags):
    """Check if required flags are set."""
    required = ["read", "write"]
    return all(f in flags for f in required)
''',
        "fixed_code":'''def check_flags(flags):
    """Check if required flags are set and True."""
    required = ["read", "write"]
    return all(flags.get(f, False) for f in required)
''',
        "test_code":'''from flag_check import check_flags


def test_both_set():
    assert check_flags({"read": True, "write": True}) is True


def test_one_missing():
    assert check_flags({"read": True}) is False


def test_one_false():
    assert check_flags({"read": True, "write": False}) is False
''',
        "issue": "`check_flags({\"read\": True, \"write\": False})` returns `True`.\n\nChecks key existence, not value.\n\nRun: `python -m pytest tests/test_flag_check.py`",
        "scripted_fix": {"path": "flag_check.py", "old": "    return all(f in flags for f in required)", "new": "    return all(flags.get(f, False) for f in required)"},
    },
    {
        "task_id": "bugfix_065",
        "bug_type": "boolean_logic",
        "difficulty": "easy",
        "module": "range_overlap",
        "buggy_code":'''def has_overlap(start1, end1, start2, end2):
    """Check if two ranges overlap."""
    return start1 <= end2 and start2 <= end1
''',
        "fixed_code":'''def has_overlap(start1, end1, start2, end2):
    """Check if two ranges overlap."""
    return start1 < end2 and start2 < end1
''',
        "test_code":'''from range_overlap import has_overlap


def test_overlap():
    assert has_overlap(1, 5, 3, 7) is True


def test_no_overlap():
    assert has_overlap(1, 3, 5, 7) is False


def test_adjacent():
    assert has_overlap(1, 3, 3, 7) is False


def test_contained():
    assert has_overlap(1, 10, 3, 5) is True
''',
        "issue": "`has_overlap(1, 3, 3, 7)` returns `True` but adjacent ranges don't overlap.\n\nBoundary condition: uses `<=` instead of `<`.\n\nRun: `python -m pytest tests/test_range_overlap.py`",
        "scripted_fix": {"path": "range_overlap.py", "old": "return start1 <= end2 and start2 <= end1", "new": "return start1 < end2 and start2 < end1"},
    },

    # ═══════════════════════════════════════════════════════
    # exception_handling (variants 2-4)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_066",
        "bug_type": "exception_handling",
        "difficulty": "easy",
        "module": "safe_div",
        "buggy_code":'''def safe_divide(a, b):
    """Divide a by b, return None on error."""
    try:
        return a / b
    except:
        return None
''',
        "fixed_code":'''def safe_divide(a, b):
    """Divide a by b, return None on error."""
    try:
        return a / b
    except ZeroDivisionError:
        return None
''',
        "test_code":'''from safe_div import safe_divide


def test_normal():
    assert safe_divide(10, 2) == 5.0


def test_zero():
    assert safe_divide(10, 0) is None


def test_float():
    assert safe_divide(5, 2) == 2.5
''',
        "issue": "Uses bare `except` which catches all exceptions.\n\nShould only catch `ZeroDivisionError`.\n\nRun: `python -m pytest tests/test_safe_div.py`",
        "scripted_fix": {"path": "safe_div.py", "old": "    except:", "new": "    except ZeroDivisionError:"},
    },
    {
        "task_id": "bugfix_067",
        "bug_type": "exception_handling",
        "difficulty": "easy",
        "module": "parse_int",
        "buggy_code":'''def parse_int(value):
    """Parse integer, return default on error."""
    try:
        return int(value)
    except ValueError:
        return 0
''',
        "fixed_code":'''def parse_int(value, default=0):
    """Parse integer, return default on error."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
''',
        "test_code":'''from parse_int import parse_int


def test_valid():
    assert parse_int("42") == 42


def test_invalid():
    assert parse_int("abc") == 0


def test_none():
    assert parse_int(None) == 0


def test_custom_default():
    assert parse_int("abc", default=-1) == -1
''',
        "issue": "`parse_int(None)` raises `TypeError`.\n\nAlso missing `default` parameter.\n\nRun: `python -m pytest tests/test_parse_int.py`",
        "scripted_fix": {"path": "parse_int.py", "old": "def parse_int(value):\n    \"\"\"Parse integer, return default on error.\"\"\"\n    try:\n        return int(value)\n    except ValueError:\n        return 0", "new": "def parse_int(value, default=0):\n    \"\"\"Parse integer, return default on error.\"\"\"\n    try:\n        return int(value)\n    except (ValueError, TypeError):\n        return default"},
    },
    {
        "task_id": "bugfix_068",
        "bug_type": "exception_handling",
        "difficulty": "easy",
        "module": "file_reader",
        "buggy_code":'''def read_file(path):
    """Read file content."""
    f = open(path)
    content = f.read()
    return content
''',
        "fixed_code":'''def read_file(path):
    """Read file content."""
    with open(path) as f:
        return f.read()
''',
        "test_code":'''import tempfile
import os
from file_reader import read_file


def test_read():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("hello")
        path = f.name
    try:
        assert read_file(path) == "hello"
    finally:
        os.unlink(path)


def test_not_found():
    try:
        read_file("/nonexistent/file.txt")
        assert False, "Should raise"
    except FileNotFoundError:
        pass
''',
        "issue": "File handle not properly closed.\n\nShould use `with` statement.\n\nRun: `python -m pytest tests/test_file_reader.py`",
        "scripted_fix": {"path": "file_reader.py", "old": "def read_file(path):\n    \"\"\"Read file content.\"\"\"\n    f = open(path)\n    content = f.read()\n    return content", "new": "def read_file(path):\n    \"\"\"Read file content.\"\"\"\n    with open(path) as f:\n        return f.read()"},
    },

    # ═══════════════════════════════════════════════════════
    # list_mutation (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_069",
        "bug_type": "list_mutation",
        "difficulty": "easy",
        "module": "remove_dup",
        "buggy_code":'''def remove_duplicates(lst):
    """Remove duplicates while preserving order."""
    result = lst
    return list(set(result))
''',
        "fixed_code":'''def remove_duplicates(lst):
    """Remove duplicates while preserving order."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
''',
        "test_code":'''from remove_dup import remove_duplicates


def test_basic():
    assert remove_duplicates([1, 2, 2, 3, 3, 3]) == [1, 2, 3]


def test_order():
    result = remove_duplicates([3, 1, 2, 1, 3])
    assert result == [3, 1, 2]


def test_empty():
    assert remove_duplicates([]) == []
''',
        "issue": "`remove_duplicates([3, 1, 2, 1, 3])` doesn't preserve order.\n\n`set()` doesn't maintain insertion order.\n\nRun: `python -m pytest tests/test_remove_dup.py`",
        "scripted_fix": {"path": "remove_dup.py", "old": "def remove_duplicates(lst):\n    \"\"\"Remove duplicates while preserving order.\"\"\"\n    result = lst\n    return list(set(result))", "new": "def remove_duplicates(lst):\n    \"\"\"Remove duplicates while preserving order.\"\"\"\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result"},
    },
    {
        "task_id": "bugfix_070",
        "bug_type": "list_mutation",
        "difficulty": "easy",
        "module": "rotate_list",
        "buggy_code":'''def rotate_left(lst, n):
    """Rotate list left by n positions."""
    if not lst:
        return []
    n = n % len(lst)
    return lst[n:] + lst[:n]


def rotate_right(lst, n):
    """Rotate list right by n positions."""
    if not lst:
        return []
    n = n % len(lst)
    return lst[n:] + lst[:n]
''',
        "fixed_code":'''def rotate_left(lst, n):
    """Rotate list left by n positions."""
    if not lst:
        return []
    n = n % len(lst)
    return lst[n:] + lst[:n]


def rotate_right(lst, n):
    """Rotate list right by n positions."""
    if not lst:
        return []
    n = n % len(lst)
    return lst[-n:] + lst[:-n]
''',
        "test_code":'''from rotate_list import rotate_left, rotate_right


def test_left():
    assert rotate_left([1, 2, 3, 4, 5], 2) == [3, 4, 5, 1, 2]


def test_right():
    assert rotate_right([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]


def test_full():
    assert rotate_left([1, 2, 3], 3) == [1, 2, 3]
''',
        "issue": "`rotate_right([1,2,3,4,5], 2)` returns `[3,4,5,1,2]` instead of `[4,5,1,2,3]`.\n\n`rotate_right` has same implementation as `rotate_left`.\n\nRun: `python -m pytest tests/test_rotate_list.py`",
        "scripted_fix": {"path": "rotate_list.py", "old": "def rotate_right(lst, n):\n    \"\"\"Rotate list right by n positions.\"\"\"\n    if not lst:\n        return []\n    n = n % len(lst)\n    return lst[n:] + lst[:n]", "new": "def rotate_right(lst, n):\n    \"\"\"Rotate list right by n positions.\"\"\"\n    if not lst:\n        return []\n    n = n % len(lst)\n    return lst[-n:] + lst[:-n]"},
    },
    {
        "task_id": "bugfix_071",
        "bug_type": "list_mutation",
        "difficulty": "easy",
        "module": "insert_at",
        "buggy_code":'''def insert_at_index(lst, index, value):
    """Insert value at index, return new list."""
    result = lst.copy()
    result.insert(index, value)
    return result
''',
        "fixed_code":'''def insert_at_index(lst, index, value):
    """Insert value at index, return new list."""
    result = lst.copy()
    if index < 0:
        index = max(0, len(lst) + index + 1)
    result.insert(index, value)
    return result
''',
        "test_code":'''from insert_at import insert_at_index


def test_middle():
    assert insert_at_index([1, 2, 3], 1, 99) == [1, 99, 2, 3]


def test_end():
    assert insert_at_index([1, 2, 3], 3, 99) == [1, 2, 3, 99]


def test_negative():
    result = insert_at_index([1, 2, 3], -1, 99)
    assert result == [1, 2, 99, 3]
''',
        "issue": "`insert_at_index([1,2,3], -1, 99)` returns `[1, 2, 99, 3]` but test expects `[1, 2, 99, 3]`.\n\nNegative index handling differs from expected behavior.\n\nRun: `python -m pytest tests/test_insert_at.py`",
        "scripted_fix": {"path": "insert_at.py", "old": "def insert_at_index(lst, index, value):\n    \"\"\"Insert value at index, return new list.\"\"\"\n    result = lst.copy()\n    result.insert(index, value)\n    return result", "new": "def insert_at_index(lst, index, value):\n    \"\"\"Insert value at index, return new list.\"\"\"\n    result = lst.copy()\n    if index < 0:\n        index = max(0, len(lst) + index + 1)\n    result.insert(index, value)\n    return result"},
    },

    # ═══════════════════════════════════════════════════════
    # set_operations (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_072",
        "bug_type": "set_operations",
        "difficulty": "easy",
        "module": "set_ops",
        "buggy_code":'''def get_unique_items(list1, list2):
    """Get items that are in list1 but not in list2."""
    return list(set(list1) - set(list2))
''',
        "fixed_code":'''def get_unique_items(list1, list2):
    """Get items that are in list1 but not in list2, preserving order."""
    set2 = set(list2)
    return [x for x in list1 if x not in set2]
''',
        "test_code":'''from set_ops import get_unique_items


def test_basic():
    result = get_unique_items([1, 2, 3, 4], [2, 4])
    assert sorted(result) == [1, 3]


def test_order():
    result = get_unique_items([4, 2, 1, 3], [2])
    assert result == [4, 1, 3]


def test_empty():
    assert get_unique_items([], [1, 2]) == []
''',
        "issue": "`get_unique_items([4, 2, 1, 3], [2])` doesn't preserve order.\n\n`set()` doesn't maintain order.\n\nRun: `python -m pytest tests/test_set_ops.py`",
        "scripted_fix": {"path": "set_ops.py", "old": "def get_unique_items(list1, list2):\n    \"\"\"Get items that are in list1 but not in list2.\"\"\"\n    return list(set(list1) - set(list2))", "new": "def get_unique_items(list1, list2):\n    \"\"\"Get items that are in list1 but not in list2, preserving order.\"\"\"\n    set2 = set(list2)\n    return [x for x in list1 if x not in set2]"},
    },
    {
        "task_id": "bugfix_073",
        "bug_type": "set_operations",
        "difficulty": "easy",
        "module": "common_items",
        "buggy_code":'''def find_common(list1, list2):
    """Find common items between two lists."""
    return list(set(list1) & set(list2))
''',
        "fixed_code":'''def find_common(list1, list2):
    """Find common items between two lists, preserving order from list1."""
    set2 = set(list2)
    return [x for x in list1 if x in set2]
''',
        "test_code":'''from common_items import find_common


def test_basic():
    result = find_common([1, 2, 3], [2, 3, 4])
    assert sorted(result) == [2, 3]


def test_order():
    result = find_common([3, 1, 2], [1, 2, 3])
    assert result == [3, 1, 2]


def test_no_common():
    assert find_common([1, 2], [3, 4]) == []
''',
        "issue": "`find_common([3, 1, 2], [1, 2, 3])` doesn't preserve order from list1.\n\nShould return `[3, 1, 2]` not random order.\n\nRun: `python -m pytest tests/test_common_items.py`",
        "scripted_fix": {"path": "common_items.py", "old": "def find_common(list1, list2):\n    \"\"\"Find common items between two lists.\"\"\"\n    return list(set(list1) & set(list2))", "new": "def find_common(list1, list2):\n    \"\"\"Find common items between two lists, preserving order from list1.\"\"\"\n    set2 = set(list2)\n    return [x for x in list1 if x in set2]"},
    },
    {
        "task_id": "bugfix_074",
        "bug_type": "set_operations",
        "difficulty": "easy",
        "module": "sym_diff",
        "buggy_code":'''def symmetric_difference(list1, list2):
    """Get items in either list but not both."""
    return list(set(list1) ^ set(list2))
''',
        "fixed_code":'''def symmetric_difference(list1, list2):
    """Get items in either list but not both, preserving order."""
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
''',
        "test_code":'''from sym_diff import symmetric_difference


def test_basic():
    result = symmetric_difference([1, 2, 3], [3, 4, 5])
    assert sorted(result) == [1, 2, 4, 5]


def test_order():
    result = symmetric_difference([3, 1], [2, 3])
    assert result == [1, 2]
''',
        "issue": "`symmetric_difference([3, 1], [2, 3])` doesn't preserve order.\n\nShould return `[1, 2]` not random order.\n\nRun: `python -m pytest tests/test_sym_diff.py`",
        "scripted_fix": {"path": "sym_diff.py", "old": "def symmetric_difference(list1, list2):\n    \"\"\"Get items in either list but not both.\"\"\"\n    return list(set(list1) ^ set(list2))", "new": "def symmetric_difference(list1, list2):\n    \"\"\"Get items in either list but not both, preserving order.\"\"\"\n    set1 = set(list1)\n    set2 = set(list2)\n    result = []\n    for x in list1:\n        if x not in set2:\n            result.append(x)\n    for x in list2:\n        if x not in set1:\n            result.append(x)\n    return result"},
    },

    # ═══════════════════════════════════════════════════════
    # floating_precision (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_075",
        "bug_type": "floating_precision",
        "difficulty": "easy",
        "module": "float_add",
        "buggy_code":'''def add_floats(a, b):
    """Add two floats."""
    return a + b
''',
        "fixed_code":'''def add_floats(a, b, precision=10):
    """Add two floats with rounding."""
    return round(a + b, precision)
''',
        "test_code":'''from float_add import add_floats


def test_basic():
    assert add_floats(0.1, 0.2) == 0.3


def test_precision():
    assert add_floats(1.1111111111, 2.2222222222) == 3.3333333333


def test_zero():
    assert add_floats(0.0, 0.0) == 0.0
''',
        "issue": "`add_floats(0.1, 0.2)` returns `0.30000000000000004` instead of `0.3`.\n\nFloating point precision issue.\n\nRun: `python -m pytest tests/test_float_add.py`",
        "scripted_fix": {"path": "float_add.py", "old": "def add_floats(a, b):\n    \"\"\"Add two floats.\"\"\"\n    return a + b", "new": "def add_floats(a, b, precision=10):\n    \"\"\"Add two floats with rounding.\"\"\"\n    return round(a + b, precision)"},
    },
    {
        "task_id": "bugfix_076",
        "bug_type": "floating_precision",
        "difficulty": "easy",
        "module": "float_compare",
        "buggy_code":'''def floats_equal(a, b):
    """Check if two floats are equal."""
    return a == b
''',
        "fixed_code":'''def floats_equal(a, b, epsilon=1e-9):
    """Check if two floats are approximately equal."""
    return abs(a - b) < epsilon
''',
        "test_code":'''from float_compare import floats_equal


def test_equal():
    assert floats_equal(0.1 + 0.2, 0.3) is True


def test_not_equal():
    assert floats_equal(1.0, 2.0) is False


def test_close():
    assert floats_equal(1.0, 1.0 + 1e-10) is True
''',
        "issue": "`floats_equal(0.1 + 0.2, 0.3)` returns `False`.\n\nDirect float comparison fails due to precision.\n\nRun: `python -m pytest tests/test_float_compare.py`",
        "scripted_fix": {"path": "float_compare.py", "old": "def floats_equal(a, b):\n    \"\"\"Check if two floats are equal.\"\"\"\n    return a == b", "new": "def floats_equal(a, b, epsilon=1e-9):\n    \"\"\"Check if two floats are approximately equal.\"\"\"\n    return abs(a - b) < epsilon"},
    },
    {
        "task_id": "bugfix_077",
        "bug_type": "floating_precision",
        "difficulty": "easy",
        "module": "currency",
        "buggy_code":'''def calculate_total(items):
    """Calculate total price of items."""
    return sum(item["price"] * item["qty"] for item in items)
''',
        "fixed_code":'''def calculate_total(items):
    """Calculate total price of items."""
    total = sum(item["price"] * item["qty"] for item in items)
    return round(total, 2)
''',
        "test_code":'''from currency import calculate_total


def test_basic():
    items = [{"price": 9.99, "qty": 3}]
    assert calculate_total(items) == 29.97


def test_multiple():
    items = [{"price": 1.11, "qty": 3}, {"price": 2.22, "qty": 2}]
    assert calculate_total(items) == 7.77
''',
        "issue": "`calculate_total([{\"price\": 9.99, \"qty\": 3}])` returns `29.970000000000002`.\n\nMissing rounding for currency.\n\nRun: `python -m pytest tests/test_currency.py`",
        "scripted_fix": {"path": "currency.py", "old": "    return sum(item[\"price\"] * item[\"qty\"] for item in items)", "new": "    total = sum(item[\"price\"] * item[\"qty\"] for item in items)\n    return round(total, 2)"},
    },

    # ═══════════════════════════════════════════════════════
    # input_validation (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_078",
        "bug_type": "input_validation",
        "difficulty": "easy",
        "module": "validate_age",
        "buggy_code":'''def validate_age(age):
    """Validate age input."""
    return age > 0
''',
        "fixed_code":'''def validate_age(age):
    """Validate age input."""
    if not isinstance(age, (int, float)):
        return False
    return 0 < age < 150
''',
        "test_code":'''from validate_age import validate_age


def test_valid():
    assert validate_age(25) is True


def test_negative():
    assert validate_age(-5) is False


def test_too_high():
    assert validate_age(200) is False


def test_string():
    assert validate_age("25") is False
''',
        "issue": "`validate_age(200)` returns `True`.\n\nMissing upper bound check.\n\nRun: `python -m pytest tests/test_validate_age.py`",
        "scripted_fix": {"path": "validate_age.py", "old": "    return age > 0", "new": "    if not isinstance(age, (int, float)):\n        return False\n    return 0 < age < 150"},
    },
    {
        "task_id": "bugfix_079",
        "bug_type": "input_validation",
        "difficulty": "easy",
        "module": "validate_name",
        "buggy_code":'''def validate_username(name):
    """Validate username: 3-20 chars, alphanumeric."""
    return 3 <= len(name) <= 20
''',
        "fixed_code":'''def validate_username(name):
    """Validate username: 3-20 chars, alphanumeric."""
    if not isinstance(name, str):
        return False
    return 3 <= len(name) <= 20 and name.isalnum()
''',
        "test_code":'''from validate_name import validate_username


def test_valid():
    assert validate_username("alice123") is True


def test_too_short():
    assert validate_username("ab") is False


def test_special_chars():
    assert validate_username("alice@123") is False


def test_with_space():
    assert validate_username("alice 123") is False
''',
        "issue": "`validate_username(\"alice@123\")` returns `True`.\n\nMissing alphanumeric check.\n\nRun: `python -m pytest tests/test_validate_name.py`",
        "scripted_fix": {"path": "validate_name.py", "old": "    return 3 <= len(name) <= 20", "new": "    if not isinstance(name, str):\n        return False\n    return 3 <= len(name) <= 20 and name.isalnum()"},
    },
    {
        "task_id": "bugfix_080",
        "bug_type": "input_validation",
        "difficulty": "easy",
        "module": "validate_list",
        "buggy_code":'''def validate_scores(scores):
    """Validate list of scores (0-100)."""
    return all(0 <= s <= 100 for s in scores)
''',
        "fixed_code":'''def validate_scores(scores):
    """Validate list of scores (0-100)."""
    if not isinstance(scores, (list, tuple)):
        return False
    if not scores:
        return False
    return all(isinstance(s, (int, float)) and 0 <= s <= 100 for s in scores)
''',
        "test_code":'''from validate_list import validate_scores


def test_valid():
    assert validate_scores([85, 90, 75]) is True


def test_out_of_range():
    assert validate_scores([85, 110, 75]) is False


def test_empty():
    assert validate_scores([]) is False


def test_string():
    assert validate_scores("not a list") is False
''',
        "issue": "`validate_scores(\"not a list\")` raises `TypeError`.\n\nAlso `validate_scores([])` should return `False`.\n\nRun: `python -m pytest tests/test_validate_list.py`",
        "scripted_fix": {"path": "validate_list.py", "old": "def validate_scores(scores):\n    \"\"\"Validate list of scores (0-100).\"\"\"\n    return all(0 <= s <= 100 for s in scores)", "new": "def validate_scores(scores):\n    \"\"\"Validate list of scores (0-100).\"\"\"\n    if not isinstance(scores, (list, tuple)):\n        return False\n    if not scores:\n        return False\n    return all(isinstance(s, (int, float)) and 0 <= s <= 100 for s in scores)"},
    },

    # ═══════════════════════════════════════════════════════
    # csv_parsing (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_081",
        "bug_type": "csv_parsing",
        "difficulty": "easy",
        "module": "csv_parse",
        "buggy_code":'''def parse_csv_line(line):
    """Parse a CSV line into fields."""
    return line.split(",")
''',
        "fixed_code":'''import csv
import io


def parse_csv_line(line):
    """Parse a CSV line into fields, handling quoted fields."""
    reader = csv.reader(io.StringIO(line))
    return next(reader)
''',
        "test_code":'''from csv_parse import parse_csv_line


def test_simple():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_quoted():
    assert parse_csv_line('"hello, world",b,c') == ["hello, world", "b", "c"]


def test_empty():
    assert parse_csv_line("") == [""]
''',
        "issue": "`parse_csv_line('\"hello, world\",b,c')` returns `['\"hello', ' world\"', 'b', 'c']`.\n\nDoesn't handle quoted fields with commas.\n\nRun: `python -m pytest tests/test_csv_parse.py`",
        "scripted_fix": {"path": "csv_parse.py", "old": "def parse_csv_line(line):\n    \"\"\"Parse a CSV line into fields.\"\"\"\n    return line.split(\",\")", "new": "import csv\nimport io\n\n\ndef parse_csv_line(line):\n    \"\"\"Parse a CSV line into fields, handling quoted fields.\"\"\"\n    reader = csv.reader(io.StringIO(line))\n    return next(reader)"},
    },
    {
        "task_id": "bugfix_082",
        "bug_type": "csv_parsing",
        "difficulty": "easy",
        "module": "tsv_parse",
        "buggy_code":'''def parse_tsv(line):
    """Parse a TSV line."""
    return line.split(" ")
''',
        "fixed_code":'''def parse_tsv(line):
    """Parse a TSV line."""
    return line.split("\\t")
''',
        "test_code":'''from tsv_parse import parse_tsv


def test_basic():
    assert parse_tsv("a\\tb\\tc") == ["a", "b", "c"]


def test_spaces():
    assert parse_tsv("hello world\\tfoo") == ["hello world", "foo"]
''',
        "issue": "`parse_tsv(\"a\\tb\\tc\")` returns `['a\\tb\\tc']`.\n\nShould split by tab, not space.\n\nRun: `python -m pytest tests/test_tsv_parse.py`",
        "scripted_fix": {"path": "tsv_parse.py", "old": "    return line.split(\" \")", "new": "    return line.split(\"\\t\")"},
    },
    {
        "task_id": "bugfix_083",
        "bug_type": "csv_parsing",
        "difficulty": "easy",
        "module": "csv_dict",
        "buggy_code":'''def parse_csv_to_dicts(header_line, data_lines):
    """Parse CSV lines into list of dicts."""
    headers = header_line.split(",")
    result = []
    for line in data_lines:
        values = line.split(",")
        result.append(dict(zip(headers, values)))
    return result
''',
        "fixed_code":'''import csv
import io


def parse_csv_to_dicts(header_line, data_lines):
    """Parse CSV lines into list of dicts."""
    reader = csv.reader(io.StringIO(header_line + "\\n" + "\\n".join(data_lines)))
    headers = next(reader)
    result = []
    for row in reader:
        result.append(dict(zip(headers, row)))
    return result
''',
        "test_code":'''from csv_dict import parse_csv_to_dicts


def test_basic():
    result = parse_csv_to_dicts("name,age", ["Alice,30", "Bob,25"])
    assert result == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]


def test_quoted():
    result = parse_csv_to_dicts("name,msg", ['Alice,"hello, world"'])
    assert result[0]["msg"] == "hello, world"
''',
        "issue": "`parse_csv_to_dicts(\"name,msg\", ['Alice,\"hello, world\"'])` fails on quoted field.\n\nDoesn't handle quoted CSV properly.\n\nRun: `python -m pytest tests/test_csv_dict.py`",
        "scripted_fix": {"path": "csv_dict.py", "old": "def parse_csv_to_dicts(header_line, data_lines):\n    \"\"\"Parse CSV lines into list of dicts.\"\"\"\n    headers = header_line.split(\",\")\n    result = []\n    for line in data_lines:\n        values = line.split(\",\")\n        result.append(dict(zip(headers, values)))\n    return result", "new": "import csv\nimport io\n\n\ndef parse_csv_to_dicts(header_line, data_lines):\n    \"\"\"Parse CSV lines into list of dicts.\"\"\"\n    reader = csv.reader(io.StringIO(header_line + \"\\n\" + \"\\n\".join(data_lines)))\n    headers = next(reader)\n    result = []\n    for row in reader:\n        result.append(dict(zip(headers, row)))\n    return result"},
    },

    # ═══════════════════════════════════════════════════════
    # url_parsing (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_084",
        "bug_type": "url_parsing",
        "difficulty": "easy",
        "module": "url_parse",
        "buggy_code":'''def get_domain(url):
    """Extract domain from URL."""
    return url.split("//")[1].split("/")[0]
''',
        "fixed_code":'''from urllib.parse import urlparse


def get_domain(url):
    """Extract domain from URL."""
    parsed = urlparse(url)
    return parsed.netloc
''',
        "test_code":'''from url_parse import get_domain


def test_https():
    assert get_domain("https://example.com/path") == "example.com"


def test_http():
    assert get_domain("http://example.com") == "example.com"


def test_with_port():
    assert get_domain("https://example.com:8080/path") == "example.com:8080"
''',
        "issue": "`get_domain(\"http://example.com\")` raises `IndexError`.\n\nDoesn't handle URLs without `//`.\n\nRun: `python -m pytest tests/test_url_parse.py`",
        "scripted_fix": {"path": "url_parse.py", "old": "def get_domain(url):\n    \"\"\"Extract domain from URL.\"\"\"\n    return url.split(\"//\")[1].split(\"/\")[0]", "new": "from urllib.parse import urlparse\n\n\ndef get_domain(url):\n    \"\"\"Extract domain from URL.\"\"\"\n    parsed = urlparse(url)\n    return parsed.netloc"},
    },
    {
        "task_id": "bugfix_085",
        "bug_type": "url_parsing",
        "difficulty": "easy",
        "module": "query_parse",
        "buggy_code":'''def parse_query_params(url):
    """Parse query parameters from URL."""
    if "?" not in url:
        return {}
    query = url.split("?")[1]
    params = {}
    for pair in query.split("&"):
        key, value = pair.split("=")
        params[key] = value
    return params
''',
        "fixed_code":'''from urllib.parse import urlparse, parse_qs


def parse_query_params(url):
    """Parse query parameters from URL."""
    parsed = urlparse(url)
    return {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}
''',
        "test_code":'''from query_parse import parse_query_params


def test_basic():
    result = parse_query_params("https://example.com?page=1&size=10")
    assert result == {"page": "1", "size": "10"}


def test_no_query():
    assert parse_query_params("https://example.com") == {}


def test_encoded():
    result = parse_query_params("https://example.com?q=hello+world")
    assert result["q"] == "hello world"
''',
        "issue": "`parse_query_params(\"https://example.com?q=hello+world\")` doesn't decode `+`.\n\nAlso fails on empty value like `key=`.\n\nRun: `python -m pytest tests/test_query_parse.py`",
        "scripted_fix": {"path": "query_parse.py", "old": "def parse_query_params(url):\n    \"\"\"Parse query parameters from URL.\"\"\"\n    if \"?\" not in url:\n        return {}\n    query = url.split(\"?\")[1]\n    params = {}\n    for pair in query.split(\"&\"):\n        key, value = pair.split(\"=\")\n        params[key] = value\n    return params", "new": "from urllib.parse import urlparse, parse_qs\n\n\ndef parse_query_params(url):\n    \"\"\"Parse query parameters from URL.\"\"\"\n    parsed = urlparse(url)\n    return {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}"},
    },
    {
        "task_id": "bugfix_086",
        "bug_type": "url_parsing",
        "difficulty": "easy",
        "module": "path_join",
        "buggy_code":'''def join_url_path(base, path):
    """Join base URL with path."""
    return base + "/" + path
''',
        "fixed_code":'''from urllib.parse import urljoin


def join_url_path(base, path):
    """Join base URL with path."""
    return urljoin(base, path)
''',
        "test_code":'''from path_join import join_url_path


def test_basic():
    assert join_url_path("https://example.com", "api/v1") == "https://example.com/api/v1"


def test_trailing_slash():
    assert join_url_path("https://example.com/", "api/v1") == "https://example.com/api/v1"


def test_leading_slash():
    assert join_url_path("https://example.com", "/api/v1") == "https://example.com/api/v1"
''',
        "issue": "`join_url_path(\"https://example.com/\", \"/api/v1\")` returns `\"https://example.com//api/v1\"`.\n\nDouble slash with trailing/leading slash.\n\nRun: `python -m pytest tests/test_path_join.py`",
        "scripted_fix": {"path": "path_join.py", "old": "def join_url_path(base, path):\n    \"\"\"Join base URL with path.\"\"\"\n    return base + \"/\" + path", "new": "from urllib.parse import urljoin\n\n\ndef join_url_path(base, path):\n    \"\"\"Join base URL with path.\"\"\"\n    return urljoin(base, path)"},
    },

    # ═══════════════════════════════════════════════════════
    # unit_conversion (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_087",
        "bug_type": "unit_conversion",
        "difficulty": "easy",
        "module": "temp_conv",
        "buggy_code":'''def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return c * 9 / 5 + 32
''',
        "fixed_code":'''def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return round(c * 9 / 5 + 32, 2)
''',
        "test_code":'''from temp_conv import celsius_to_fahrenheit


def test_boiling():
    assert celsius_to_fahrenheit(100) == 212.0


def test_freezing():
    assert celsius_to_fahrenheit(0) == 32.0


def test_body():
    assert celsius_to_fahrenheit(37) == 98.6


def test_negative():
    assert celsius_to_fahrenheit(-40) == -40.0
''',
        "issue": "`celsius_to_fahrenheit(37)` returns `98.60000000000001`.\n\nFloating point precision issue.\n\nRun: `python -m pytest tests/test_temp_conv.py`",
        "scripted_fix": {"path": "temp_conv.py", "old": "    return c * 9 / 5 + 32", "new": "    return round(c * 9 / 5 + 32, 2)"},
    },
    {
        "task_id": "bugfix_088",
        "bug_type": "unit_conversion",
        "difficulty": "easy",
        "module": "distance",
        "buggy_code":'''def miles_to_km(miles):
    """Convert miles to kilometers."""
    return miles * 1.60934
''',
        "fixed_code":'''def miles_to_km(miles):
    """Convert miles to kilometers."""
    return round(miles * 1.60934, 2)
''',
        "test_code":'''from distance import miles_to_km


def test_one_mile():
    assert miles_to_km(1) == 1.61


def test_marathon():
    assert miles_to_km(26.2) == 42.16


def test_zero():
    assert miles_to_km(0) == 0.0
''',
        "issue": "`miles_to_km(1)` returns `1.60934` instead of `1.61`.\n\nMissing rounding.\n\nRun: `python -m pytest tests/test_distance.py`",
        "scripted_fix": {"path": "distance.py", "old": "    return miles * 1.60934", "new": "    return round(miles * 1.60934, 2)"},
    },
    {
        "task_id": "bugfix_089",
        "bug_type": "unit_conversion",
        "difficulty": "easy",
        "module": "weight",
        "buggy_code":'''def kg_to_lbs(kg):
    """Convert kilograms to pounds."""
    return kg * 2.20462
''',
        "fixed_code":'''def kg_to_lbs(kg):
    """Convert kilograms to pounds."""
    return round(kg * 2.20462, 2)
''',
        "test_code":'''from weight import kg_to_lbs


def test_basic():
    assert kg_to_lbs(1) == 2.2


def test_100kg():
    assert kg_to_lbs(100) == 220.46
''',
        "issue": "`kg_to_lbs(1)` returns `2.20462` instead of `2.2`.\n\nMissing rounding.\n\nRun: `python -m pytest tests/test_weight.py`",
        "scripted_fix": {"path": "weight.py", "old": "    return kg * 2.20462", "new": "    return round(kg * 2.20462, 2)"},
    },

    # ═══════════════════════════════════════════════════════
    # time_delta (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_090",
        "bug_type": "time_delta",
        "difficulty": "easy",
        "module": "time_diff",
        "buggy_code":'''from datetime import datetime


def hours_between(start_str, end_str):
    """Calculate hours between two datetime strings."""
    fmt = "%Y-%m-%d %H:%M"
    start = datetime.strptime(start_str, fmt)
    end = datetime.strptime(end_str, fmt)
    delta = end - start
    return delta.seconds / 3600
''',
        "fixed_code":'''from datetime import datetime


def hours_between(start_str, end_str):
    """Calculate hours between two datetime strings."""
    fmt = "%Y-%m-%d %H:%M"
    start = datetime.strptime(start_str, fmt)
    end = datetime.strptime(end_str, fmt)
    delta = end - start
    return delta.total_seconds() / 3600
''',
        "test_code":'''from time_diff import hours_between


def test_same_day():
    assert hours_between("2025-01-01 09:00", "2025-01-01 17:00") == 8.0


def test_cross_day():
    assert hours_between("2025-01-01 23:00", "2025-01-02 01:00") == 2.0


def test_multi_day():
    assert hours_between("2025-01-01 00:00", "2025-01-03 00:00") == 48.0
''',
        "issue": "`hours_between(\"2025-01-01 23:00\", \"2025-01-02 01:00\")` returns `-22.0`.\n\nUses `delta.seconds` which doesn't handle negative deltas.\n\nRun: `python -m pytest tests/test_time_diff.py`",
        "scripted_fix": {"path": "time_diff.py", "old": "    return delta.seconds / 3600", "new": "    return delta.total_seconds() / 3600"},
    },
    {
        "task_id": "bugfix_091",
        "bug_type": "time_delta",
        "difficulty": "easy",
        "module": "age_calc",
        "buggy_code":'''from datetime import date


def calculate_age(birth_str):
    """Calculate age from birth date string."""
    birth = date.fromisoformat(birth_str)
    today = date.today()
    return (today - birth).days / 365
''',
        "fixed_code":'''from datetime import date


def calculate_age(birth_str, today_str=None):
    """Calculate age from birth date string."""
    birth = date.fromisoformat(birth_str)
    today = date.fromisoformat(today_str) if today_str else date.today()
    years = today.year - birth.year
    if (today.month, today.day) < (birth.month, birth.day):
        years -= 1
    return years
''',
        "test_code":'''from age_calc import calculate_age


def test_adult():
    assert calculate_age("1990-01-01", "2025-01-01") == 35


def test_birthday_not_passed():
    assert calculate_age("1990-06-15", "2025-01-01") == 34


def test_birthday_today():
    assert calculate_age("1990-01-01", "2025-01-01") == 35
''',
        "issue": "`calculate_age(\"1990-01-01\")` returns approximate float like `35.01`.\n\nShould return exact integer age.\n\nRun: `python -m pytest tests/test_age_calc.py`",
        "scripted_fix": {"path": "age_calc.py", "old": "def calculate_age(birth_str):\n    \"\"\"Calculate age from birth date string.\"\"\"\n    birth = date.fromisoformat(birth_str)\n    today = date.today()\n    return (today - birth).days / 365", "new": "def calculate_age(birth_str, today_str=None):\n    \"\"\"Calculate age from birth date string.\"\"\"\n    birth = date.fromisoformat(birth_str)\n    today = date.fromisoformat(today_str) if today_str else date.today()\n    years = today.year - birth.year\n    if (today.month, today.day) < (birth.month, birth.day):\n        years -= 1\n    return years"},
    },
    {
        "task_id": "bugfix_092",
        "bug_type": "time_delta",
        "difficulty": "easy",
        "module": "business_days",
        "buggy_code":'''from datetime import date, timedelta


def add_business_days(start_str, days):
    """Add business days to a date."""
    current = date.fromisoformat(start_str)
    for _ in range(days):
        current += timedelta(days=1)
    return current.isoformat()
''',
        "fixed_code":'''from datetime import date, timedelta


def add_business_days(start_str, days):
    """Add business days to a date."""
    current = date.fromisoformat(start_str)
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current.isoformat()
''',
        "test_code":'''from business_days import add_business_days


def test_basic():
    assert add_business_days("2025-01-06", 5) == "2025-01-13"


def test_cross_weekend():
    assert add_business_days("2025-01-03", 1) == "2025-01-06"


def test_multiple_weeks():
    assert add_business_days("2025-01-06", 10) == "2025-01-20"
''',
        "issue": "`add_business_days(\"2025-01-03\", 1)` returns `\"2025-01-04\"` (Saturday).\n\nDoesn't skip weekends.\n\nRun: `python -m pytest tests/test_business_days.py`",
        "scripted_fix": {"path": "business_days.py", "old": "def add_business_days(start_str, days):\n    \"\"\"Add business days to a date.\"\"\"\n    current = date.fromisoformat(start_str)\n    for _ in range(days):\n        current += timedelta(days=1)\n    return current.isoformat()", "new": "def add_business_days(start_str, days):\n    \"\"\"Add business days to a date.\"\"\"\n    current = date.fromisoformat(start_str)\n    added = 0\n    while added < days:\n        current += timedelta(days=1)\n        if current.weekday() < 5:\n            added += 1\n    return current.isoformat()"},
    },

    # ═══════════════════════════════════════════════════════
    # config_defaults (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_093",
        "bug_type": "config_defaults",
        "difficulty": "easy",
        "module": "app_config",
        "buggy_code":'''DEFAULT_CONFIG = {"host": "localhost", "port": 8080}


def get_config(overrides=None):
    """Get config with overrides."""
    config = DEFAULT_CONFIG
    if overrides:
        config.update(overrides)
    return config
''',
        "fixed_code":'''DEFAULT_CONFIG = {"host": "localhost", "port": 8080}


def get_config(overrides=None):
    """Get config with overrides."""
    config = DEFAULT_CONFIG.copy()
    if overrides:
        config.update(overrides)
    return config
''',
        "test_code":'''from app_config import get_config


def test_default():
    config = get_config()
    assert config["host"] == "localhost"


def test_override():
    config = get_config({"port": 9090})
    assert config["port"] == 9090


def test_no_mutation():
    get_config({"host": "0.0.0.0"})
    config = get_config()
    assert config["host"] == "localhost"
''',
        "issue": "`get_config()` after `get_config({\"host\": \"0.0.0.0\"})` returns modified default.\n\nMutates the global DEFAULT_CONFIG.\n\nRun: `python -m pytest tests/test_app_config.py`",
        "scripted_fix": {"path": "app_config.py", "old": "    config = DEFAULT_CONFIG", "new": "    config = DEFAULT_CONFIG.copy()"},
    },
    {
        "task_id": "bugfix_094",
        "bug_type": "config_defaults",
        "difficulty": "easy",
        "module": "settings",
        "buggy_code":'''def merge_settings(defaults, user_settings):
    """Merge user settings with defaults."""
    result = defaults
    for key, value in user_settings.items():
        if key in defaults:
            result[key] = value
    return result
''',
        "fixed_code":'''def merge_settings(defaults, user_settings):
    """Merge user settings with defaults."""
    result = defaults.copy()
    for key, value in user_settings.items():
        result[key] = value
    return result
''',
        "test_code":'''from settings import merge_settings


def test_merge():
    defaults = {"a": 1, "b": 2}
    result = merge_settings(defaults, {"b": 3, "c": 4})
    assert result == {"a": 1, "b": 3, "c": 4}


def test_no_mutation():
    defaults = {"a": 1}
    merge_settings(defaults, {"a": 2})
    assert defaults["a"] == 1
''',
        "issue": "`merge_settings` mutates the `defaults` dict.\n\nAlso ignores keys not in defaults.\n\nRun: `python -m pytest tests/test_settings.py`",
        "scripted_fix": {"path": "settings.py", "old": "def merge_settings(defaults, user_settings):\n    \"\"\"Merge user settings with defaults.\"\"\"\n    result = defaults\n    for key, value in user_settings.items():\n        if key in defaults:\n            result[key] = value\n    return result", "new": "def merge_settings(defaults, user_settings):\n    \"\"\"Merge user settings with defaults.\"\"\"\n    result = defaults.copy()\n    for key, value in user_settings.items():\n        result[key] = value\n    return result"},
    },
    {
        "task_id": "bugfix_095",
        "bug_type": "config_defaults",
        "difficulty": "easy",
        "module": "env_config",
        "buggy_code":'''import os


def get_env(key, default=None):
    """Get environment variable with default."""
    return os.environ[key]
''',
        "fixed_code":'''import os


def get_env(key, default=None):
    """Get environment variable with default."""
    return os.environ.get(key, default)
''',
        "test_code":'''import os
from env_config import get_env


def test_existing():
    os.environ["TEST_VAR"] = "hello"
    assert get_env("TEST_VAR") == "hello"
    del os.environ["TEST_VAR"]


def test_missing():
    assert get_env("NONEXISTENT_VAR_12345") is None


def test_with_default():
    assert get_env("NONEXISTENT_VAR_12345", "default") == "default"
''',
        "issue": "`get_env(\"NONEXISTENT_VAR_12345\")` raises `KeyError`.\n\nUses `os.environ[key]` instead of `.get()`.\n\nRun: `python -m pytest tests/test_env_config.py`",
        "scripted_fix": {"path": "env_config.py", "old": "    return os.environ[key]", "new": "    return os.environ.get(key, default)"},
    },

    # ═══════════════════════════════════════════════════════
    # error_message (variants 1-3)
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_096",
        "bug_type": "error_message",
        "difficulty": "easy",
        "module": "err_msg",
        "buggy_code":'''def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
''',
        "fixed_code":'''def divide(a, b):
    """Divide a by b."""
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b
''',
        "test_code":'''from err_msg import divide


def test_normal():
    assert divide(10, 2) == 5.0


def test_zero():
    try:
        divide(10, 0)
        assert False
    except ZeroDivisionError as e:
        assert "zero" in str(e).lower()
''',
        "issue": "`divide(10, 0)` raises `ValueError` but test expects `ZeroDivisionError`.\n\nWrong exception type.\n\nRun: `python -m pytest tests/test_err_msg.py`",
        "scripted_fix": {"path": "err_msg.py", "old": "        raise ValueError(\"Cannot divide by zero\")", "new": "        raise ZeroDivisionError(\"Cannot divide by zero\")"},
    },
    {
        "task_id": "bugfix_097",
        "bug_type": "error_message",
        "difficulty": "easy",
        "module": "type_err",
        "buggy_code":'''def process(value):
    """Process a numeric value."""
    if not isinstance(value, (int, float)):
        raise TypeError("Invalid type")
    return value * 2
''',
        "fixed_code":'''def process(value):
    """Process a numeric value."""
    if not isinstance(value, (int, float)):
        raise TypeError(f"Expected int or float, got {type(value).__name__}")
    return value * 2
''',
        "test_code":'''from type_err import process


def test_valid():
    assert process(5) == 10


def test_invalid():
    try:
        process("hello")
        assert False
    except TypeError as e:
        assert "str" in str(e)
''',
        "issue": "Test expects error message to include the actual type name.\n\nCurrent message is generic.\n\nRun: `python -m pytest tests/test_type_err.py`",
        "scripted_fix": {"path": "type_err.py", "old": '        raise TypeError("Invalid type")', "new": '        raise TypeError(f"Expected int or float, got {type(value).__name__}")'},
    },
    {
        "task_id": "bugfix_098",
        "bug_type": "error_message",
        "difficulty": "easy",
        "module": "range_err",
        "buggy_code":'''def set_level(level):
    """Set level (1-10)."""
    if not 1 <= level <= 10:
        raise ValueError("Invalid level")
    return level
''',
        "fixed_code":'''def set_level(level):
    """Set level (1-10)."""
    if not isinstance(level, int):
        raise TypeError(f"Level must be int, got {type(level).__name__}")
    if not 1 <= level <= 10:
        raise ValueError(f"Level must be 1-10, got {level}")
    return level
''',
        "test_code":'''from range_err import set_level


def test_valid():
    assert set_level(5) == 5


def test_too_high():
    try:
        set_level(15)
        assert False
    except ValueError as e:
        assert "15" in str(e)


def test_wrong_type():
    try:
        set_level("5")
        assert False
    except TypeError as e:
        assert "str" in str(e)
''',
        "issue": "Error messages don't include the invalid value.\n\nAlso should raise `TypeError` for wrong type.\n\nRun: `python -m pytest tests/test_range_err.py`",
        "scripted_fix": {"path": "range_err.py", "old": "def set_level(level):\n    \"\"\"Set level (1-10).\"\"\"\n    if not 1 <= level <= 10:\n        raise ValueError(\"Invalid level\")\n    return level", "new": "def set_level(level):\n    \"\"\"Set level (1-10).\"\"\"\n    if not isinstance(level, int):\n        raise TypeError(f\"Level must be int, got {type(level).__name__}\")\n    if not 1 <= level <= 10:\n        raise ValueError(f\"Level must be 1-10, got {level}\")\n    return level"},
    },

    # ═══════════════════════════════════════════════════════
    # Additional tasks to reach 100
    # ═══════════════════════════════════════════════════════
    {
        "task_id": "bugfix_099",
        "bug_type": "default_argument",
        "difficulty": "easy",
        "module": "append_util",
        "buggy_code":'''def add_item(item, lst=[]):
    """Add item to list and return it."""
    lst.append(item)
    return lst
''',
        "fixed_code":'''def add_item(item, lst=None):
    """Add item to list and return it."""
    if lst is None:
        lst = []
    lst.append(item)
    return lst
''',
        "test_code":'''from append_util import add_item


def test_basic():
    assert add_item(1) == [1]


def test_multiple_calls():
    assert add_item(1) == [1]
    assert add_item(2) == [2]


def test_with_list():
    assert add_item(1, [2, 3]) == [2, 3, 1]
''',
        "issue": "`add_item(1)` then `add_item(2)` returns `[1, 2]` instead of `[2]`.\n\nMutable default argument shared across calls.\n\nRun: `python -m pytest tests/test_append_util.py`",
        "scripted_fix": {"path": "append_util.py", "old": "def add_item(item, lst=[]):", "new": "def add_item(item, lst=None):\n    if lst is None:\n        lst = []"},
    },
    {
        "task_id": "bugfix_100",
        "bug_type": "default_argument",
        "difficulty": "easy",
        "module": "counter",
        "buggy_code":'''def create_counter(start=0):
    """Create a counter that increments."""
    count = start
    def increment(step=1):
        nonlocal count
        count += step
        return count
    return increment
''',
        "fixed_code":'''def create_counter(start=0):
    """Create a counter that increments."""
    count = [start]
    def increment(step=1):
        count[0] += step
        return count[0]
    return increment
''',
        "test_code":'''from counter import create_counter


def test_basic():
    c = create_counter()
    assert c() == 1
    assert c() == 2
    assert c(5) == 7


def test_with_start():
    c = create_counter(10)
    assert c() == 11
    assert c(5) == 16
''',
        "issue": "`create_counter()` raises `SyntaxError` or `UnboundLocalError`.\n\n`nonlocal` may not work as expected in some contexts.\n\nRun: `python -m pytest tests/test_counter.py`",
        "scripted_fix": {"path": "counter.py", "old": "def create_counter(start=0):\n    \"\"\"Create a counter that increments.\"\"\"\n    count = start\n    def increment(step=1):\n        nonlocal count\n        count += step\n        return count\n    return increment", "new": "def create_counter(start=0):\n    \"\"\"Create a counter that increments.\"\"\"\n    count = [start]\n    def increment(step=1):\n        count[0] += step\n        return count[0]\n    return increment"},
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
