"""Generate benchmark tasks (bugfix_011 .. bugfix_030)."""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    # ── 011 string_split_join ──
    {
        "task_id": "bugfix_011",
        "bug_type": "string_split_join",
        "difficulty": "easy",
        "module": "csv_utils",
        "buggy_code": '''def csv_to_list(csv_string):
    """Convert a comma-separated string to a list of stripped items."""
    return csv_string.split(",")
''',
        "fixed_code": '''def csv_to_list(csv_string):
    """Convert a comma-separated string to a list of stripped items."""
    return [item.strip() for item in csv_string.split(",")]
''',
        "test_code": '''from csv_utils import csv_to_list


def test_csv_to_list_basic():
    assert csv_to_list("a,b,c") == ["a", "b", "c"]


def test_csv_to_list_with_spaces():
    assert csv_to_list("hello , world , foo") == ["hello", "world", "foo"]


def test_csv_to_list_single():
    assert csv_to_list("only") == ["only"]
''',
        "issue": "`csv_to_list` does not strip whitespace from items.\n\n`csv_to_list(\"a , b , c\")` should return `[\"a\", \"b\", \"c\"]` not `[\"a \", \" b \", \" c\"]`.\n\nRun: `python -m pytest tests/test_csv_utils.py`",
        "scripted_fix": {"path": "csv_utils.py", "old": 'return csv_string.split(",")', "new": 'return [item.strip() for item in csv_string.split(",")]'},
    },
    # ── 012 default_argument ──
    {
        "task_id": "bugfix_012",
        "bug_type": "default_argument",
        "difficulty": "easy",
        "module": "greet",
        "buggy_code": '''def greet(name, greeting="Hello"):
    return greeting + ", " + name + "!"


def greet_many(names, seen=None):
    if seen is None:
        seen = []
    result = []
    for n in names:
        if n not in seen:
            result.append(greet(n))
            seen.append(n)
    return result
''',
        "fixed_code": '''def greet(name, greeting="Hello"):
    return greeting + ", " + name + "!"


def greet_many(names, seen=None):
    if seen is None:
        seen = []
    result = []
    for n in names:
        if n not in seen:
            result.append(greet(n))
            seen.append(n)
    return result
''',
        "test_code": '''from greet import greet_many


def test_greet_many_unique():
    assert greet_many(["Alice", "Bob"]) == ["Hello, Alice!", "Hello, Bob!"]


def test_greet_many_deduplicates():
    assert greet_many(["Alice", "Bob", "Alice"]) == ["Hello, Alice!", "Hello, Bob!"]


def test_greet_many_with_seen():
    assert greet_many(["Alice", "Bob"], seen=["Alice"]) == ["Hello, Bob!"]
''',
        "issue": "`greet_many` uses a mutable default argument `seen=[]` which is shared across calls.\n\n`greet_many([\"Alice\"], seen=[\"Alice\"])` should return `[]` but may behave incorrectly with the mutable default.\n\nRun: `python -m pytest tests/test_greet.py`",
        "scripted_fix": {"path": "greet.py", "old": "def greet_many(names, seen=[]):", "new": "def greet_many(names, seen=None):\n    if seen is None:\n        seen = []"},
    },
    # ── 013 case_sensitivity ──
    {
        "task_id": "bugfix_013",
        "bug_type": "case_sensitivity",
        "difficulty": "easy",
        "module": "username",
        "buggy_code": '''def is_valid_username(username):
    """Username must be 3-15 chars, alphanumeric only."""
    if not (3 <= len(username) <= 15):
        return False
    for ch in username:
        if not (ch.isalpha() or ch.isdigit()):
            return False
    return True


def normalize_username(username):
    return username
''',
        "fixed_code": '''def is_valid_username(username):
    """Username must be 3-15 chars, alphanumeric only."""
    if not (3 <= len(username) <= 15):
        return False
    for ch in username:
        if not (ch.isalpha() or ch.isdigit()):
            return False
    return True


def normalize_username(username):
    return username.lower()
''',
        "test_code": '''from username import is_valid_username, normalize_username


def test_valid_username():
    assert is_valid_username("alice") is True


def test_invalid_too_short():
    assert is_valid_username("ab") is False


def test_normalize_lowercases():
    assert normalize_username("Alice") == "alice"


def test_normalize_already_lower():
    assert normalize_username("bob") == "bob"


def test_normalize_mixed_case():
    assert normalize_username("CharlieBrown") == "charliebrown"
''',
        "issue": "`normalize_username` does not lowercase the username.\n\n`normalize_username(\"Alice\")` should return `\"alice\"`.\n\nRun: `python -m pytest tests/test_username.py`",
        "scripted_fix": {"path": "username.py", "old": "def normalize_username(username):\n    return username", "new": "def normalize_username(username):\n    return username.lower()"},
    },
    # ── 014 path_handling ──
    {
        "task_id": "bugfix_014",
        "bug_type": "path_handling",
        "difficulty": "easy",
        "module": "path_utils",
        "buggy_code": '''def join_path(base, *parts):
    result = base
    for p in parts:
        result = result + "/" + p
    return result
''',
        "fixed_code": '''def join_path(base, *parts):
    result = base
    for p in parts:
        result = result.rstrip("/") + "/" + p.lstrip("/")
    return result
''',
        "test_code": '''from path_utils import join_path


def test_join_simple():
    assert join_path("home", "user") == "home/user"


def test_join_trailing_slash():
    assert join_path("home/", "user") == "home/user"


def test_join_leading_slash():
    assert join_path("home", "/user") == "home/user"


def test_join_multiple_parts():
    assert join_path("/home/", "/user/", "/docs") == "/home/user/docs"
''',
        "issue": "`join_path` does not handle extra slashes correctly.\n\n`join_path(\"home/\", \"user\")` returns `\"home//user\"` instead of `\"home/user\"`.\n\nRun: `python -m pytest tests/test_path_utils.py`",
        "scripted_fix": {"path": "path_utils.py", "old": 'result = result + "/" + p', "new": 'result = result.rstrip("/") + "/" + p.lstrip("/")'},
    },
    # ── 015 json_serialization ──
    {
        "task_id": "bugfix_015",
        "bug_type": "json_serialization",
        "difficulty": "easy",
        "module": "json_config",
        "buggy_code": '''import json


def save_config(data, path):
    with open(path, "w") as f:
        json.dump(data, f)


def load_config(path):
    with open(path) as f:
        return json.load(f)


def merge_configs(base, override):
    result = base
    result.update(override)
    return result
''',
        "fixed_code": '''import json


def save_config(data, path):
    with open(path, "w") as f:
        json.dump(data, f)


def load_config(path):
    with open(path) as f:
        return json.load(f)


def merge_configs(base, override):
    result = dict(base)
    result.update(override)
    return result
''',
        "test_code": '''from json_config import merge_configs


def test_merge_basic():
    base = {"a": 1, "b": 2}
    override = {"b": 3, "c": 4}
    merged = merge_configs(base, override)
    assert merged == {"a": 1, "b": 3, "c": 4}


def test_merge_does_not_mutate_base():
    base = {"a": 1, "b": 2}
    override = {"b": 3}
    merge_configs(base, override)
    assert base == {"a": 1, "b": 2}
''',
        "issue": "`merge_configs` mutates the `base` dict in-place.\n\nAfter `merge_configs(base, override)`, the original `base` should remain unchanged.\n\nRun: `python -m pytest tests/test_json_config.py`",
        "scripted_fix": {"path": "json_config.py", "old": "result = base", "new": "result = dict(base)"},
    },
    # ── 016 sorting_key ──
    {
        "task_id": "bugfix_016",
        "bug_type": "sorting_key",
        "difficulty": "easy",
        "module": "sort_utils",
        "buggy_code": '''def sort_by_score(items):
    """Sort list of dicts by 'score' descending."""
    return sorted(items, key=lambda x: x["score"])
''',
        "fixed_code": '''def sort_by_score(items):
    """Sort list of dicts by 'score' descending."""
    return sorted(items, key=lambda x: x["score"], reverse=True)
''',
        "test_code": '''from sort_utils import sort_by_score


def test_sort_descending():
    items = [{"name": "a", "score": 10}, {"name": "b", "score": 30}, {"name": "c", "score": 20}]
    result = sort_by_score(items)
    assert [r["name"] for r in result] == ["b", "c", "a"]


def test_sort_empty():
    assert sort_by_score([]) == []
''',
        "issue": "`sort_by_score` sorts ascending instead of descending.\n\n`sort_by_score` should return items ordered by score from highest to lowest.\n\nRun: `python -m pytest tests/test_sort_utils.py`",
        "scripted_fix": {"path": "sort_utils.py", "old": 'return sorted(items, key=lambda x: x["score"])', "new": 'return sorted(items, key=lambda x: x["score"], reverse=True)'},
    },
    # ── 017 deduplication ──
    {
        "task_id": "bugfix_017",
        "bug_type": "deduplication",
        "difficulty": "easy",
        "module": "dedup",
        "buggy_code": '''def remove_duplicates(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def unique_by_key(items, key):
    seen = set()
    result = []
    for item in items:
        k = item[key]
        if k not in seen:
            result.append(item)
            seen.add(k)
    return result
''',
        "fixed_code": '''def remove_duplicates(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def unique_by_key(items, key):
    seen = set()
    result = []
    for item in items:
        k = item[key]
        if k not in seen:
            result.append(item)
            seen.add(str(k))
    return result
''',
        "test_code": '''from dedup import unique_by_key


def test_unique_basic():
    items = [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}, {"id": 1, "name": "c"}]
    result = unique_by_key(items, "id")
    assert len(result) == 2
    assert result[0]["name"] == "a"
    assert result[1]["name"] == "b"


def test_unique_mixed_types():
    items = [{"id": 1}, {"id": "1"}, {"id": 2}]
    result = unique_by_key(items, "id")
    assert len(result) == 2
''',
        "issue": "`unique_by_key` considers `1` and `\"1\"` as the same key because `set()` comparison is type-insensitive in some edge cases.\n\n`unique_by_key([{\"id\": 1}, {\"id\": \"1\"}, {\"id\": 2}], \"id\")` should return all 3 items since `1 != \"1\"`.\n\nRun: `python -m pytest tests/test_dedup.py`",
        "scripted_fix": {"path": "dedup.py", "old": "seen.add(k)", "new": "seen.add(str(k))"},
    },
    # ── 018 rounding ──
    {
        "task_id": "bugfix_018",
        "bug_type": "rounding",
        "difficulty": "easy",
        "module": "finance",
        "buggy_code": '''def calculate_tax(amount, rate=0.1):
    return amount * rate


def round_price(price):
    return round(price)
''',
        "fixed_code": '''def calculate_tax(amount, rate=0.1):
    return amount * rate


def round_price(price):
    return round(price, 2)
''',
        "test_code": '''from finance import round_price


def test_round_whole():
    assert round_price(10.0) == 10.0


def test_round_two_decimals():
    assert round_price(10.567) == 10.57


def test_round_one_decimal():
    assert round_price(10.5) == 10.5


def test_round_zero():
    assert round_price(0.0) == 0.0
''',
        "issue": "`round_price` rounds to integer instead of 2 decimal places.\n\n`round_price(10.567)` should return `10.57` not `11`.\n\nRun: `python -m pytest tests/test_finance.py`",
        "scripted_fix": {"path": "finance.py", "old": "return round(price)", "new": "return round(price, 2)"},
    },
    # ── 019 boolean_logic ──
    {
        "task_id": "bugfix_019",
        "bug_type": "boolean_logic",
        "difficulty": "easy",
        "module": "access",
        "buggy_code": '''def can_access(user_role, is_admin, resource_owner_id, user_id):
    if is_admin or user_role == "editor":
        return True
    if resource_owner_id == user_id:
        return True
    return False
''',
        "fixed_code": '''def can_access(user_role, is_admin, resource_owner_id, user_id):
    if is_admin:
        return True
    if user_role == "editor" and resource_owner_id == user_id:
        return True
    if resource_owner_id == user_id:
        return True
    return False
''',
        "test_code": '''from access import can_access


def test_admin_can_access():
    assert can_access("viewer", True, 1, 2) is True


def test_owner_can_access():
    assert can_access("viewer", False, 5, 5) is True


def test_editor_non_owner_cannot_access():
    assert can_access("editor", False, 1, 2) is False


def test_viewer_non_owner_cannot_access():
    assert can_access("viewer", False, 1, 2) is False
''',
        "issue": "`can_access` gives editors access to any resource, not just their own.\n\nAn editor who is NOT the resource owner should NOT have access.\n\nRun: `python -m pytest tests/test_access.py`",
        "scripted_fix": {"path": "access.py", "old": 'if is_admin or user_role == "editor":\n        return True', "new": 'if is_admin:\n        return True\n    if user_role == "editor" and resource_owner_id == user_id:\n        return True'},
    },
    # ── 020 exception_handling ──
    {
        "task_id": "bugfix_020",
        "bug_type": "exception_handling",
        "difficulty": "easy",
        "module": "safe_ops",
        "buggy_code": '''def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return 0


def safe_int(value):
    return int(value)
''',
        "fixed_code": '''def safe_divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return 0


def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
''',
        "test_code": '''from safe_ops import safe_int


def test_safe_int_normal():
    assert safe_int("42") == 42


def test_safe_int_invalid():
    assert safe_int("abc") == 0


def test_safe_int_none():
    assert safe_int(None) == 0


def test_safe_int_float_string():
    assert safe_int("3.14") == 0
''',
        "issue": "`safe_int` does not handle invalid input — it raises an exception instead of returning 0.\n\n`safe_int(\"abc\")` should return `0`, not raise `ValueError`.\n\nRun: `python -m pytest tests/test_safe_ops.py`",
        "scripted_fix": {"path": "safe_ops.py", "old": "def safe_int(value):\n    return int(value)", "new": "def safe_int(value):\n    try:\n        return int(value)\n    except (ValueError, TypeError):\n        return 0"},
    },
    # ── 021 boundary_condition (2nd) ──
    {
        "task_id": "bugfix_021",
        "bug_type": "boundary_condition",
        "difficulty": "easy",
        "module": "discount",
        "buggy_code": '''def get_discount(quantity):
    if quantity > 100:
        return 0.20
    if quantity > 50:
        return 0.10
    return 0.0
''',
        "fixed_code": '''def get_discount(quantity):
    if quantity >= 100:
        return 0.20
    if quantity >= 50:
        return 0.10
    return 0.0
''',
        "test_code": '''from discount import get_discount


def test_below_50():
    assert get_discount(10) == 0.0


def test_exactly_50():
    assert get_discount(50) == 0.10


def test_exactly_100():
    assert get_discount(100) == 0.20


def test_above_100():
    assert get_discount(200) == 0.20
''',
        "issue": "`get_discount` uses `>` instead of `>=` for boundary checks.\n\n`get_discount(50)` should return `0.10` and `get_discount(100)` should return `0.20`.\n\nRun: `python -m pytest tests/test_discount.py`",
        "scripted_fix": {"path": "discount.py", "old": "if quantity > 100:", "new": "if quantity >= 100:"},
    },
    # ── 022 type_conversion (2nd) ──
    {
        "task_id": "bugfix_022",
        "bug_type": "type_conversion",
        "difficulty": "easy",
        "module": "counter",
        "buggy_code": '''def increment_all(counts):
    result = {}
    for key, value in counts.items():
        result[key] = value + 1
    return result
''',
        "fixed_code": '''def increment_all(counts):
    result = {}
    for key, value in counts.items():
        result[key] = int(value) + 1
    return result
''',
        "test_code": '''from counter import increment_all


def test_increment_ints():
    assert increment_all({"a": 1, "b": 2}) == {"a": 2, "b": 3}


def test_increment_strings():
    assert increment_all({"a": "1", "b": "2"}) == {"a": 2, "b": 3}


def test_increment_empty():
    assert increment_all({}) == {}
''',
        "issue": "`increment_all` fails when values are strings.\n\n`increment_all({\"a\": \"1\"})` should return `{\"a\": 2}` by converting to int first.\n\nRun: `python -m pytest tests/test_counter.py`",
        "scripted_fix": {"path": "counter.py", "old": "result[key] = value + 1", "new": "result[key] = int(value) + 1"},
    },
    # ── 023 dict_key (2nd) ──
    {
        "task_id": "bugfix_023",
        "bug_type": "dict_key",
        "difficulty": "easy",
        "module": "config_reader",
        "buggy_code": '''def get_setting(config, key, default=None):
    return config[key]
''',
        "fixed_code": '''def get_setting(config, key, default=None):
    return config.get(key, default)
''',
        "test_code": '''from config_reader import get_setting


def test_existing_key():
    assert get_setting({"host": "localhost"}, "host") == "localhost"


def test_missing_key_returns_default():
    assert get_setting({"host": "localhost"}, "port") is None


def test_missing_key_with_custom_default():
    assert get_setting({"host": "localhost"}, "port", 8080) == 8080
''',
        "issue": "`get_setting` raises `KeyError` instead of returning the default for missing keys.\n\n`get_setting({}, \"port\")` should return `None`, not raise `KeyError`.\n\nRun: `python -m pytest tests/test_config_reader.py`",
        "scripted_fix": {"path": "config_reader.py", "old": "return config[key]", "new": "return config.get(key, default)"},
    },
    # ── 024 off_by_one (2nd) ──
    {
        "task_id": "bugfix_024",
        "bug_type": "off_by_one",
        "difficulty": "easy",
        "module": "pager",
        "buggy_code": '''def get_page(items, page_num, page_size=10):
    start = page_num * page_size
    end = start + page_size
    return items[start:end]
''',
        "fixed_code": '''def get_page(items, page_num, page_size=10):
    start = (page_num - 1) * page_size
    end = start + page_size
    return items[start:end]
''',
        "test_code": '''from pager import get_page


def test_first_page():
    items = list(range(25))
    assert get_page(items, 1, 10) == list(range(10))


def test_second_page():
    items = list(range(25))
    assert get_page(items, 2, 10) == list(range(10, 20))


def test_last_partial_page():
    items = list(range(25))
    assert get_page(items, 3, 10) == list(range(20, 25))
''',
        "issue": "`get_page` is off by one — page 1 returns the second page instead of the first.\n\n`get_page(items, 1)` should return items 0-9, not 10-19.\n\nRun: `python -m pytest tests/test_pager.py`",
        "scripted_fix": {"path": "pager.py", "old": "start = page_num * page_size", "new": "start = (page_num - 1) * page_size"},
    },
    # ── 025 none_handling (2nd) ──
    {
        "task_id": "bugfix_025",
        "bug_type": "none_handling",
        "difficulty": "easy",
        "module": "string_helper",
        "buggy_code": '''def first_word(text):
    return text.split()[0]


def safe_first_word(text):
    return first_word(text)
''',
        "fixed_code": '''def first_word(text):
    return text.split()[0]


def safe_first_word(text):
    if not text or not text.strip():
        return ""
    return first_word(text)
''',
        "test_code": '''from string_helper import safe_first_word


def test_normal():
    assert safe_first_word("hello world") == "hello"


def test_empty_string():
    assert safe_first_word("") == ""


def test_none():
    assert safe_first_word(None) == ""


def test_whitespace_only():
    assert safe_first_word("   ") == ""
''',
        "issue": "`safe_first_word` crashes on empty/None input.\n\n`safe_first_word(\"\")` and `safe_first_word(None)` should return `\"\"`.\n\nRun: `python -m pytest tests/test_string_helper.py`",
        "scripted_fix": {"path": "string_helper.py", "old": "def safe_first_word(text):\n    return first_word(text)", "new": "def safe_first_word(text):\n    if not text or not text.strip():\n        return \"\"\n    return first_word(text)"},
    },
    # ── 026 regex (2nd) ──
    {
        "task_id": "bugfix_026",
        "bug_type": "regex",
        "difficulty": "easy",
        "module": "validator",
        "buggy_code": '''import re


def is_valid_email(email):
    pattern = r"^[\\w.-]+@[\\w.-]+\\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
''',
        "fixed_code": '''import re


def is_valid_email(email):
    pattern = r"^[\\w.+-]+@[\\w.-]+\\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))
''',
        "test_code": '''from validator import is_valid_email


def test_valid_email():
    assert is_valid_email("user@example.com") is True


def test_invalid_no_at():
    assert is_valid_email("userexample.com") is False


def test_email_with_plus():
    assert is_valid_email("user+tag@example.com") is True


def test_email_with_dot():
    assert is_valid_email("first.last@example.com") is True
''',
        "issue": "`is_valid_email` rejects valid emails containing `+` in the local part.\n\n`is_valid_email(\"user+tag@example.com\")` should return `True`.\n\nRun: `python -m pytest tests/test_validator.py`",
        "scripted_fix": {"path": "validator.py", "old": 'pattern = r"^[\\\\w.-]+@[\\\\w.-]+\\\\.[a-zA-Z]{2,}$"', "new": 'pattern = r"^[\\\\w.+-]+@[\\\\w.-]+\\\\.[a-zA-Z]{2,}$"'},
    },
    # ── 027 return_format (2nd) ──
    {
        "task_id": "bugfix_027",
        "bug_type": "return_format",
        "difficulty": "easy",
        "module": "stats",
        "buggy_code": '''def summarize(values):
    if not values:
        return None
    return {
        "count": len(values),
        "sum": sum(values),
        "avg": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }
''',
        "fixed_code": '''def summarize(values):
    if not values:
        return {"count": 0, "sum": 0, "avg": 0, "min": None, "max": None}
    return {
        "count": len(values),
        "sum": sum(values),
        "avg": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }
''',
        "test_code": '''from stats import summarize


def test_summarize_normal():
    result = summarize([1, 2, 3, 4, 5])
    assert result["count"] == 5
    assert result["sum"] == 15
    assert result["avg"] == 3.0
    assert result["min"] == 1
    assert result["max"] == 5


def test_summarize_empty():
    result = summarize([])
    assert result["count"] == 0
    assert result["avg"] == 0
''',
        "issue": "`summarize([])` returns `None` instead of a dict with zeroed fields.\n\nThe API contract requires a dict with keys `count`, `sum`, `avg`, `min`, `max` even for empty input.\n\nRun: `python -m pytest tests/test_stats.py`",
        "scripted_fix": {"path": "stats.py", "old": "return None", "new": 'return {"count": 0, "sum": 0, "avg": 0, "min": None, "max": None}'},
    },
    # ── 028 argument_order (2nd) ──
    {
        "task_id": "bugfix_028",
        "bug_type": "argument_order",
        "difficulty": "easy",
        "module": "range_check",
        "buggy_code": '''def is_in_range(value, low, high):
    return low <= value <= high


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value
''',
        "fixed_code": '''def is_in_range(value, low, high):
    return low <= value <= high


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def clamp_and_check(value, low, high):
    clamped = clamp(value, low, high)
    return clamped, is_in_range(clamped, low, high)
''',
        "test_code": '''from range_check import is_in_range, clamp


def test_in_range():
    assert is_in_range(5, 1, 10) is True


def test_below_range():
    assert is_in_range(0, 1, 10) is False


def test_clamp_below():
    assert clamp(-5, 0, 100) == 0


def test_clamp_above():
    assert clamp(150, 0, 100) == 100


def test_clamp_in_range():
    assert clamp(50, 0, 100) == 50
''',
        "issue": "The functions work correctly individually but tests reveal an integration issue.\n\nRun: `python -m pytest tests/test_range_check.py`",
        "scripted_fix": {"path": "range_check.py", "old": "def clamp_and_check(value, low, high):\n    clamped = clamp(high, low, value)\n    return clamped, is_in_range(clamped, high, low)", "new": "def clamp_and_check(value, low, high):\n    clamped = clamp(value, low, high)\n    return clamped, is_in_range(clamped, low, high)"},
    },
    # ── 029 simple_algorithm (2nd) ──
    {
        "task_id": "bugfix_029",
        "bug_type": "simple_algorithm",
        "difficulty": "easy",
        "module": "fizzbuzz",
        "buggy_code": '''def fizzbuzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 3 == 0:
            result.append("Fizz")
        if i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result
''',
        "fixed_code": '''def fizzbuzz(n):
    result = []
    for i in range(1, n + 1):
        if i % 3 == 0 and i % 5 == 0:
            result.append("FizzBuzz")
        elif i % 3 == 0:
            result.append("Fizz")
        elif i % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(i))
    return result
''',
        "test_code": '''from fizzbuzz import fizzbuzz


def test_fizzbuzz_basic():
    result = fizzbuzz(15)
    assert result[0] == "1"
    assert result[1] == "2"
    assert result[2] == "Fizz"
    assert result[4] == "Buzz"
    assert result[14] == "FizzBuzz"
    assert len(result) == 15


def test_fizzbuzz_5():
    result = fizzbuzz(5)
    assert result == ["1", "2", "Fizz", "4", "Buzz"]
''',
        "issue": "`fizzbuzz` has two bugs: (1) it doesn't handle FizzBuzz (divisible by both 3 and 5), and (2) it appends both Fizz and Buzz instead of FizzBuzz.\n\n`fizzbuzz(15)[14]` should be `\"FizzBuzz\"`, not `\"Fizz\"`.\n\nRun: `python -m pytest tests/test_fizzbuzz.py`",
        "scripted_fix": {"path": "fizzbuzz.py", "old": "if i % 3 == 0:\n            result.append(\"Fizz\")\n        if i % 5 == 0:\n            result.append(\"Buzz\")\n        else:\n            result.append(str(i))", "new": "if i % 3 == 0 and i % 5 == 0:\n            result.append(\"FizzBuzz\")\n        elif i % 3 == 0:\n            result.append(\"Fizz\")\n        elif i % 5 == 0:\n            result.append(\"Buzz\")\n        else:\n            result.append(str(i))"},
    },
    # ── 030 date_comparison (2nd) ──
    {
        "task_id": "bugfix_030",
        "bug_type": "date_comparison",
        "difficulty": "easy",
        "module": "days_until",
        "buggy_code": '''from datetime import date


def days_until(target_str):
    target = date.fromisoformat(target_str)
    today = date.today()
    delta = target - today
    return delta.days
''',
        "fixed_code": '''from datetime import date


def days_until(target_str, today_str=None):
    target = date.fromisoformat(target_str)
    today = date.fromisoformat(today_str) if today_str else date.today()
    delta = target - today
    return delta.days
''',
        "test_code": '''from days_until import days_until


def test_future_date():
    assert days_until("2099-01-01") > 0


def test_past_date():
    assert days_until("2000-01-01") < 0


def test_specific_today():
    assert days_until("2025-06-01", today_str="2025-06-01") == 0


def test_one_day_later():
    assert days_until("2025-06-02", today_str="2025-06-01") == 1
''',
        "issue": "`days_until` cannot be tested deterministically because it uses `date.today()`.\n\nAdd an optional `today_str` parameter so tests can inject a fixed date.\n\nRun: `python -m pytest tests/test_days_until.py`",
        "scripted_fix": {"path": "days_until.py", "old": "def days_until(target_str):", "new": "def days_until(target_str, today_str=None):"},
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
