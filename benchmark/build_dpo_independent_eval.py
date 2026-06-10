"""Build DPO-independent eval tasks (bugfix_351-400).

Focus: patch stability, wrong patch, test feedback, indentation-sensitive,
regex, date/time, type conversion, stateful logic, nested condition.
"""
import json
from pathlib import Path

TASKS = [
    # === patch_stability: edit_file precision ===
    {"task_id": "bugfix_351", "bug_type": "patch_stability", "difficulty": "medium", "module": "temp_conv",
     "buggy_code": 'def celsius_to_fahrenheit(c):\n    """Convert Celsius to Fahrenheit."""\n    return c * 9/5 + 32\n\ndef fahrenheit_to_celsius(f):\n    """Convert Fahrenheit to Celsius."""\n    return (f - 32) * 5/9\n',
     "fixed_code": 'def celsius_to_fahrenheit(c):\n    """Convert Celsius to Fahrenheit."""\n    return c * 9/5 + 32\n\ndef fahrenheit_to_celsius(f):\n    """Convert Fahrenheit to Celsius."""\n    return round((f - 32) * 5/9, 2)\n',
     "test_code": 'from temp_conv import celsius_to_fahrenheit, fahrenheit_to_celsius\n\ndef test_c_to_f():\n    assert celsius_to_fahrenheit(0) == 32\n    assert celsius_to_fahrenheit(100) == 212\n\ndef test_f_to_c():\n    assert fahrenheit_to_celsius(32) == 0\n    assert fahrenheit_to_celsius(212) == 100\n\ndef test_precision():\n    assert fahrenheit_to_celsius(98.6) == 37.0\n',
     "issue": '`fahrenheit_to_celsius(98.6)` returns 36.99999... instead of 37.0.\n\nNeeds rounding.\n\nRun: `python -m pytest tests/test_temp_conv.py`'},

    {"task_id": "bugfix_352", "bug_type": "patch_stability", "difficulty": "medium", "module": "str_clean",
     "buggy_code": 'def clean_string(s):\n    """Remove extra spaces and strip."""\n    return " ".join(s.split())\n\ndef normalize_newlines(s):\n    """Normalize line endings to \\n."""\n    return s.replace("\\r\\n", "\\n").replace("\\r", "\\n")\n',
     "fixed_code": 'def clean_string(s):\n    """Remove extra spaces and strip."""\n    if not s:\n        return ""\n    return " ".join(s.split())\n\ndef normalize_newlines(s):\n    """Normalize line endings to \\n."""\n    if not s:\n        return ""\n    return s.replace("\\r\\n", "\\n").replace("\\r", "\\n")\n',
     "test_code": 'from str_clean import clean_string, normalize_newlines\n\ndef test_clean():\n    assert clean_string("  hello   world  ") == "hello world"\n\ndef test_clean_empty():\n    assert clean_string("") == ""\n    assert clean_string(None) == ""\n\ndef test_newlines():\n    assert normalize_newlines("a\\r\\nb") == "a\\nb"\n\ndef test_newlines_empty():\n    assert normalize_newlines("") == ""\n',
     "issue": '`clean_string("")` and `clean_string(None)` raise TypeError.\n\nRun: `python -m pytest tests/test_str_clean.py`'},

    {"task_id": "bugfix_353", "bug_type": "patch_stability", "difficulty": "easy", "module": "clamp_util",
     "buggy_code": 'def clamp(value, low, high):\n    """Clamp value to [low, high]."""\n    return max(low, min(value, high))\n\ndef clamp_list(values, low, high):\n    """Clamp each value in list."""\n    return [clamp(v, low, high) for v in values]\n',
     "fixed_code": 'def clamp(value, low, high):\n    """Clamp value to [low, high]."""\n    if low > high:\n        low, high = high, low\n    return max(low, min(value, high))\n\ndef clamp_list(values, low, high):\n    """Clamp each value in list."""\n    return [clamp(v, low, high) for v in values]\n',
     "test_code": 'from clamp_util import clamp, clamp_list\n\ndef test_basic():\n    assert clamp(5, 0, 10) == 5\n    assert clamp(-5, 0, 10) == 0\n    assert clamp(15, 0, 10) == 10\n\ndef test_reversed():\n    assert clamp(5, 10, 0) == 5\n\ndef test_list():\n    assert clamp_list([0, 5, 10, 15], 2, 8) == [2, 5, 8, 8]\n',
     "issue": '`clamp(5, 10, 0)` returns 10 instead of 5.\n\nShould handle reversed bounds.\n\nRun: `python -m pytest tests/test_clamp_util.py`'},

    # === wrong_patch: edit correctness ===
    {"task_id": "bugfix_354", "bug_type": "wrong_patch", "difficulty": "medium", "module": "roman_conv",
     "buggy_code": 'def to_roman(num):\n    """Convert number to Roman numeral."""\n    vals = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]\n    result = ""\n    for v, s in vals:\n        while num >= v:\n            result += s\n            num -= v\n    return result\n\ndef from_roman(s):\n    """Convert Roman numeral to number."""\n    return 0\n',
     "fixed_code": 'def to_roman(num):\n    """Convert number to Roman numeral."""\n    if not 1 <= num <= 3999:\n        return ""\n    vals = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),(40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]\n    result = ""\n    for v, s in vals:\n        while num >= v:\n            result += s\n            num -= v\n    return result\n\ndef from_roman(s):\n    """Convert Roman numeral to number."""\n    vals = {"M":1000,"D":500,"C":100,"L":50,"X":10,"V":5,"I":1}\n    result = 0\n    for i in range(len(s)):\n        if i + 1 < len(s) and vals[s[i]] < vals[s[i+1]]:\n            result -= vals[s[i]]\n        else:\n            result += vals[s[i]]\n    return result\n',
     "test_code": 'from roman_conv import to_roman, from_roman\n\ndef test_to():\n    assert to_roman(3) == "III"\n    assert to_roman(4) == "IV"\n    assert to_roman(1994) == "MCMXCIV"\n\ndef test_from():\n    assert from_roman("III") == 3\n    assert from_roman("IV") == 4\n    assert from_roman("MCMXCIV") == 1994\n\ndef test_invalid():\n    assert to_roman(0) == ""\n    assert to_roman(4000) == ""\n',
     "issue": '`from_roman("IV")` returns 0 (not implemented).\n`to_roman(0)` returns "I" instead of "".\n\nRun: `python -m pytest tests/test_roman_conv.py`'},

    {"task_id": "bugfix_355", "bug_type": "wrong_patch", "difficulty": "medium", "module": "word_freq",
     "buggy_code": 'def word_frequency(text):\n    """Count word frequency, case-insensitive."""\n    words = text.split()\n    freq = {}\n    for w in words:\n        freq[w] = freq.get(w, 0) + 1\n    return freq\n\ndef top_words(text, n=3):\n    """Return top n most frequent words."""\n    freq = word_frequency(text)\n    return sorted(freq.items(), key=lambda x: x[1])[:n]\n',
     "fixed_code": 'import re\n\ndef word_frequency(text):\n    """Count word frequency, case-insensitive."""\n    if not text:\n        return {}\n    words = re.findall(r"[a-zA-Z]+", text.lower())\n    freq = {}\n    for w in words:\n        freq[w] = freq.get(w, 0) + 1\n    return freq\n\ndef top_words(text, n=3):\n    """Return top n most frequent words."""\n    freq = word_frequency(text)\n    return sorted(freq.items(), key=lambda x: -x[1])[:n]\n',
     "test_code": 'from word_freq import word_frequency, top_words\n\ndef test_basic():\n    freq = word_frequency("hello world hello")\n    assert freq["hello"] == 2\n    assert freq["world"] == 1\n\ndef test_case():\n    freq = word_frequency("Hello hello HELLO")\n    assert freq["hello"] == 3\n\ndef test_top():\n    result = top_words("a b a c a b", 2)\n    assert result[0][0] == "a"\n\ndef test_empty():\n    assert word_frequency("") == {}\n',
     "issue": '`word_frequency("Hello hello HELLO")` returns 3 different keys.\nCase-insensitive counting not working.\n`top_words` returns least frequent instead of most.\n\nRun: `python -m pytest tests/test_word_freq.py`'},

    {"task_id": "bugfix_356", "bug_type": "wrong_patch", "difficulty": "medium", "module": "path_util",
     "buggy_code": 'import os\n\ndef join_paths(*parts):\n    """Join path parts."""\n    return "/".join(parts)\n\ndef get_extension(filename):\n    """Get file extension without dot."""\n    return filename.split(".")[-1]\n',
     "fixed_code": 'import os\n\ndef join_paths(*parts):\n    """Join path parts, normalized."""\n    return os.path.normpath(os.path.join(*parts))\n\ndef get_extension(filename):\n    """Get file extension without dot."""\n    if "." not in filename:\n        return ""\n    return filename.rsplit(".", 1)[-1].lower()\n',
     "test_code": 'from path_util import join_paths, get_extension\n\ndef test_join():\n    assert join_paths("/home", "user", "file.txt") == "/home/user/file.txt"\n\ndef test_join_normalized():\n    result = join_paths("/home/", "/user/", "file.txt")\n    assert "\\\\" not in result or "/" in result\n    assert "//" not in result\n\ndef test_ext():\n    assert get_extension("file.txt") == "txt"\n    assert get_extension("archive.tar.gz") == "gz"\n    assert get_extension("Makefile") == ""\n\ndef test_ext_case():\n    assert get_extension("FILE.PDF") == "pdf"\n',
     "issue": '`join_paths("/home/", "/user/")` has extra slashes.\n`get_extension("Makefile")` returns "Makefile" instead of "".\n\nRun: `python -m pytest tests/test_path_util.py`'},

    # === test_feedback: test-driven correction ===
    {"task_id": "bugfix_357", "bug_type": "test_feedback", "difficulty": "medium", "module": "stack_util",
     "buggy_code": 'class Stack:\n    def __init__(self):\n        self._items = []\n    def push(self, item):\n        self._items.append(item)\n    def pop(self):\n        return self._items.pop()\n    def peek(self):\n        return self._items[-1]\n    def is_empty(self):\n        return len(self._items) == 0\n    def size(self):\n        return len(self._items)\n',
     "fixed_code": 'class Stack:\n    def __init__(self):\n        self._items = []\n    def push(self, item):\n        self._items.append(item)\n    def pop(self):\n        if self.is_empty():\n            raise IndexError("Pop from empty stack")\n        return self._items.pop()\n    def peek(self):\n        if self.is_empty():\n            raise IndexError("Peek at empty stack")\n        return self._items[-1]\n    def is_empty(self):\n        return len(self._items) == 0\n    def size(self):\n        return len(self._items)\n',
     "test_code": 'import pytest\nfrom stack_util import Stack\n\ndef test_push_pop():\n    s = Stack()\n    s.push(1)\n    s.push(2)\n    assert s.pop() == 2\n    assert s.pop() == 1\n\ndef test_empty():\n    s = Stack()\n    assert s.is_empty() is True\n\ndef test_pop_empty():\n    s = Stack()\n    with pytest.raises(IndexError):\n        s.pop()\n\ndef test_peek():\n    s = Stack()\n    s.push("a")\n    assert s.peek() == "a"\n    assert s.size() == 1\n',
     "issue": '`Stack().pop()` raises unhelpful error on empty stack.\nShould raise IndexError.\n\nRun: `python -m pytest tests/test_stack_util.py`'},

    {"task_id": "bugfix_358", "bug_type": "test_feedback", "difficulty": "medium", "module": "queue_util",
     "buggy_code": 'class Queue:\n    def __init__(self):\n        self._items = []\n    def enqueue(self, item):\n        self._items.append(item)\n    def dequeue(self):\n        return self._items.pop()\n    def peek(self):\n        return self._items[-1]\n    def is_empty(self):\n        return len(self._items) == 0\n',
     "fixed_code": 'class Queue:\n    def __init__(self):\n        self._items = []\n    def enqueue(self, item):\n        self._items.append(item)\n    def dequeue(self):\n        if self.is_empty():\n            raise IndexError("Dequeue from empty queue")\n        return self._items.pop(0)\n    def peek(self):\n        if self.is_empty():\n            raise IndexError("Peek at empty queue")\n        return self._items[0]\n    def is_empty(self):\n        return len(self._items) == 0\n',
     "test_code": 'import pytest\nfrom queue_util import Queue\n\ndef test_fifo():\n    q = Queue()\n    q.enqueue(1)\n    q.enqueue(2)\n    q.enqueue(3)\n    assert q.dequeue() == 1\n    assert q.dequeue() == 2\n\ndef test_peek():\n    q = Queue()\n    q.enqueue("a")\n    q.enqueue("b")\n    assert q.peek() == "a"\n\ndef test_empty():\n    q = Queue()\n    with pytest.raises(IndexError):\n        q.dequeue()\n',
     "issue": 'Queue.dequeue() returns items in LIFO order (stack behavior).\nShould be FIFO.\n\nRun: `python -m pytest tests/test_queue_util.py`'},

    {"task_id": "bugfix_359", "bug_type": "test_feedback", "difficulty": "medium", "module": "cache_util",
     "buggy_code": 'class SimpleCache:\n    def __init__(self, maxsize=3):\n        self.maxsize = maxsize\n        self._cache = {}\n        self._order = []\n\n    def get(self, key):\n        return self._cache.get(key, None)\n\n    def put(self, key, value):\n        if key in self._cache:\n            self._cache[key] = value\n            return\n        if len(self._cache) >= self.maxsize:\n            oldest = self._order.pop(0)\n            del self._cache[oldest]\n        self._cache[key] = value\n        self._order.append(key)\n',
     "fixed_code": 'class SimpleCache:\n    def __init__(self, maxsize=3):\n        self.maxsize = maxsize\n        self._cache = {}\n        self._order = []\n\n    def get(self, key):\n        if key in self._cache:\n            self._order.remove(key)\n            self._order.append(key)\n        return self._cache.get(key, None)\n\n    def put(self, key, value):\n        if key in self._cache:\n            self._order.remove(key)\n        elif len(self._cache) >= self.maxsize:\n            oldest = self._order.pop(0)\n            del self._cache[oldest]\n        self._cache[key] = value\n        self._order.append(key)\n',
     "test_code": 'from cache_util import SimpleCache\n\ndef test_basic():\n    c = SimpleCache(2)\n    c.put("a", 1)\n    c.put("b", 2)\n    assert c.get("a") == 1\n\ndef test_eviction():\n    c = SimpleCache(2)\n    c.put("a", 1)\n    c.put("b", 2)\n    c.put("c", 3)\n    assert c.get("a") is None\n    assert c.get("c") == 3\n\ndef test_lru():\n    c = SimpleCache(2)\n    c.put("a", 1)\n    c.get("a")  # access a\n    c.put("b", 2)\n    c.put("c", 3)  # should evict b, not a\n    assert c.get("a") == 1\n    assert c.get("b") is None\n',
     "issue": 'Cache eviction is not LRU-aware.\n`get("a")` does not update access order.\n\nRun: `python -m pytest tests/test_cache_util.py`'},

    # === regex ===
    {"task_id": "bugfix_360", "bug_type": "regex", "difficulty": "medium", "module": "date_parse",
     "buggy_code": 'import re\n\ndef extract_date(text):\n    """Extract date in YYYY-MM-DD format."""\n    match = re.search(r"\\d{4}-\\d{2}-\\d{2}", text)\n    return match.group() if match else None\n\ndef is_valid_date(date_str):\n    """Check if string is valid date."""\n    return bool(re.match(r"\\d{4}-\\d{2}-\\d{2}", date_str))\n',
     "fixed_code": 'import re\nfrom datetime import datetime\n\ndef extract_date(text):\n    """Extract date in YYYY-MM-DD format."""\n    match = re.search(r"\\d{4}-\\d{2}-\\d{2}", text)\n    return match.group() if match else None\n\ndef is_valid_date(date_str):\n    """Check if string is valid date."""\n    if not re.match(r"^\\d{4}-\\d{2}-\\d{2}$", date_str):\n        return False\n    try:\n        datetime.strptime(date_str, "%Y-%m-%d")\n        return True\n    except ValueError:\n        return False\n',
     "test_code": 'from date_parse import extract_date, is_valid_date\n\ndef test_extract():\n    assert extract_date("born on 2024-01-15") == "2024-01-15"\n    assert extract_date("no date") is None\n\ndef test_valid():\n    assert is_valid_date("2024-01-15") is True\n    assert is_valid_date("2024-13-01") is False\n    assert is_valid_date("2024-02-30") is False\n    assert is_valid_date("not-a-date") is False\n',
     "issue": '`is_valid_date("2024-13-01")` returns True.\nDoes not validate actual date values.\n\nRun: `python -m pytest tests/test_date_parse.py`'},

    # === nested_condition ===
    {"task_id": "bugfix_361", "bug_type": "nested_condition", "difficulty": "medium", "module": "vip_discount",
     "buggy_code": 'def get_discount(is_vip, purchase_amount, is_first_purchase):\n    """Calculate discount percentage."""\n    if is_vip:\n        return 0.20\n    if purchase_amount > 100:\n        return 0.10\n    return 0.0\n',
     "fixed_code": 'def get_discount(is_vip, purchase_amount, is_first_purchase):\n    """Calculate discount percentage."""\n    discount = 0.0\n    if is_vip:\n        discount = 0.20\n    elif purchase_amount > 100:\n        discount = 0.10\n    if is_first_purchase:\n        discount += 0.05\n    return min(discount, 0.30)\n',
     "test_code": 'from vip_discount import get_discount\n\ndef test_vip():\n    assert get_discount(True, 50, False) == 0.20\n\ndef test_high_purchase():\n    assert get_discount(False, 150, False) == 0.10\n\ndef test_first_purchase():\n    assert get_discount(False, 50, True) == 0.05\n\ndef test_vip_first():\n    assert get_discount(True, 200, True) == 0.25\n\ndef test_max_cap():\n    assert get_discount(True, 200, True) <= 0.30\n',
     "issue": 'First-purchase discount not applied.\nVIP + first purchase should stack.\n\nRun: `python -m pytest tests/test_vip_discount.py`'},

    {"task_id": "bugfix_362", "bug_type": "nested_condition", "difficulty": "medium", "module": "access_level",
     "buggy_code": 'def can_access(user_role, resource_level):\n    """Check access: admin=all, editor=read+write, viewer=read only."""\n    levels = {"public": 0, "internal": 1, "confidential": 2, "secret": 3}\n    roles = {"viewer": 1, "editor": 2, "admin": 3}\n    return roles.get(user_role, 0) >= levels.get(resource_level, 0)\n',
     "fixed_code": 'def can_access(user_role, resource_level):\n    """Check access: admin=all, editor=up to confidential, viewer=public+internal."""\n    levels = {"public": 0, "internal": 1, "confidential": 2, "secret": 3}\n    roles = {"viewer": 1, "editor": 2, "admin": 3}\n    user_level = roles.get(user_role, -1)\n    resource = levels.get(resource_level, 99)\n    if user_level < 0:\n        return False\n    return user_level >= resource\n',
     "test_code": 'from access_level import can_access\n\ndef test_admin():\n    assert can_access("admin", "secret") is True\n\ndef test_editor():\n    assert can_access("editor", "confidential") is True\n    assert can_access("editor", "secret") is False\n\ndef test_viewer():\n    assert can_access("viewer", "public") is True\n    assert can_access("viewer", "confidential") is False\n\ndef test_unknown():\n    assert can_access("guest", "public") is False\n',
     "issue": '`can_access("guest", "public")` returns True.\nUnknown roles should be denied.\n\nRun: `python -m pytest tests/test_access_level.py`'},

    # === type_conversion ===
    {"task_id": "bugfix_363", "bug_type": "type_conversion", "difficulty": "easy", "module": "money_util",
     "buggy_code": 'def format_money(amount, currency="USD"):\n    """Format amount as currency string."""\n    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}\n    sym = symbols.get(currency, currency)\n    return f"{sym}{amount}"\n',
     "fixed_code": 'def format_money(amount, currency="USD"):\n    """Format amount as currency string."""\n    symbols = {"USD": "$", "EUR": "€", "GBP": "£"}\n    sym = symbols.get(currency, currency)\n    return f"{sym}{amount:,.2f}"\n',
     "test_code": 'from money_util import format_money\n\ndef test_basic():\n    assert format_money(100) == "$100.00"\n\ndef test_decimals():\n    assert format_money(99.9) == "$99.90"\n\ndef test_eur():\n    r = format_money(50, "EUR")\n    assert "50.00" in r\n\ndef test_large():\n    r = format_money(1234567.89)\n    assert "1,234,567.89" in r\n',
     "issue": '`format_money(99.9)` returns "$99.9" (no trailing zero).\n`format_money(1234567.89)` has no comma separators.\n\nRun: `python -m pytest tests/test_money_util.py`'},

    {"task_id": "bugfix_364", "bug_type": "type_conversion", "difficulty": "medium", "module": "config_merge",
     "buggy_code": 'def merge_configs(base, override):\n    """Deep merge two config dicts."""\n    result = base.copy()\n    for k, v in override.items():\n        if k in result and isinstance(result[k], dict) and isinstance(v, dict):\n            result[k] = merge_configs(result[k], v)\n        else:\n            result[k] = v\n    return result\n\ndef load_config(defaults, user_config):\n    """Load config with defaults."""\n    return merge_configs(defaults, user_config)\n',
     "fixed_code": 'def merge_configs(base, override):\n    """Deep merge two config dicts (non-destructive)."""\n    result = {k: v for k, v in base.items()}\n    for k, v in override.items():\n        if k in result and isinstance(result[k], dict) and isinstance(v, dict):\n            result[k] = merge_configs(result[k], v)\n        else:\n            result[k] = v\n    return result\n\ndef load_config(defaults, user_config):\n    """Load config with defaults."""\n    return merge_configs(defaults, user_config)\n',
     "test_code": 'from config_merge import merge_configs, load_config\n\ndef test_basic():\n    r = merge_configs({"a": 1}, {"b": 2})\n    assert r == {"a": 1, "b": 2}\n\ndef test_nested():\n    r = merge_configs({"db": {"host": "localhost"}}, {"db": {"port": 5432}})\n    assert r == {"db": {"host": "localhost", "port": 5432}}\n\ndef test_no_mutate():\n    base = {"a": {"x": 1}}\n    merge_configs(base, {"a": {"y": 2}})\n    assert "y" not in base["a"]\n',
     "issue": '`merge_configs` mutates the base dict.\n`base["a"]` gets modified after merge.\n\nRun: `python -m pytest tests/test_config_merge.py`'},

    {"task_id": "bugfix_365", "bug_type": "type_conversion", "difficulty": "medium", "module": "safe_json",
     "buggy_code": 'import json\n\ndef safe_loads(s):\n    """Parse JSON string, return None on error."""\n    return json.loads(s)\n\ndef safe_dumps(obj):\n    """Serialize to JSON string."""\n    return json.dumps(obj)\n',
     "fixed_code": 'import json\n\ndef safe_loads(s):\n    """Parse JSON string, return None on error."""\n    try:\n        return json.loads(s)\n    except (json.JSONDecodeError, TypeError):\n        return None\n\ndef safe_dumps(obj, indent=None):\n    """Serialize to JSON string."""\n    try:\n        return json.dumps(obj, indent=indent, ensure_ascii=False)\n    except (TypeError, ValueError):\n        return None\n',
     "test_code": 'from safe_json import safe_loads, safe_dumps\nimport json\n\ndef test_loads():\n    assert safe_loads(\'{"a": 1}\') == {"a": 1}\n\ndef test_loads_error():\n    assert safe_loads("not json") is None\n    assert safe_loads(None) is None\n\ndef test_dumps():\n    assert safe_dumps({"a": 1}) == \'{"a": 1}\'\n\ndef test_dumps_error():\n    assert safe_dumps({1, 2, 3}) is None\n',
     "issue": '`safe_loads("not json")` raises JSONDecodeError.\n`safe_dumps({1,2,3})` raises TypeError.\n\nRun: `python -m pytest tests/test_safe_json.py`'},

    # === off_by_one ===
    {"task_id": "bugfix_366", "bug_type": "off_by_one", "difficulty": "medium", "module": "window_slide",
     "buggy_code": 'def sliding_window(lst, k):\n    """Generate all sliding windows of size k."""\n    return [lst[i:i+k] for i in range(len(lst) - k)]\n',
     "fixed_code": 'def sliding_window(lst, k):\n    """Generate all sliding windows of size k."""\n    if k <= 0 or k > len(lst):\n        return []\n    return [lst[i:i+k] for i in range(len(lst) - k + 1)]\n',
     "test_code": 'from window_slide import sliding_window\n\ndef test_basic():\n    assert sliding_window([1,2,3,4], 2) == [[1,2],[2,3],[3,4]]\n\ndef test_full():\n    assert sliding_window([1,2,3], 3) == [[1,2,3]]\n\ndef test_too_large():\n    assert sliding_window([1,2], 5) == []\n\ndef test_zero():\n    assert sliding_window([1,2,3], 0) == []\n',
     "issue": '`sliding_window([1,2,3,4], 2)` returns `[[1,2],[2,3]]` (missing [3,4]).\n\nRun: `python -m pytest tests/test_window_slide.py`'},

    # === exception_handling ===
    {"task_id": "bugfix_367", "bug_type": "exception_handling", "difficulty": "medium", "module": "chain_util",
     "buggy_code": 'def safe_chain(*funcs):\n    """Chain functions, stop on error."""\n    result = None\n    for f in funcs:\n        result = f(result)\n    return result\n',
     "fixed_code": 'def safe_chain(*funcs):\n    """Chain functions, stop on error, return (result, error)."""\n    result = None\n    for f in funcs:\n        try:\n            result = f(result)\n        except Exception as e:\n            return result, e\n    return result, None\n',
     "test_code": 'from chain_util import safe_chain\n\ndef test_basic():\n    r, err = safe_chain(lambda x: 1, lambda x: x + 1, lambda x: x * 3)\n    assert r == 6\n    assert err is None\n\ndef test_error():\n    r, err = safe_chain(lambda x: 1, lambda x: x/0, lambda x: x+1)\n    assert r == 1\n    assert err is not None\n',
     "issue": '`safe_chain` raises exception instead of handling it.\n\nRun: `python -m pytest tests/test_chain_util.py`'},

    # === boundary_empty ===
    {"task_id": "bugfix_368", "bug_type": "boundary_empty", "difficulty": "easy", "module": "flatten_util",
     "buggy_code": 'def flatten(lst):\n    """Flatten nested list."""\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result\n\ndef flatten_depth(lst, depth=1):\n    """Flatten nested list to given depth."""\n    return flatten(lst)\n',
     "fixed_code": 'def flatten(lst):\n    """Flatten nested list fully."""\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten(item))\n        else:\n            result.append(item)\n    return result\n\ndef flatten_depth(lst, depth=1):\n    """Flatten nested list to given depth."""\n    if depth <= 0:\n        return lst\n    result = []\n    for item in lst:\n        if isinstance(item, list):\n            result.extend(flatten_depth(item, depth - 1))\n        else:\n            result.append(item)\n    return result\n',
     "test_code": 'from flatten_util import flatten, flatten_depth\n\ndef test_flatten():\n    assert flatten([1,[2,[3,4]],5]) == [1,2,3,4,5]\n\ndef test_flatten_empty():\n    assert flatten([]) == []\n    assert flatten([[],[[]]]) == []\n\ndef test_depth():\n    assert flatten_depth([1,[2,[3,[4]]]], 1) == [1,2,[3,[4]]]\n    assert flatten_depth([1,[2,[3]]], 2) == [1,2,3]\n\ndef test_depth_zero():\n    assert flatten_depth([1,[2]], 0) == [1,[2]]\n',
     "issue": '`flatten_depth` ignores depth parameter (always fully flattens).\n\nRun: `python -m pytest tests/test_flatten_util.py`'},

    # === default_arg ===
    {"task_id": "bugfix_369", "bug_type": "default_arg", "difficulty": "easy", "module": "builder_util",
     "buggy_code": 'def build_url(base, path, params={}):\n    """Build URL with query parameters."""\n    url = f"{base.rstrip(\"/\")}/{path.lstrip(\"/\")}"\n    if params:\n        qs = "&".join(f"{k}={v}" for k, v in params.items())\n        url += f"?{qs}"\n    return url\n',
     "fixed_code": 'def build_url(base, path, params=None):\n    """Build URL with query parameters."""\n    if params is None:\n        params = {}\n    url = f"{base.rstrip(\"/\")}/{path.lstrip(\"/\")}"\n    if params:\n        qs = "&".join(f"{k}={v}" for k, v in params.items())\n        url += f"?{qs}"\n    return url\n',
     "test_code": 'from builder_util import build_url\n\ndef test_basic():\n    assert build_url("http://api.com", "/users") == "http://api.com/users"\n\ndef test_params():\n    r = build_url("http://api.com", "/users", {"page": "1"})\n    assert "page=1" in r\n\ndef test_no_mutate():\n    build_url("http://api.com", "/a", {"x": "1"})\n    r = build_url("http://api.com", "/b")\n    assert "x=" not in r\n',
     "issue": 'Second call to `build_url` without params still includes previous params.\nMutable default argument.\n\nRun: `python -m pytest tests/test_builder_util.py`'},

    # === stateful_counter ===
    {"task_id": "bugfix_370", "bug_type": "stateful_counter", "difficulty": "medium", "module": "token_bucket",
     "buggy_code": 'class TokenBucket:\n    _tokens = 10\n\n    def consume(self, n=1):\n        if self._tokens >= n:\n            self._tokens -= n\n            return True\n        return False\n\n    def remaining(self):\n        return self._tokens\n\n    def refill(self):\n        self._tokens = 10\n',
     "fixed_code": 'class TokenBucket:\n    def __init__(self, capacity=10):\n        self._capacity = capacity\n        self._tokens = capacity\n\n    def consume(self, n=1):\n        if self._tokens >= n:\n            self._tokens -= n\n            return True\n        return False\n\n    def remaining(self):\n        return self._tokens\n\n    def refill(self):\n        self._tokens = self._capacity\n',
     "test_code": 'from token_bucket import TokenBucket\n\ndef test_basic():\n    tb = TokenBucket()\n    assert tb.remaining() == 10\n    assert tb.consume(3) is True\n    assert tb.remaining() == 7\n\ndef test_exhaust():\n    tb = TokenBucket(5)\n    assert tb.consume(5) is True\n    assert tb.consume(1) is False\n\ndef test_separate():\n    tb1 = TokenBucket()\n    tb2 = TokenBucket()\n    tb1.consume(5)\n    assert tb2.remaining() == 10\n',
     "issue": 'Two TokenBucket instances share state (class variable).\n`tb1.consume(5)` affects `tb2.remaining()`.\n\nRun: `python -m pytest tests/test_token_bucket.py`'},

    # === multi_branch ===
    {"task_id": "bugfix_371", "bug_type": "multi_branch", "difficulty": "medium", "module": "grade_util",
     "buggy_code": 'def get_gpa(score):\n    """Convert score (0-100) to GPA (0.0-4.0)."""\n    if score >= 90: return 4.0\n    if score >= 80: return 3.0\n    if score >= 70: return 2.0\n    if score >= 60: return 1.0\n',
     "fixed_code": 'def get_gpa(score):\n    """Convert score (0-100) to GPA (0.0-4.0)."""\n    if score < 0 or score > 100:\n        return None\n    if score >= 90: return 4.0\n    if score >= 80: return 3.0\n    if score >= 70: return 2.0\n    if score >= 60: return 1.0\n    return 0.0\n',
     "test_code": 'from grade_util import get_gpa\n\ndef test_a():\n    assert get_gpa(95) == 4.0\n\ndef test_b():\n    assert get_gpa(85) == 3.0\n\ndef test_f():\n    assert get_gpa(50) == 0.0\n\ndef test_invalid():\n    assert get_gpa(-1) is None\n    assert get_gpa(101) is None\n',
     "issue": '`get_gpa(50)` returns None instead of 0.0.\n`get_gpa(-1)` returns None (should also be invalid).\n\nRun: `python -m pytest tests/test_grade_util.py`'},

    # === config_parse ===
    {"task_id": "bugfix_372", "bug_type": "config_parse", "difficulty": "medium", "module": "properties_parse",
     "buggy_code": 'def parse_properties(text):\n    """Parse Java-style properties file."""\n    result = {}\n    for line in text.strip().split("\\n"):\n        line = line.strip()\n        if "=" in line:\n            key, val = line.split("=", 1)\n            result[key.strip()] = val.strip()\n    return result\n',
     "fixed_code": 'def parse_properties(text):\n    """Parse Java-style properties file."""\n    result = {}\n    for line in text.strip().split("\\n"):\n        line = line.strip()\n        if not line or line.startswith("#") or line.startswith("!"):\n            continue\n        if "=" in line:\n            key, val = line.split("=", 1)\n            result[key.strip()] = val.strip()\n        elif ":" in line:\n            key, val = line.split(":", 1)\n            result[key.strip()] = val.strip()\n    return result\n',
     "test_code": 'from properties_parse import parse_properties\n\ndef test_basic():\n    assert parse_properties("host=localhost\\nport=8080") == {"host": "localhost", "port": "8080"}\n\ndef test_comments():\n    r = parse_properties("# comment\\nhost=localhost\\n! another\\nport=8080")\n    assert r == {"host": "localhost", "port": "8080"}\n\ndef test_colon():\n    r = parse_properties("host: localhost")\n    assert r == {"host": "localhost"}\n\ndef test_empty():\n    assert parse_properties("") == {}\n',
     "issue": '`parse_properties` includes comment lines as keys.\nDoes not support `:` separator.\n\nRun: `python -m pytest tests/test_properties_parse.py`'},

    # === string_norm ===
    {"task_id": "bugfix_373", "bug_type": "string_norm", "difficulty": "easy", "module": "plural_util",
     "buggy_code": 'def pluralize(word, count):\n    """Return plural form if count != 1."""\n    if count == 1:\n        return word\n    return word + "s"\n',
     "fixed_code": 'def pluralize(word, count):\n    """Return plural form if count != 1."""\n    if count == 1:\n        return word\n    if word.endswith("y") and word[-2] not in "aeiou":\n        return word[:-1] + "ies"\n    if word.endswith(("s", "sh", "ch", "x", "z")):\n        return word + "es"\n    return word + "s"\n',
     "test_code": 'from plural_util import pluralize\n\ndef test_basic():\n    assert pluralize("cat", 2) == "cats"\n    assert pluralize("cat", 1) == "cat"\n\ndef test_y():\n    assert pluralize("city", 3) == "cities"\n    assert pluralize("day", 3) == "days"\n\ndef test_s():\n    assert pluralize("bus", 3) == "buses"\n    assert pluralize("wish", 3) == "wishes"\n',
     "issue": '`pluralize("city", 3)` returns "citys" instead of "cities".\n`pluralize("bus", 3)` returns "buss" instead of "buses".\n\nRun: `python -m pytest tests/test_plural_util.py`'},

    # === list_mutation ===
    {"task_id": "bugfix_374", "bug_type": "list_mutation", "difficulty": "medium", "module": "unique_util",
     "buggy_code": 'def unique_preserve_order(lst):\n    """Remove duplicates preserving order."""\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result\n\ndef unique_by_key(lst, key):\n    """Remove duplicates by key function."""\n    return unique_preserve_order(lst)\n',
     "fixed_code": 'def unique_preserve_order(lst):\n    """Remove duplicates preserving order."""\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result\n\ndef unique_by_key(lst, key):\n    """Remove duplicates by key function."""\n    seen = set()\n    result = []\n    for item in lst:\n        k = key(item)\n        if k not in seen:\n            seen.add(k)\n            result.append(item)\n    return result\n',
     "test_code": 'from unique_util import unique_preserve_order, unique_by_key\n\ndef test_basic():\n    assert unique_preserve_order([1,2,2,3,3,3]) == [1,2,3]\n\ndef test_by_key():\n    data = [{"id":1,"name":"a"},{"id":2,"name":"b"},{"id":1,"name":"c"}]\n    result = unique_by_key(data, lambda x: x["id"])\n    assert len(result) == 2\n    assert result[0]["name"] == "a"\n',
     "issue": '`unique_by_key` ignores the key function.\nDeduplicates by identity instead of by key.\n\nRun: `python -m pytest tests/test_unique_util.py`'},

    # === regex (more) ===
    {"task_id": "bugfix_375", "bug_type": "regex", "difficulty": "medium", "module": "csv_util",
     "buggy_code": 'import re\n\ndef parse_csv_simple(text):\n    """Parse simple CSV (no quotes)."""\n    lines = text.strip().split("\\n")\n    return [line.split(",") for line in lines]\n\ndef count_columns(text):\n    """Count columns in first row."""\n    lines = text.strip().split("\\n")\n    return len(lines[0].split(",")) if lines else 0\n',
     "fixed_code": 'import csv, io\n\ndef parse_csv_simple(text):\n    """Parse CSV handling quoted fields."""\n    reader = csv.reader(io.StringIO(text.strip()))\n    return [row for row in reader]\n\ndef count_columns(text):\n    """Count columns in first row."""\n    rows = parse_csv_simple(text)\n    return len(rows[0]) if rows else 0\n',
     "test_code": 'from csv_util import parse_csv_simple, count_columns\n\ndef test_simple():\n    assert parse_csv_simple("a,b,c\\n1,2,3") == [["a","b","c"],["1","2","3"]]\n\ndef test_quoted():\n    result = parse_csv_simple(\'"hello, world",b,c\')\n    assert result[0][0] == "hello, world"\n\ndef test_count():\n    assert count_columns("a,b,c\\n1,2,3") == 3\n',
     "issue": '`parse_csv_simple` splits on commas inside quoted fields.\n`"hello, world"` becomes two fields.\n\nRun: `python -m pytest tests/test_csv_util.py`'},

    # === date_time ===
    {"task_id": "bugfix_376", "bug_type": "date_time", "difficulty": "medium", "module": "age_util",
     "buggy_code": 'from datetime import date\n\ndef age_in_days(birth_date):\n    """Calculate age in days."""\n    return (date.today() - birth_date).days\n\ndef is_birthday_today(birth_date):\n    """Check if today is birthday."""\n    today = date.today()\n    return birth_date.month == today.month and birth_date.day == today.day\n',
     "fixed_code": 'from datetime import date\n\ndef age_in_days(birth_date):\n    """Calculate age in days."""\n    if birth_date > date.today():\n        return 0\n    return (date.today() - birth_date).days\n\ndef is_birthday_today(birth_date):\n    """Check if today is birthday."""\n    today = date.today()\n    return birth_date.month == today.month and birth_date.day == today.day\n\ndef days_until_birthday(birth_date):\n    """Calculate days until next birthday."""\n    today = date.today()\n    this_year = date(today.year, birth_date.month, birth_date.day)\n    if this_year >= today:\n        return (this_year - today).days\n    next_year = date(today.year + 1, birth_date.month, birth_date.day)\n    return (next_year - today).days\n',
     "test_code": 'from datetime import date, timedelta\nfrom age_util import age_in_days, is_birthday_today, days_until_birthday\n\ndef test_age():\n    assert age_in_days(date.today() - timedelta(days=100)) == 100\n\ndef test_future():\n    assert age_in_days(date.today() + timedelta(days=10)) == 0\n\ndef test_birthday():\n    assert is_birthday_today(date.today()) is True\n\ndef test_days_until():\n    d = days_until_birthday(date.today())\n    assert d == 0\n',
     "issue": '`age_in_days(future_date)` returns negative.\n`days_until_birthday` not implemented.\n\nRun: `python -m pytest tests/test_age_util.py`'},

    # === multi_file ===
    {"task_id": "bugfix_377", "bug_type": "multi_file", "difficulty": "hard", "module": "event_bus",
     "buggy_code": 'class EventBus:\n    def __init__(self):\n        self._handlers = {}\n\n    def on(self, event, handler):\n        if event not in self._handlers:\n            self._handlers[event] = []\n        self._handlers[event].append(handler)\n\n    def emit(self, event, data=None):\n        for handler in self._handlers.get(event, []):\n            handler(data)\n\n    def off(self, event, handler):\n        if event in self._handlers:\n            self._handlers[event].remove(handler)\n',
     "fixed_code": 'class EventBus:\n    def __init__(self):\n        self._handlers = {}\n\n    def on(self, event, handler):\n        if event not in self._handlers:\n            self._handlers[event] = []\n        self._handlers[event].append(handler)\n\n    def emit(self, event, data=None):\n        for handler in list(self._handlers.get(event, [])):\n            handler(data)\n\n    def off(self, event, handler=None):\n        if event not in self._handlers:\n            return\n        if handler is None:\n            del self._handlers[event]\n        elif handler in self._handlers[event]:\n            self._handlers[event].remove(handler)\n\n    def once(self, event, handler):\n        def wrapper(data):\n            handler(data)\n            self.off(event, wrapper)\n        self.on(event, wrapper)\n',
     "test_code": 'from event_bus import EventBus\n\ndef test_basic():\n    eb = EventBus()\n    results = []\n    eb.on("test", lambda d: results.append(d))\n    eb.emit("test", "hello")\n    assert results == ["hello"]\n\ndef test_off():\n    eb = EventBus()\n    results = []\n    h = lambda d: results.append(d)\n    eb.on("test", h)\n    eb.off("test", h)\n    eb.emit("test", "hello")\n    assert results == []\n\ndef test_once():\n    eb = EventBus()\n    results = []\n    eb.once("test", lambda d: results.append(d))\n    eb.emit("test", "a")\n    eb.emit("test", "b")\n    assert results == ["a"]\n\ndef test_off_all():\n    eb = EventBus()\n    eb.on("test", lambda d: None)\n    eb.off("test")\n    assert len(eb._handlers.get("test", [])) == 0\n',
     "issue": '`off()` does not support removing all handlers.\n`once()` not implemented.\nEmit during handler modification may skip handlers.\n\nRun: `python -m pytest tests/test_event_bus.py`'},

    # === exception_handling (more) ===
    {"task_id": "bugfix_378", "bug_type": "exception_handling", "difficulty": "medium", "module": "retry_util",
     "buggy_code": 'import time\n\ndef retry(func, max_attempts=3, delay=1):\n    """Retry function on failure."""\n    for i in range(max_attempts):\n        try:\n            return func()\n        except Exception:\n            time.sleep(delay)\n    return None\n',
     "fixed_code": 'import time\n\ndef retry(func, max_attempts=3, delay=1, backoff=1):\n    """Retry function on failure with exponential backoff."""\n    last_error = None\n    for i in range(max_attempts):\n        try:\n            return func()\n        except Exception as e:\n            last_error = e\n            if i < max_attempts - 1:\n                time.sleep(delay * (backoff ** i))\n    raise last_error\n',
     "test_code": 'import pytest\nfrom retry_util import retry\n\ndef test_success():\n    c = [0]\n    def f():\n        c[0] += 1\n        if c[0] < 3:\n            raise ValueError("not yet")\n        return "ok"\n    assert retry(f, max_attempts=5, delay=0) == "ok"\n\ndef test_all_fail():\n    def f():\n        raise ValueError("always")\n    with pytest.raises(ValueError):\n        retry(f, max_attempts=2, delay=0)\n\ndef test_no_none():\n    def f():\n        raise RuntimeError("err")\n    with pytest.raises(RuntimeError):\n        retry(f, max_attempts=1, delay=0)\n',
     "issue": '`retry` silently returns None on exhaustion.\nShould raise the last error.\n\nRun: `python -m pytest tests/test_retry_util.py`'},

    # === boundary_empty (more) ===
    {"task_id": "bugfix_379", "bug_type": "boundary_empty", "difficulty": "easy", "module": "stats_util",
     "buggy_code": 'def mean(values):\n    """Calculate mean."""\n    return sum(values) / len(values)\n\ndef median(values):\n    """Calculate median."""\n    s = sorted(values)\n    n = len(s)\n    if n % 2 == 1:\n        return s[n // 2]\n    return (s[n//2 - 1] + s[n//2]) / 2\n',
     "fixed_code": 'def mean(values):\n    """Calculate mean."""\n    if not values:\n        return 0\n    return sum(values) / len(values)\n\ndef median(values):\n    """Calculate median."""\n    if not values:\n        return 0\n    s = sorted(values)\n    n = len(s)\n    if n % 2 == 1:\n        return s[n // 2]\n    return (s[n//2 - 1] + s[n//2]) / 2\n',
     "test_code": 'from stats_util import mean, median\n\ndef test_mean():\n    assert mean([1,2,3,4,5]) == 3.0\n\ndef test_mean_empty():\n    assert mean([]) == 0\n\ndef test_median():\n    assert median([3,1,2]) == 2\n    assert median([1,2,3,4]) == 2.5\n\ndef test_median_empty():\n    assert median([]) == 0\n',
     "issue": '`mean([])` and `median([])` raise ZeroDivisionError/IndexError.\n\nRun: `python -m pytest tests/test_stats_util.py`'},

    {"task_id": "bugfix_380", "bug_type": "boundary_empty", "difficulty": "medium", "module": "group_util",
     "buggy_code": 'def group_by(items, key_func):\n    """Group items by key function."""\n    groups = {}\n    for item in items:\n        key = key_func(item)\n        groups[key].append(item)\n    return groups\n',
     "fixed_code": 'from collections import defaultdict\n\ndef group_by(items, key_func):\n    """Group items by key function."""\n    groups = defaultdict(list)\n    for item in items:\n        key = key_func(item)\n        groups[key].append(item)\n    return dict(groups)\n',
     "test_code": 'from group_util import group_by\n\ndef test_basic():\n    r = group_by([1,2,3,4,5], lambda x: x % 2)\n    assert r[0] == [2, 4]\n    assert r[1] == [1, 3, 5]\n\ndef test_strings():\n    r = group_by(["a","bb","ccc"], len)\n    assert r[1] == ["a"]\n    assert r[2] == ["bb"]\n\ndef test_empty():\n    assert group_by([], lambda x: x) == {}\n',
     "issue": '`group_by` raises KeyError for new keys.\nShould use defaultdict or check before append.\n\nRun: `python -m pytest tests/test_group_util.py`'},
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
    print(f"Building {len(TASKS)} independent eval tasks...")
    for task in TASKS:
        build_task_dir(tasks_root, task)
        print(f"  {task['task_id']}: {task['bug_type']} ({task['difficulty']})")

    splits_dir = root / "outputs" / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    (splits_dir / "dpo_independent_eval_tasks.txt").write_text(
        "\n".join(t["task_id"] for t in TASKS) + "\n", encoding="utf-8"
    )

    bt = {}
    for t in TASKS:
        bt[t["bug_type"]] = bt.get(t["bug_type"], 0) + 1
    print(f"\nTotal: {len(TASKS)} tasks")
    print(f"Bug types: {bt}")


if __name__ == "__main__":
    main()
