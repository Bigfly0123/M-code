"""Generate remaining new100 tasks (bugfix_270-350) programmatically."""
import json
from pathlib import Path

TASKS = []

def add(tid, bug_type, diff, module, buggy, fixed, tests, issue):
    TASKS.append({
        "task_id": tid, "bug_type": bug_type, "difficulty": diff, "module": module,
        "buggy_code": buggy, "fixed_code": fixed, "test_code": tests, "issue": issue,
        "target_file": f"{module}.py",
    })

# === regex (3 more) ===
add("bugfix_270", "regex", "easy", "url_check",
    'import re\n\ndef is_valid_url(url):\n    """Check if URL is valid."""\n    pattern = r"https?://.+ "\n    return bool(re.match(pattern, url))\n',
    'import re\n\ndef is_valid_url(url):\n    """Check if URL is valid."""\n    pattern = r"^https?://[^\\s]+\\.[^\\s]+$"\n    return bool(re.match(pattern, url))\n',
    'from url_check import is_valid_url\n\ndef test_valid():\n    assert is_valid_url("https://example.com") is True\n\ndef test_no_tld():\n    assert is_valid_url("https://example") is False\n\ndef test_spaces():\n    assert is_valid_url("https://example .com") is False\n',
    '`is_valid_url("https://example")` returns True but should return False (no TLD).\n\nRun: `python -m pytest tests/test_url_check.py`')

add("bugfix_271", "regex", "medium", "hex_color",
    'import re\n\ndef is_hex_color(s):\n    """Check if string is valid hex color code."""\n    pattern = r"#[0-9a-fA-F]"\n    return bool(re.match(pattern, s))\n',
    'import re\n\ndef is_hex_color(s):\n    """Check if string is valid hex color code."""\n    pattern = r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"\n    return bool(re.match(pattern, s))\n',
    'from hex_color import is_hex_color\n\ndef test_3digit():\n    assert is_hex_color("#abc") is True\n\ndef test_6digit():\n    assert is_hex_color("#aabbcc") is True\n\ndef test_invalid():\n    assert is_hex_color("#xyz") is False\n\ndef test_short():\n    assert is_hex_color("#ab") is False\n',
    '`is_hex_color("#abc")` returns False (should accept 3-digit codes).\n\nRun: `python -m pytest tests/test_hex_color.py`')

add("bugfix_272", "regex", "medium", "ip_check",
    'import re\n\ndef is_valid_ipv4(s):\n    """Check if string is valid IPv4 address."""\n    pattern = r"\\d+\\.\\d+\\.\\d+\\.\\d+"\n    return bool(re.match(pattern, s))\n',
    'import re\n\ndef is_valid_ipv4(s):\n    """Check if string is valid IPv4 address."""\n    pattern = r"^((25[0-5]|2[0-4]\\d|[01]?\\d\\d?)\\.){3}(25[0-5]|2[0-4]\\d|[01]?\\d\\d?)$"\n    return bool(re.match(pattern, s))\n',
    'from ip_check import is_valid_ipv4\n\ndef test_valid():\n    assert is_valid_ipv4("192.168.1.1") is True\n\ndef test_over_255():\n    assert is_valid_ipv4("256.1.1.1") is False\n\ndef test_letters():\n    assert is_valid_ipv4("abc.def.ghi.jkl") is False\n',
    '`is_valid_ipv4("256.1.1.1")` returns True (should reject values > 255).\n\nRun: `python -m pytest tests/test_ip_check.py`')

# === date_time (3 more) ===
add("bugfix_273", "date_time", "medium", "week_util",
    'from datetime import date\n\ndef is_weekend(d):\n    """Check if date falls on weekend."""\n    return d.weekday() >= 5\n\ndef next_weekday(d):\n    """Return next weekday from given date."""\n    from datetime import timedelta\n    return d + timedelta(days=1)\n',
    'from datetime import date, timedelta\n\ndef is_weekend(d):\n    """Check if date falls on weekend."""\n    return d.weekday() >= 5\n\ndef next_weekday(d):\n    """Return next weekday from given date."""\n    next_day = d + timedelta(days=1)\n    while next_day.weekday() >= 5:\n        next_day += timedelta(days=1)\n    return next_day\n',
    'from datetime import date\nfrom week_util import is_weekend, next_weekday\n\ndef test_friday():\n    assert is_weekend(date(2024, 1, 5)) is False\n\ndef test_saturday():\n    assert is_weekend(date(2024, 1, 6)) is True\n\ndef test_next_after_friday():\n    assert next_weekday(date(2024, 1, 5)).weekday() == 0\n\ndef test_next_after_saturday():\n    result = next_weekday(date(2024, 1, 6))\n    assert result.weekday() == 0\n',
    '`next_weekday(Saturday)` returns Sunday instead of Monday.\n\nShould skip weekends.\n\nRun: `python -m pytest tests/test_week_util.py`')

add("bugfix_274", "date_time", "easy", "time_fmt",
    'def format_duration(seconds):\n    """Format seconds into HH:MM:SS."""\n    h = seconds // 3600\n    m = (seconds % 3600) // 60\n    s = seconds % 60\n    return f"{h}:{m}:{s}"\n',
    'def format_duration(seconds):\n    """Format seconds into HH:MM:SS."""\n    h = seconds // 3600\n    m = (seconds % 3600) // 60\n    s = seconds % 60\n    return f"{h:02d}:{m:02d}:{s:02d}"\n',
    'from time_fmt import format_duration\n\ndef test_basic():\n    assert format_duration(3661) == "01:01:01"\n\ndef test_zero():\n    assert format_duration(0) == "00:00:00"\n\ndef test_padded():\n    assert format_duration(65) == "00:01:05"\n',
    '`format_duration(65)` returns "0:1:5" instead of "00:01:05".\n\nMissing zero-padding.\n\nRun: `python -m pytest tests/test_time_fmt.py`')

add("bugfix_275", "date_time", "medium", "meeting_sched",
    'def can_schedule(start1, end1, start2, end2):\n    """Check if two meetings can be scheduled without overlap.\n    Times are in minutes from midnight."""\n    return start1 > end2 or start2 > end1\n',
    'def can_schedule(start1, end1, start2, end2):\n    """Check if two meetings can be scheduled without overlap.\n    Times are in minutes from midnight."""\n    return end1 <= start2 or end2 <= start1\n',
    'from meeting_sched import can_schedule\n\ndef test_no_overlap():\n    assert can_schedule(60, 90, 100, 120) is True\n\ndef test_adjacent():\n    assert can_schedule(60, 90, 90, 120) is True\n\ndef test_overlap():\n    assert can_schedule(60, 100, 80, 120) is False\n\ndef test_contained():\n    assert can_schedule(60, 120, 70, 80) is False\n',
    '`can_schedule(60, 90, 90, 120)` returns False (adjacent meetings seen as overlapping).\n\nShould allow back-to-back scheduling.\n\nRun: `python -m pytest tests/test_meeting_sched.py`')

# === nested_condition (3 more) ===
add("bugfix_276", "nested_condition", "medium", "shipping_calc",
    'def calc_shipping(weight, is_express, is_international):\n    """Calculate shipping cost."""\n    if weight > 50:\n        return 25.0\n    if is_express:\n        return 15.0\n    return 5.0\n',
    'def calc_shipping(weight, is_express, is_international):\n    """Calculate shipping cost."""\n    base = 5.0\n    if weight > 50:\n        base = 25.0\n    elif weight > 20:\n        base = 10.0\n    if is_express:\n        base *= 2\n    if is_international:\n        base += 10.0\n    return base\n',
    'from shipping_calc import calc_shipping\n\ndef test_basic():\n    assert calc_shipping(5, False, False) == 5.0\n\ndef test_heavy():\n    assert calc_shipping(60, False, False) == 25.0\n\ndef test_express_intl():\n    assert calc_shipping(5, True, True) == 20.0\n\ndef test_medium():\n    assert calc_shipping(25, False, False) == 10.0\n',
    '`calc_shipping(5, True, True)` should be 20.0 (express doubles base + international adds 10).\n\nMissing weight tiers and modifier stacking.\n\nRun: `python -m pytest tests/test_shipping_calc.py`')

add("bugfix_277", "nested_condition", "medium", "tax_calc",
    'def calculate_tax(income):\n    """Calculate tax based on income brackets."""\n    if income <= 10000:\n        return 0\n    elif income <= 40000:\n        return income * 0.1\n    elif income <= 80000:\n        return income * 0.2\n    return income * 0.3\n',
    'def calculate_tax(income):\n    """Calculate tax based on income brackets."""\n    if income <= 10000:\n        return 0\n    tax = 0\n    remaining = income\n    brackets = [(40000, 0.1), (80000, 0.2), (float("inf"), 0.3)]\n    prev = 10000\n    for limit, rate in brackets:\n        if remaining <= prev:\n            break\n        taxable = min(remaining, limit) - prev\n        tax += taxable * rate\n        prev = limit\n    return tax\n',
    'from tax_calc import calculate_tax\n\ndef test_no_tax():\n    assert calculate_tax(5000) == 0\n\ndef test_low():\n    assert calculate_tax(20000) == 1000\n\ndef test_mid():\n    assert calculate_tax(50000) == 5000\n\ndef test_high():\n    result = calculate_tax(100000)\n    assert result == 3000 + 8000 + 6000\n',
    '`calculate_tax(50000)` returns 10000 instead of 5000.\n\nTax should be progressive (only income above each bracket taxed at higher rate).\n\nRun: `python -m pytest tests/test_tax_calc.py`')

add("bugfix_278", "nested_condition", "hard", "perm_check",
    'def has_permission(user, action, resource):\n    """Check RBAC permission."""\n    roles = {\n        "admin": ["read", "write", "delete"],\n        "editor": ["read", "write"],\n        "viewer": ["read"],\n    }\n    user_roles = user.get("roles", [])\n    for role in user_roles:\n        if action in roles.get(role, []):\n            return True\n    return False\n',
    'def has_permission(user, action, resource):\n    """Check RBAC permission with resource ownership."""\n    roles = {\n        "admin": ["read", "write", "delete"],\n        "editor": ["read", "write"],\n        "viewer": ["read"],\n    }\n    user_roles = user.get("roles", [])\n    user_id = user.get("id")\n    for role in user_roles:\n        if role == "admin":\n            return True\n        if role == "editor" and action in ("read", "write"):\n            if resource.get("owner") == user_id or action == "read":\n                return True\n        if role == "viewer" and action == "read":\n            return True\n    return False\n',
    'from perm_check import has_permission\n\ndef test_admin():\n    u = {"id": 1, "roles": ["admin"]}\n    assert has_permission(u, "delete", {"owner": 2}) is True\n\ndef test_editor_own():\n    u = {"id": 1, "roles": ["editor"]}\n    assert has_permission(u, "write", {"owner": 1}) is True\n\ndef test_editor_other():\n    u = {"id": 1, "roles": ["editor"]}\n    assert has_permission(u, "write", {"owner": 2}) is False\n\ndef test_viewer_write():\n    u = {"id": 1, "roles": ["viewer"]}\n    assert has_permission(u, "write", {"owner": 1}) is False\n',
    'Editors can write to any resource regardless of ownership.\n`has_permission(editor, "write", {owner: other})` should be False.\n\nRun: `python -m pytest tests/test_perm_check.py`')

# === type_conversion (3 more) ===
add("bugfix_279", "type_conversion", "easy", "sum_util",
    'def safe_sum(values):\n    """Sum numeric values, skip non-numeric."""\n    return sum(values)\n',
    'def safe_sum(values):\n    """Sum numeric values, skip non-numeric."""\n    total = 0\n    for v in values:\n        try:\n            total += float(v)\n        except (TypeError, ValueError):\n            continue\n    return total\n',
    'from sum_util import safe_sum\n\ndef test_numbers():\n    assert safe_sum([1, 2, 3]) == 6\n\ndef test_strings():\n    assert safe_sum(["1", "2", "3"]) == 6\n\ndef test_mixed():\n    assert safe_sum([1, "two", 3]) == 4\n\ndef test_empty():\n    assert safe_sum([]) == 0\n',
    '`safe_sum([1, "two", 3])` raises TypeError.\n\nShould skip non-numeric values.\n\nRun: `python -m pytest tests/test_sum_util.py`')

add("bugfix_280", "type_conversion", "medium", "config_util",
    'def get_int_config(config, key, default=0):\n    """Get integer config value."""\n    return config.get(key, default)\n',
    'def get_int_config(config, key, default=0):\n    """Get integer config value."""\n    val = config.get(key, default)\n    try:\n        return int(val)\n    except (TypeError, ValueError):\n        return default\n',
    'from config_util import get_int_config\n\ndef test_int():\n    assert get_int_config({"port": 8080}, "port") == 8080\n\ndef test_string():\n    assert get_int_config({"port": "8080"}, "port") == 8080\n\ndef test_missing():\n    assert get_int_config({}, "port", 3000) == 3000\n\ndef test_invalid():\n    assert get_int_config({"port": "abc"}, "port", 3000) == 3000\n',
    '`get_int_config({"port": "8080"}, "port")` returns "8080" (string) instead of 8080 (int).\n\nRun: `python -m pytest tests/test_config_util.py`')

add("bugfix_281", "type_conversion", "medium", "math_eval",
    'def eval_expression(expr):\n    """Evaluate simple math expression string."""\n    return eval(expr)\n',
    'def eval_expression(expr):\n    """Evaluate simple math expression string safely."""\n    import ast, operator\n    ops = {ast.Add: operator.add, ast.Sub: operator.sub,\n           ast.Mult: operator.mul, ast.Div: operator.truediv}\n    def _eval(node):\n        if isinstance(node, ast.Num):\n            return node.n\n        if isinstance(node, ast.BinOp):\n            return ops[type(node.op)](_eval(node.left), _eval(node.right))\n        raise ValueError(f"Unsupported: {ast.dump(node)}")\n    return _eval(ast.parse(expr, mode="eval").body)\n',
    'import pytest\nfrom math_eval import eval_expression\n\ndef test_add():\n    assert eval_expression("1+2") == 3\n\ndef test_complex():\n    assert eval_expression("2*3+4") == 10\n\ndef test_dangerous():\n    with pytest.raises((ValueError, TypeError)):\n        eval_expression("__import__(\'os\').system(\'ls\')")\n',
    '`eval_expression("__import__(\'os\').system(\'ls\')")` executes arbitrary code.\n\nUses `eval()` instead of safe expression parser.\n\nRun: `python -m pytest tests/test_math_eval.py`')

# === list_mutation (3 more) ===
add("bugfix_282", "list_mutation", "medium", "set_ops",
    'def union(a, b):\n    """Return union of two lists."""\n    return a + b\n\ndef intersection(a, b):\n    """Return intersection of two lists."""\n    return [x for x in a if x in b]\n\ndef difference(a, b):\n    """Return elements in a but not in b."""\n    return [x for x in a if x not in b]\n',
    'def union(a, b):\n    """Return union of two lists (unique)."""\n    return list(set(a) | set(b))\n\ndef intersection(a, b):\n    """Return intersection of two lists."""\n    return list(set(a) & set(b))\n\ndef difference(a, b):\n    """Return elements in a but not in b."""\n    return list(set(a) - set(b))\n',
    'from set_ops import union, intersection, difference\n\ndef test_union():\n    result = union([1,2,3], [3,4,5])\n    assert sorted(result) == [1,2,3,4,5]\n\ndef test_intersection():\n    result = intersection([1,2,3], [2,3,4])\n    assert sorted(result) == [2,3]\n\ndef test_difference():\n    result = difference([1,2,3], [2,3,4])\n    assert result == [1]\n\ndef test_union_no_dup():\n    result = union([1,1,2], [2,2,3])\n    assert sorted(result) == [1,2,3]\n',
    '`union([1,1,2], [2,2,3])` returns duplicates [1,1,2,2,2,3] instead of [1,2,3].\n\nRun: `python -m pytest tests/test_set_ops.py`')

add("bugfix_283", "list_mutation", "medium", "stack_util",
    'class Stack:\n    def __init__(self):\n        self._items = []\n    def push(self, item):\n        self._items.append(item)\n    def pop(self):\n        return self._items.pop()\n    def is_empty(self):\n        return len(self._items) == 0\n    def peek(self):\n        return self._items[-1]\n    def size(self):\n        return len(self._items)\n',
    'class Stack:\n    def __init__(self):\n        self._items = []\n    def push(self, item):\n        self._items.append(item)\n    def pop(self):\n        if self.is_empty():\n            raise IndexError("Pop from empty stack")\n        return self._items.pop()\n    def is_empty(self):\n        return len(self._items) == 0\n    def peek(self):\n        if self.is_empty():\n            raise IndexError("Peek at empty stack")\n        return self._items[-1]\n    def size(self):\n        return len(self._items)\n',
    'import pytest\nfrom stack_util import Stack\n\ndef test_push_pop():\n    s = Stack()\n    s.push(1)\n    s.push(2)\n    assert s.pop() == 2\n    assert s.pop() == 1\n\ndef test_empty():\n    s = Stack()\n    assert s.is_empty() is True\n\ndef test_pop_empty():\n    s = Stack()\n    with pytest.raises(IndexError):\n        s.pop()\n\ndef test_peek():\n    s = Stack()\n    s.push("a")\n    assert s.peek() == "a"\n    assert s.size() == 1\n',
    '`Stack().pop()` raises unhelpful error instead of IndexError.\n\nNo bounds checking on pop/peek.\n\nRun: `python -m pytest tests/test_stack_util.py`')

add("bugfix_284", "list_mutation", "easy", "dedup_util",
    'def deduplicate(lst):\n    """Remove duplicates preserving order."""\n    return list(set(lst))\n',
    'def deduplicate(lst):\n    """Remove duplicates preserving order."""\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result\n',
    'from dedup_util import deduplicate\n\ndef test_basic():\n    assert deduplicate([1,2,2,3,3,3]) == [1,2,3]\n\ndef test_order():\n    result = deduplicate([3,1,2,1,3])\n    assert result == [3,1,2]\n\ndef test_strings():\n    assert deduplicate(["a","b","a"]) == ["a","b"]\n',
    '`deduplicate([3,1,2,1,3])` does not preserve order (uses set).\n\nRun: `python -m pytest tests/test_dedup_util.py`')

# === off_by_one (3 more) ===
add("bugfix_285", "off_by_one", "easy", "range_util",
    'def clamp(value, min_val, max_val):\n    """Clamp value to range [min_val, max_val]."""\n    if value < min_val:\n        return min_val\n    if value > max_val:\n        return max_val\n    return value\n\ndef in_range(value, min_val, max_val):\n    """Check if value is in range [min_val, max_val]."""\n    return min_val < value < max_val\n',
    'def clamp(value, min_val, max_val):\n    """Clamp value to range [min_val, max_val]."""\n    if value < min_val:\n        return min_val\n    if value > max_val:\n        return max_val\n    return value\n\ndef in_range(value, min_val, max_val):\n    """Check if value is in range [min_val, max_val]."""\n    return min_val <= value <= max_val\n',
    'from range_util import clamp, in_range\n\ndef test_clamp():\n    assert clamp(5, 0, 10) == 5\n    assert clamp(-5, 0, 10) == 0\n    assert clamp(15, 0, 10) == 10\n\ndef test_in_range():\n    assert in_range(5, 0, 10) is True\n    assert in_range(0, 0, 10) is True\n    assert in_range(10, 0, 10) is True\n    assert in_range(-1, 0, 10) is False\n',
    '`in_range(0, 0, 10)` returns False (should be True for inclusive range).\n\nRun: `python -m pytest tests/test_range_util.py`')

add("bugfix_286", "off_by_one", "medium", "sublist_find",
    'def find_sublist(lst, sub):\n    """Find starting index of sub in lst, -1 if not found."""\n    for i in range(len(lst) - len(sub)):\n        if lst[i:i+len(sub)] == sub:\n            return i\n    return -1\n',
    'def find_sublist(lst, sub):\n    """Find starting index of sub in lst, -1 if not found."""\n    for i in range(len(lst) - len(sub) + 1):\n        if lst[i:i+len(sub)] == sub:\n            return i\n    return -1\n',
    'from sublist_find import find_sublist\n\ndef test_found():\n    assert find_sublist([1,2,3,4], [2,3]) == 1\n\ndef test_at_end():\n    assert find_sublist([1,2,3,4], [3,4]) == 2\n\ndef test_not_found():\n    assert find_sublist([1,2,3], [4,5]) == -1\n\ndef test_full():\n    assert find_sublist([1,2], [1,2]) == 0\n',
    '`find_sublist([1,2,3,4], [3,4])` returns -1 instead of 2.\n\nOff-by-one in range misses last possible position.\n\nRun: `python -m pytest tests/test_sublist_find.py`')

add("bugfix_287", "off_by_one", "medium", "buffer_util",
    'class RingBuffer:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.buffer = [None] * capacity\n        self.head = 0\n        self.count = 0\n\n    def push(self, item):\n        self.buffer[self.head] = item\n        self.head = (self.head + 1) % self.capacity\n        if self.count < self.capacity:\n            self.count += 1\n\n    def get(self):\n        if self.count == 0:\n            return []\n        start = (self.head - self.count) % self.capacity\n        return [self.buffer[(start + i) % self.capacity] for i in range(self.count)]\n',
    'class RingBuffer:\n    def __init__(self, capacity):\n        if capacity <= 0:\n            raise ValueError("Capacity must be positive")\n        self.capacity = capacity\n        self.buffer = [None] * capacity\n        self.head = 0\n        self.count = 0\n\n    def push(self, item):\n        self.buffer[self.head] = item\n        self.head = (self.head + 1) % self.capacity\n        if self.count < self.capacity:\n            self.count += 1\n\n    def get(self):\n        if self.count == 0:\n            return []\n        start = (self.head - self.count) % self.capacity\n        return [self.buffer[(start + i) % self.capacity] for i in range(self.count)]\n',
    'import pytest\nfrom buffer_util import RingBuffer\n\ndef test_basic():\n    b = RingBuffer(3)\n    b.push(1)\n    b.push(2)\n    assert b.get() == [1, 2]\n\ndef test_overflow():\n    b = RingBuffer(3)\n    for i in range(5):\n        b.push(i)\n    assert b.get() == [2, 3, 4]\n\ndef test_zero_capacity():\n    with pytest.raises(ValueError):\n        RingBuffer(0)\n',
    '`RingBuffer(0)` creates buffer of size 0, causing division by zero.\n\nNo capacity validation.\n\nRun: `python -m pytest tests/test_buffer_util.py`')

# === exception_handling (3 more) ===
add("bugfix_288", "exception_handling", "medium", "file_util",
    'def read_first_line(path):\n    """Read first line of file."""\n    f = open(path)\n    line = f.readline()\n    f.close()\n    return line.strip()\n',
    'def read_first_line(path):\n    """Read first line of file."""\n    try:\n        with open(path) as f:\n            return f.readline().strip()\n    except FileNotFoundError:\n        return None\n',
    'import tempfile, os\nfrom file_util import read_first_line\n\ndef test_exists():\n    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:\n        f.write("hello\\nworld")\n        f.flush()\n        assert read_first_line(f.name) == "hello"\n        os.unlink(f.name)\n\ndef test_missing():\n    assert read_first_line("/nonexistent.txt") is None\n',
    '`read_first_line("/nonexistent.txt")` raises FileNotFoundError.\n\nNo error handling for missing files.\n\nRun: `python -m pytest tests/test_file_util.py`')

add("bugfix_289", "exception_handling", "medium", "convert_util",
    'def to_int(value):\n    """Convert value to integer."""\n    return int(value)\n\ndef to_float(value):\n    """Convert value to float."""\n    return float(value)\n',
    'def to_int(value, default=None):\n    """Convert value to integer, return default on failure."""\n    try:\n        return int(value)\n    except (TypeError, ValueError):\n        return default\n\ndef to_float(value, default=None):\n    """Convert value to float, return default on failure."""\n    try:\n        return float(value)\n    except (TypeError, ValueError):\n        return default\n',
    'from convert_util import to_int, to_float\n\ndef test_int():\n    assert to_int("42") == 42\n\ndef test_int_invalid():\n    assert to_int("abc") is None\n\ndef test_float():\n    assert to_float("3.14") == 3.14\n\ndef test_none():\n    assert to_int(None) is None\n',
    '`to_int("abc")` raises ValueError instead of returning default.\n\nRun: `python -m pytest tests/test_convert_util.py`')

add("bugfix_290", "exception_handling", "medium", "dict_util",
    'def deep_get(d, *keys):\n    """Get nested dict value by chain of keys."""\n    result = d\n    for key in keys:\n        result = result[key]\n    return result\n',
    'def deep_get(d, *keys, default=None):\n    """Get nested dict value by chain of keys."""\n    result = d\n    for key in keys:\n        try:\n            result = result[key]\n        except (KeyError, TypeError, IndexError):\n            return default\n    return result\n',
    'from dict_util import deep_get\n\ndef test_basic():\n    assert deep_get({"a": {"b": 1}}, "a", "b") == 1\n\ndef test_missing():\n    assert deep_get({"a": 1}, "b") is None\n\ndef test_nested_missing():\n    assert deep_get({"a": {"b": 1}}, "a", "c") is None\n\ndef test_default():\n    assert deep_get({}, "x", default="N/A") == "N/A"\n',
    '`deep_get({"a": 1}, "b")` raises KeyError instead of returning None.\n\nRun: `python -m pytest tests/test_dict_util.py`')

# === boundary_empty (3 more) ===
add("bugfix_291", "boundary_empty", "easy", "max_util",
    'def find_max(lst):\n    """Find maximum value in list."""\n    return max(lst)\n',
    'def find_max(lst, default=None):\n    """Find maximum value in list."""\n    if not lst:\n        return default\n    return max(lst)\n',
    'from max_util import find_max\n\ndef test_basic():\n    assert find_max([3, 1, 4, 1, 5]) == 5\n\ndef test_empty():\n    assert find_max([]) is None\n\ndef test_single():\n    assert find_max([42]) == 42\n',
    '`find_max([])` raises ValueError instead of returning None.\n\nRun: `python -m pytest tests/test_max_util.py`')

add("bugfix_292", "boundary_empty", "medium", "filter_util",
    'def filter_by_key(items, key, value):\n    """Filter list of dicts where key equals value."""\n    return [item for item in items if item[key] == value]\n',
    'def filter_by_key(items, key, value):\n    """Filter list of dicts where key equals value."""\n    return [item for item in items if item.get(key) == value]\n',
    'from filter_util import filter_by_key\n\ndef test_basic():\n    data = [{"name": "a", "id": 1}, {"name": "b", "id": 2}]\n    assert filter_by_key(data, "name", "a") == [{"name": "a", "id": 1}]\n\ndef test_missing_key():\n    data = [{"name": "a"}, {"id": 2}]\n    result = filter_by_key(data, "id", 2)\n    assert len(result) == 1\n\ndef test_empty():\n    assert filter_by_key([], "x", 1) == []\n',
    '`filter_by_key([{"name": "a"}], "id", 1)` raises KeyError.\n\nUses `item[key]` instead of `item.get(key)`.\n\nRun: `python -m pytest tests/test_filter_util.py`')

add("bugfix_293", "boundary_empty", "medium", "str_util",
    'def truncate(text, max_len):\n    """Truncate text to max_len, add ... if truncated."""\n    return text[:max_len] + "..."\n',
    'def truncate(text, max_len):\n    """Truncate text to max_len, add ... if truncated."""\n    if not text:\n        return ""\n    if len(text) <= max_len:\n        return text\n    return text[:max_len - 3] + "..."\n',
    'from str_util import truncate\n\ndef test_short():\n    assert truncate("hello", 10) == "hello"\n\ndef test_long():\n    assert truncate("hello world", 8) == "hello..."\n\ndef test_empty():\n    assert truncate("", 10) == ""\n\ndef test_exact():\n    assert truncate("hello", 5) == "hello"\n',
    '`truncate("hello", 10)` returns "hello..." instead of "hello".\n\nAlways appends "..." even when not truncated.\n\nRun: `python -m pytest tests/test_str_util.py`')

# === multi_file (3 more) ===
add("bugfix_294", "multi_file", "hard", "auth_system",
    'def validate_password(password):\n    """Check password strength."""\n    if len(password) < 8:\n        return False\n    return True\n',
    'def validate_password(password):\n    """Check password strength."""\n    if len(password) < 8:\n        return False\n    has_upper = any(c.isupper() for c in password)\n    has_lower = any(c.islower() for c in password)\n    has_digit = any(c.isdigit() for c in password)\n    return has_upper and has_lower and has_digit\n',
    'from auth_system import validate_password\n\ndef test_strong():\n    assert validate_password("MyPass123") is True\n\ndef test_short():\n    assert validate_password("Ab1") is False\n\ndef test_no_upper():\n    assert validate_password("mypass123") is False\n\ndef test_no_digit():\n    assert validate_password("MyPassword") is False\n',
    '`validate_password("mypass123")` returns True (only checks length).\n\nMissing uppercase, lowercase, digit requirements.\n\nRun: `python -m pytest tests/test_auth_system.py`')

add("bugfix_295", "multi_file", "hard", "cache_util",
    'class LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.cache = {}\n        self.order = []\n\n    def get(self, key):\n        if key in self.cache:\n            self.order.remove(key)\n            self.order.append(key)\n            return self.cache[key]\n        return -1\n\n    def put(self, key, value):\n        if key in self.cache:\n            self.order.remove(key)\n        elif len(self.cache) >= self.capacity:\n            oldest = self.order.pop(0)\n            del self.cache[oldest]\n        self.cache[key] = value\n        self.order.append(key)\n',
    'from collections import OrderedDict\n\nclass LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.cache = OrderedDict()\n\n    def get(self, key):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n            return self.cache[key]\n        return -1\n\n    def put(self, key, value):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        elif len(self.cache) >= self.capacity:\n            self.cache.popitem(last=False)\n        self.cache[key] = value\n',
    'from cache_util import LRUCache\n\ndef test_basic():\n    c = LRUCache(2)\n    c.put(1, "a")\n    c.put(2, "b")\n    assert c.get(1) == "a"\n\ndef test_eviction():\n    c = LRUCache(2)\n    c.put(1, "a")\n    c.put(2, "b")\n    c.put(3, "c")\n    assert c.get(1) == -1\n    assert c.get(3) == "c"\n\ndef test_update():\n    c = LRUCache(2)\n    c.put(1, "a")\n    c.put(1, "b")\n    assert c.get(1) == "b"\n',
    'LRU eviction is O(n) due to list operations.\nWith large capacity, `order.remove(key)` becomes slow.\nShould use OrderedDict.\n\nRun: `python -m pytest tests/test_cache_util.py`')

# === string_norm (3 more) ===
add("bugfix_296", "string_norm", "easy", "title_case",
    'def to_title_case(s):\n    """Convert string to title case."""\n    return s.title()\n',
    'def to_title_case(s):\n    """Convert string to title case, handling special cases."""\n    small_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with"}\n    words = s.lower().split()\n    if not words:\n        return ""\n    result = [words[0].capitalize()]\n    for w in words[1:]:\n        result.append(w if w in small_words else w.capitalize())\n    return " ".join(result)\n',
    'from title_case import to_title_case\n\ndef test_basic():\n    assert to_title_case("hello world") == "Hello World"\n\ndef test_articles():\n    assert to_title_case("the lord of the rings") == "The Lord of the Rings"\n\ndef test_empty():\n    assert to_title_case("") == ""\n',
    '`to_title_case("the lord of the rings")` returns "The Lord Of The Rings".\n\nSmall words like "of", "the" should not be capitalized (except first word).\n\nRun: `python -m pytest tests/test_title_case.py`')

add("bugfix_297", "string_norm", "medium", "csv_parser",
    'def parse_csv_line(line):\n    """Parse CSV line into fields."""\n    return line.split(",")\n',
    'def parse_csv_line(line):\n    """Parse CSV line into fields, handling quoted fields."""\n    import csv\n    import io\n    reader = csv.reader(io.StringIO(line))\n    return next(reader)\n',
    'from csv_parser import parse_csv_line\n\ndef test_simple():\n    assert parse_csv_line("a,b,c") == ["a", "b", "c"]\n\ndef test_quoted():\n    assert parse_csv_line(\'"hello, world",b\') == ["hello, world", "b"]\n\ndef test_empty():\n    assert parse_csv_line("") == [""]\n',
    '`parse_csv_line(\'"hello, world",b\')` returns `["\\"hello", " world\\"","b"]` instead of `["hello, world", "b"]`.\n\nDoes not handle quoted fields with commas.\n\nRun: `python -m pytest tests/test_csv_parser.py`')

add("bugfix_298", "string_norm", "easy", "trim_util",
    'def clean_whitespace(s):\n    """Normalize whitespace."""\n    return s.strip()\n',
    'def clean_whitespace(s):\n    """Normalize whitespace: strip and collapse internal spaces."""\n    import re\n    return re.sub(r"\\s+", " ", s.strip())\n',
    'from trim_util import clean_whitespace\n\ndef test_basic():\n    assert clean_whitespace("  hello  ") == "hello"\n\ndef test_internal():\n    assert clean_whitespace("hello   world") == "hello world"\n\ndef test_tabs():\n    assert clean_whitespace("\\thello\\tworld\\t") == "hello world"\n',
    '`clean_whitespace("hello   world")` returns "hello   world" (only strips edges).\n\nDoes not collapse internal whitespace.\n\nRun: `python -m pytest tests/test_trim_util.py`')

# === default_arg (3 more) ===
add("bugfix_299", "default_arg", "medium", "logger_util",
    'def create_logger(name, handlers=[]):\n    """Create logger with handlers."""\n    return {"name": name, "handlers": handlers}\n',
    'def create_logger(name, handlers=None):\n    """Create logger with handlers."""\n    if handlers is None:\n        handlers = []\n    return {"name": name, "handlers": handlers}\n',
    'from logger_util import create_logger\n\ndef test_basic():\n    l = create_logger("app")\n    assert l == {"name": "app", "handlers": []}\n\ndef test_independent():\n    l1 = create_logger("app1")\n    l2 = create_logger("app2", ["file"])\n    assert l1["handlers"] == []\n    assert l2["handlers"] == ["file"]\n',
    'Two loggers share the same handlers list.\n`create_logger("app1")` and `create_logger("app2")` share mutable default.\n\nRun: `python -m pytest tests/test_logger_util.py`')

add("bugfix_300", "default_arg", "medium", "api_client",
    'def make_request(url, headers={}):\n    """Make HTTP request."""\n    headers["User-Agent"] = "MyApp/1.0"\n    return {"url": url, "headers": headers}\n',
    'def make_request(url, headers=None):\n    """Make HTTP request."""\n    if headers is None:\n        headers = {}\n    headers = headers.copy()\n    headers["User-Agent"] = "MyApp/1.0"\n    return {"url": url, "headers": headers}\n',
    'from api_client import make_request\n\ndef test_default():\n    r = make_request("http://example.com")\n    assert r["headers"] == {"User-Agent": "MyApp/1.0"}\n\ndef test_custom():\n    r = make_request("http://example.com", {"Auth": "token"})\n    assert r["headers"]["Auth"] == "token"\n    assert r["headers"]["User-Agent"] == "MyApp/1.0"\n\ndef test_no_mutate():\n    h = {"Auth": "token"}\n    make_request("http://example.com", h)\n    assert "User-Agent" not in h\n',
    'Passing custom headers gets mutated: `make_request(url, {"Auth": "token"})` adds User-Agent to caller\'s dict.\n\nRun: `python -m pytest tests/test_api_client.py`')


def build_task_dir(root, task):
    task_dir = root / task["task_id"]
    task_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = task_dir / "repo"
    repo_dir.mkdir(exist_ok=True)
    (repo_dir / task["target_file"]).write_text(task["buggy_code"], encoding="utf-8")
    tests_dir = repo_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    test_filename = f"test_{task['module']}.py"
    (tests_dir / test_filename).write_text(task["test_code"], encoding="utf-8")
    (task_dir / "issue.md").write_text(task["issue"], encoding="utf-8")
    meta = {
        "task_id": task["task_id"], "bug_type": task["bug_type"], "language": "python",
        "test_command": f"python -m pytest tests/{test_filename}",
        "target_files": [task["target_file"]], "difficulty": task["difficulty"],
        "timeout": 30,
        "scripted_fix": {"path": task["target_file"], "old": task["buggy_code"].strip(), "new": task["fixed_code"].strip()},
    }
    (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"
    print(f"Building {len(TASKS)} extra tasks (bugfix_270-300)...")
    for task in TASKS:
        build_task_dir(tasks_root, task)
        print(f"  {task['task_id']}: {task['bug_type']} ({task['difficulty']})")

    # Update split file
    all_new = sorted([p.name for p in tasks_root.iterdir()
                     if p.is_dir() and p.name.startswith("bugfix_")
                     and int(p.name.split("_")[1]) >= 251])
    splits_dir = root / "outputs" / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    (splits_dir / "new100_heldout_tasks.txt").write_text("\n".join(all_new) + "\n", encoding="utf-8")
    print(f"\nTotal new tasks: {len(all_new)}")


if __name__ == "__main__":
    main()
