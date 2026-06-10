"""Build harder new100 held-out tasks (bugfix_251-350).

Bug types: regex, date_time, path_norm, exception, nested_condition,
type_conversion, list_mutation, off_by_one, multi_branch, default_arg,
stateful_counter, multi_file, config_parse, string_norm, boundary_empty.
"""
from __future__ import annotations
import json
from pathlib import Path


def make_task(task_id, bug_type, difficulty, module, buggy_code, fixed_code,
              test_code, issue, target_file=None):
    if target_file is None:
        target_file = f"{module}.py"
    return {
        "task_id": task_id,
        "bug_type": bug_type,
        "difficulty": difficulty,
        "module": module,
        "buggy_code": buggy_code,
        "fixed_code": fixed_code,
        "test_code": test_code,
        "issue": issue,
        "target_file": target_file,
        "scripted_fix": {
            "path": target_file,
            "old": buggy_code.strip(),
            "new": fixed_code.strip(),
        },
    }


TASKS = [
    # === regex ===
    make_task("bugfix_251", "regex", "medium", "email_check",
        'import re\n\ndef is_valid_email(email):\n    """Check if email is valid."""\n    pattern = r"\\w+@\\w+"\n    return bool(re.match(pattern, email))\n',
        'import re\n\ndef is_valid_email(email):\n    """Check if email is valid."""\n    pattern = r"^[\\w.+-]+@[\\w-]+\\.[a-zA-Z]{2,}$"\n    return bool(re.match(pattern, email))\n',
        'from email_check import is_valid_email\n\ndef test_valid():\n    assert is_valid_email("user@example.com") is True\n\ndef test_no_domain():\n    assert is_valid_email("user@") is False\n\ndef test_no_tld():\n    assert is_valid_email("user@com") is False\n\ndef test_plain():\n    assert is_valid_email("plainaddress") is False\n',
        '`is_valid_email("user@")` returns `True` but should return `False`.\n\nThe regex pattern is too permissive.\n\nRun: `python -m pytest tests/test_email_check.py`'),

    make_task("bugfix_252", "regex", "medium", "phone_fmt",
        'import re\n\ndef format_phone(number):\n    """Format phone number to (XXX) XXX-XXXX."""\n    digits = re.sub(r"\\D", "", number)\n    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"\n',
        'import re\n\ndef format_phone(number):\n    """Format phone number to (XXX) XXX-XXXX."""\n    digits = re.sub(r"\\D", "", number)\n    if len(digits) != 10:\n        return None\n    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"\n',
        'from phone_fmt import format_phone\n\ndef test_valid():\n    assert format_phone("1234567890") == "(123) 456-7890"\n\ndef test_with_dashes():\n    assert format_phone("123-456-7890") == "(123) 456-7890"\n\ndef test_short():\n    assert format_phone("123") is None\n\ndef test_long():\n    assert format_phone("12345678901") is None\n',
        '`format_phone("123")` should return `None` for invalid length, but returns `"(12) 3-3"`.\n\nNo length validation on extracted digits.\n\nRun: `python -m pytest tests/test_phone_fmt.py`'),

    # === date_time ===
    make_task("bugfix_253", "date_time", "medium", "date_diff",
        'from datetime import datetime\n\ndef days_between(date1, date2):\n    """Return absolute days between two dates."""\n    d1 = datetime.strptime(date1, "%Y-%m-%d")\n    d2 = datetime.strptime(date2, "%Y-%m-%d")\n    return (d1 - d2).days\n',
        'from datetime import datetime\n\ndef days_between(date1, date2):\n    """Return absolute days between two dates."""\n    d1 = datetime.strptime(date1, "%Y-%m-%d")\n    d2 = datetime.strptime(date2, "%Y-%m-%d")\n    return abs((d1 - d2).days)\n',
        'from date_diff import days_between\n\ndef test_forward():\n    assert days_between("2024-01-10", "2024-01-01") == 9\n\ndef test_backward():\n    assert days_between("2024-01-01", "2024-01-10") == 9\n\ndef test_same():\n    assert days_between("2024-01-01", "2024-01-01") == 0\n',
        '`days_between("2024-01-01", "2024-01-10")` returns `-9` instead of `9`.\n\nShould return absolute difference.\n\nRun: `python -m pytest tests/test_date_diff.py`'),

    make_task("bugfix_254", "date_time", "medium", "age_calc",
        'from datetime import datetime, date\n\ndef calculate_age(birth_date_str):\n    """Calculate age from birth date string YYYY-MM-DD."""\n    birth = datetime.strptime(birth_date_str, "%Y-%m-%d").date()\n    today = date.today()\n    return today.year - birth.year\n',
        'from datetime import datetime, date\n\ndef calculate_age(birth_date_str):\n    """Calculate age from birth date string YYYY-MM-DD."""\n    birth = datetime.strptime(birth_date_str, "%Y-%m-%d").date()\n    today = date.today()\n    age = today.year - birth.year\n    if (today.month, today.day) < (birth.month, birth.day):\n        age -= 1\n    return age\n',
        'from unittest.mock import patch\nfrom datetime import date\nfrom age_calc import calculate_age\n\ndef test_past_birthday():\n    with patch("age_calc.date") as mock_date:\n        mock_date.today.return_value = date(2024, 6, 15)\n        mock_date.side_effect = lambda *a, **k: date(*a, **k)\n        assert calculate_age("2000-01-01") == 24\n\ndef test_future_birthday():\n    with patch("age_calc.date") as mock_date:\n        mock_date.today.return_value = date(2024, 3, 15)\n        mock_date.side_effect = lambda *a, **k: date(*a, **k)\n        assert calculate_age("2000-06-01") == 23\n',
        '`calculate_age("2000-06-01")` returns 24 when today is 2024-03-15, but should return 23.\n\nBirthday has not occurred yet this year.\n\nRun: `python -m pytest tests/test_age_calc.py`'),

    # === nested_condition ===
    make_task("bugfix_255", "nested_condition", "medium", "discount_calc",
        'def calculate_discount(age, is_member, purchase_amount):\n    """Calculate discount percentage."""\n    if age >= 65:\n        discount = 0.20\n    elif is_member:\n        discount = 0.10\n    elif purchase_amount > 100:\n        discount = 0.05\n    return discount\n',
        'def calculate_discount(age, is_member, purchase_amount):\n    """Calculate discount percentage."""\n    if age >= 65 and is_member:\n        discount = 0.25\n    elif age >= 65:\n        discount = 0.20\n    elif is_member:\n        discount = 0.10\n    elif purchase_amount > 100:\n        discount = 0.05\n    else:\n        discount = 0.0\n    return discount\n',
        'from discount_calc import calculate_discount\n\ndef test_senior_member():\n    assert calculate_discount(70, True, 50) == 0.25\n\ndef test_senior_non_member():\n    assert calculate_discount(70, False, 50) == 0.20\n\ndef test_member():\n    assert calculate_discount(30, True, 50) == 0.10\n\ndef test_no_discount():\n    assert calculate_discount(30, False, 50) == 0.0\n',
        '`calculate_discount(70, True, 50)` should return 0.25 (senior + member combo), but returns 0.20.\n\nAlso crashes for non-qualifying inputs.\n\nRun: `python -m pytest tests/test_discount_calc.py`'),

    # === type_conversion ===
    make_task("bugfix_256", "type_conversion", "easy", "avg_score",
        'def average_score(scores):\n    """Calculate average of a list of scores."""\n    if not scores:\n        return 0\n    return sum(scores) / len(scores)\n',
        'def average_score(scores):\n    """Calculate average of a list of numeric scores."""\n    if not scores:\n        return 0\n    numeric = [float(s) for s in scores]\n    return sum(numeric) / len(numeric)\n',
        'from avg_score import average_score\n\ndef test_ints():\n    assert average_score([80, 90, 100]) == 90.0\n\ndef test_strings():\n    assert average_score(["80", "90", "100"]) == 90.0\n\ndef test_empty():\n    assert average_score([]) == 0\n\ndef test_mixed():\n    assert average_score(["85", 90, "95"]) == 90.0\n',
        '`average_score(["80", "90", "100"])` raises TypeError.\n\nShould handle string scores.\n\nRun: `python -m pytest tests/test_avg_score.py`'),

    # === list_mutation ===
    make_task("bugfix_257", "list_mutation", "medium", "queue_ops",
        'class Queue:\n    def __init__(self):\n        self.items = []\n\n    def enqueue(self, item):\n        self.items.append(item)\n\n    def dequeue(self):\n        return self.items.pop()\n\n    def peek(self):\n        return self.items[-1]\n',
        'class Queue:\n    def __init__(self):\n        self.items = []\n\n    def enqueue(self, item):\n        self.items.append(item)\n\n    def dequeue(self):\n        return self.items.pop(0)\n\n    def peek(self):\n        return self.items[0]\n',
        'from queue_ops import Queue\n\ndef test_fifo():\n    q = Queue()\n    q.enqueue(1)\n    q.enqueue(2)\n    q.enqueue(3)\n    assert q.dequeue() == 1\n    assert q.dequeue() == 2\n\ndef test_peek():\n    q = Queue()\n    q.enqueue("a")\n    q.enqueue("b")\n    assert q.peek() == "a"\n    assert q.dequeue() == "a"\n',
        'Queue.dequeue() returns items in LIFO order instead of FIFO.\n\n`enqueue(1); enqueue(2); dequeue()` returns `2` instead of `1`.\n\nRun: `python -m pytest tests/test_queue_ops.py`'),

    # === off_by_one ===
    make_task("bugfix_258", "off_by_one", "easy", "chunk_list",
        'def chunk_list(lst, size):\n    """Split list into chunks of given size."""\n    return [lst[i:i+size] for i in range(0, len(lst), size)]\n',
        'def chunk_list(lst, size):\n    """Split list into chunks of given size."""\n    if size <= 0:\n        raise ValueError("Chunk size must be positive")\n    return [lst[i:i+size] for i in range(0, len(lst), size)]\n',
        'import pytest\nfrom chunk_list import chunk_list\n\ndef test_basic():\n    assert chunk_list([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]\n\ndef test_exact():\n    assert chunk_list([1,2,3,4], 2) == [[1,2],[3,4]]\n\ndef test_zero_size():\n    with pytest.raises(ValueError):\n        chunk_list([1,2,3], 0)\n\ndef test_negative():\n    with pytest.raises(ValueError):\n        chunk_list([1,2,3], -1)\n',
        '`chunk_list([1,2,3], 0)` causes infinite loop instead of raising ValueError.\n\nNo validation for zero/negative chunk size.\n\nRun: `python -m pytest tests/test_chunk_list.py`'),

    # === exception_handling ===
    make_task("bugfix_259", "exception_handling", "medium", "safe_div",
        'def safe_divide(a, b):\n    """Divide a by b, return None on error."""\n    try:\n        return a / b\n    except ZeroDivisionError:\n        return None\n',
        'def safe_divide(a, b):\n    """Divide a by b, return None on error."""\n    try:\n        return a / b\n    except (ZeroDivisionError, TypeError):\n        return None\n',
        'from safe_div import safe_divide\n\ndef test_normal():\n    assert safe_divide(10, 2) == 5.0\n\ndef test_zero():\n    assert safe_divide(10, 0) is None\n\ndef test_string():\n    assert safe_divide("10", 2) is None\n\ndef test_none():\n    assert safe_divide(None, 2) is None\n',
        '`safe_divide("10", 2)` raises TypeError instead of returning None.\n\nOnly catches ZeroDivisionError, not TypeError.\n\nRun: `python -m pytest tests/test_safe_div.py`'),

    # === default_arg ===
    make_task("bugfix_260", "default_arg", "medium", "greet_user",
        'def greet(name, greeting="Hello"):\n    """Return greeting string."""\n    names = []\n    names.append(name)\n    return f"{greeting}, {names[-1]}!"\n',
        'def greet(name, greeting="Hello"):\n    """Return greeting string."""\n    return f"{greeting}, {name}!"\n',
        'from greet_user import greet\n\ndef test_default():\n    assert greet("Alice") == "Hello, Alice!"\n\ndef test_custom():\n    assert greet("Bob", "Hi") == "Hi, Bob!"\n\ndef test_repeated():\n    assert greet("Alice") == "Hello, Alice!"\n    assert greet("Bob") == "Hello, Bob!"\n',
        'Calling greet("Bob") after greet("Alice") returns "Hello, Alice!" instead of "Hello, Bob!".\n\nMutable default argument causes state leakage.\n\nRun: `python -m pytest tests/test_greet_user.py`'),
]

# === Generate more tasks programmatically ===
# Additional task templates for harder bug types

EXTRA_TASKS = [
    # boundary + empty input
    make_task("bugfix_261", "boundary_empty", "medium", "word_count",
        'def word_count(text):\n    """Count words in text."""\n    return len(text.split())\n',
        'def word_count(text):\n    """Count words in text."""\n    if not text or not text.strip():\n        return 0\n    return len(text.split())\n',
        'from word_count import word_count\n\ndef test_normal():\n    assert word_count("hello world") == 2\n\ndef test_empty():\n    assert word_count("") == 0\n\ndef test_spaces():\n    assert word_count("   ") == 0\n\ndef test_single():\n    assert word_count("hello") == 1\n',
        '`word_count("")` returns 1 instead of 0.\n`word_count("   ")` returns 1 instead of 0.\n\nRun: `python -m pytest tests/test_word_count.py`'),

    # string normalization
    make_task("bugfix_262", "string_norm", "easy", "slug_gen",
        'def generate_slug(title):\n    """Generate URL slug from title."""\n    return title.replace(" ", "-")\n',
        'def generate_slug(title):\n    """Generate URL slug from title."""\n    import re\n    slug = title.lower().strip()\n    slug = re.sub(r"[^a-z0-9]+", "-", slug)\n    return slug.strip("-")\n',
        'from slug_gen import generate_slug\n\ndef test_basic():\n    assert generate_slug("Hello World") == "hello-world"\n\ndef test_special():\n    assert generate_slug("Hello! @World#") == "hello-world"\n\ndef test_spaces():\n    assert generate_slug("  Hello  World  ") == "hello-world"\n\ndef test_upper():\n    assert generate_slug("UPPER CASE") == "upper-case"\n',
        '`generate_slug("Hello! @World#")` returns "Hello!-@World#" instead of "hello-world".\n\nDoes not handle special characters or case.\n\nRun: `python -m pytest tests/test_slug_gen.py`'),

    # multi-branch return
    make_task("bugfix_263", "multi_branch", "medium", "grade_calc",
        'def get_grade(score):\n    """Return letter grade for score."""\n    if score >= 90:\n        return "A"\n    elif score >= 80:\n        return "B"\n    elif score >= 70:\n        return "C"\n    elif score >= 60:\n        return "D"\n',
        'def get_grade(score):\n    """Return letter grade for score."""\n    if score >= 90:\n        return "A"\n    elif score >= 80:\n        return "B"\n    elif score >= 70:\n        return "C"\n    elif score >= 60:\n        return "D"\n    else:\n        return "F"\n',
        'from grade_calc import get_grade\n\ndef test_a():\n    assert get_grade(95) == "A"\n\ndef test_b():\n    assert get_grade(85) == "B"\n\ndef test_f():\n    assert get_grade(50) == "F"\n\ndef test_exact_boundary():\n    assert get_grade(90) == "A"\n    assert get_grade(60) == "D"\n',
        '`get_grade(50)` returns None instead of "F".\n\nMissing else branch for failing scores.\n\nRun: `python -m pytest tests/test_grade_calc.py`'),

    # stateful counter
    make_task("bugfix_264", "stateful_counter", "medium", "counter_util",
        'class Counter:\n    _count = 0\n\n    def increment(self):\n        self._count += 1\n        return self._count\n\n    def reset(self):\n        self._count = 0\n',
        'class Counter:\n    def __init__(self):\n        self._count = 0\n\n    def increment(self):\n        self._count += 1\n        return self._count\n\n    def reset(self):\n        self._count = 0\n',
        'from counter_util import Counter\n\ndef test_independent():\n    c1 = Counter()\n    c2 = Counter()\n    c1.increment()\n    c1.increment()\n    assert c1.increment() == 3\n    assert c2.increment() == 1\n\ndef test_reset():\n    c = Counter()\n    c.increment()\n    c.reset()\n    assert c.increment() == 1\n',
        'Two Counter instances share state.\n`c1.increment()` 3 times, then `c2.increment()` returns 4 instead of 1.\n\nClass variable used instead of instance variable.\n\nRun: `python -m pytest tests/test_counter_util.py`'),

    # path normalization
    make_task("bugfix_265", "path_norm", "medium", "path_join",
        'import os\n\ndef join_paths(base, *parts):\n    """Join path parts."""\n    result = base\n    for part in parts:\n        result = result + "/" + part\n    return result\n',
        'import os\n\ndef join_paths(base, *parts):\n    """Join path parts, normalizing separators."""\n    result = base\n    for part in parts:\n        result = os.path.join(result, part)\n    return os.path.normpath(result)\n',
        'from path_join import join_paths\n\ndef test_basic():\n    assert join_paths("/home", "user", "file.txt") == "/home/user/file.txt"\n\ndef test_trailing_slash():\n    assert join_paths("/home/", "/user/", "file.txt") == "/home/user/file.txt"\n\ndef test_double_slash():\n    result = join_paths("/home", "", "user")\n    assert "//" not in result\n',
        '`join_paths("/home/", "/user/")` returns "/home///user/" with extra slashes.\n\nNo path normalization.\n\nRun: `python -m pytest tests/test_path_join.py`'),

    # config parsing
    make_task("bugfix_266", "config_parse", "medium", "ini_parser",
        'def parse_ini(text):\n    """Simple INI parser returning dict of sections."""\n    result = {}\n    current = None\n    for line in text.strip().split("\\n"):\n        line = line.strip()\n        if line.startswith("[") and line.endswith("]"):\n            current = line[1:-1]\n            result[current] = {}\n        elif "=" in line and current:\n            key, val = line.split("=", 1)\n            result[current][key.strip()] = val.strip()\n    return result\n',
        'def parse_ini(text):\n    """Simple INI parser returning dict of sections."""\n    result = {}\n    current = None\n    for line in text.strip().split("\\n"):\n        line = line.strip()\n        if not line or line.startswith(";") or line.startswith("#"):\n            continue\n        if line.startswith("[") and line.endswith("]"):\n            current = line[1:-1]\n            result[current] = {}\n        elif "=" in line and current:\n            key, val = line.split("=", 1)\n            result[current][key.strip()] = val.strip()\n    return result\n',
        'from ini_parser import parse_ini\n\ndef test_basic():\n    result = parse_ini("[section]\\nkey=value")\n    assert result == {"section": {"key": "value"}}\n\ndef test_comments():\n    result = parse_ini("[s]\\n; comment\\nkey=val\\n# another")\n    assert result == {"s": {"key": "val"}}\n\ndef test_empty():\n    assert parse_ini("") == {}\n',
        '`parse_ini("[s]\\n; comment\\nkey=val")` includes comment as a key.\n\nDoes not skip comment lines starting with ; or #.\n\nRun: `python -m pytest tests/test_ini_parser.py`'),

    # list mutation (harder)
    make_task("bugfix_267", "list_mutation", "hard", "matrix_ops",
        'def transpose(matrix):\n    """Transpose a 2D matrix."""\n    return [list(row) for row in zip(*matrix)]\n\ndef rotate_90(matrix):\n    """Rotate matrix 90 degrees clockwise."""\n    return [list(row) for row in zip(*matrix[::-1])]\n\ndef flatten(matrix):\n    """Flatten 2D matrix to 1D list."""\n    result = []\n    for row in matrix:\n        result.extend(row)\n    return result\n\ndef multiply(a, b):\n    """Multiply two 2x2 matrices."""\n    result = [[0, 0], [0, 0]]\n    for i in range(2):\n        for j in range(2):\n            for k in range(2):\n                result[i][j] += a[i][k] * b[k][j]\n    return result\n',
        'def transpose(matrix):\n    """Transpose a 2D matrix."""\n    return [list(row) for row in zip(*matrix)]\n\ndef rotate_90(matrix):\n    """Rotate matrix 90 degrees clockwise."""\n    return [list(row) for row in zip(*matrix[::-1])]\n\ndef flatten(matrix):\n    """Flatten 2D matrix to 1D list."""\n    result = []\n    for row in matrix:\n        result.extend(row)\n    return result\n\ndef multiply(a, b):\n    """Multiply two 2x2 matrices."""\n    rows_a, cols_a = len(a), len(a[0])\n    rows_b, cols_b = len(b), len(b[0])\n    if cols_a != rows_b:\n        raise ValueError("Incompatible dimensions")\n    result = [[0]*cols_b for _ in range(rows_a)]\n    for i in range(rows_a):\n        for j in range(cols_b):\n            for k in range(cols_a):\n                result[i][j] += a[i][k] * b[k][j]\n    return result\n',
        'import pytest\nfrom matrix_ops import transpose, rotate_90, flatten, multiply\n\ndef test_transpose():\n    assert transpose([[1,2],[3,4]]) == [[1,3],[2,4]]\n\ndef test_rotate():\n    assert rotate_90([[1,2],[3,4]]) == [[3,1],[4,2]]\n\ndef test_flatten():\n    assert flatten([[1,2],[3,4]]) == [1,2,3,4]\n\ndef test_multiply():\n    assert multiply([[1,2],[3,4]], [[5,6],[7,8]]) == [[19,22],[43,50]]\n\ndef test_multiply_3x3():\n    a = [[1,2,3],[4,5,6],[7,8,9]]\n    b = [[1,0,0],[0,1,0],[0,0,1]]\n    assert multiply(a, b) == a\n\ndef test_incompatible():\n    with pytest.raises(ValueError):\n        multiply([[1,2]], [[1,2,3]])\n',
        '`multiply` only works for 2x2 matrices.\n`multiply([[1,2,3],[4,5,6],[7,8,9]], identity)` raises IndexError.\n\nHardcoded size 2 instead of using actual dimensions.\n\nRun: `python -m pytest tests/test_matrix_ops.py`'),

    # nested condition (harder)
    make_task("bugfix_268", "nested_condition", "hard", "access_ctrl",
        'def check_access(user_role, resource_type, is_owner, is_published):\n    """Check if user can access resource."""\n    if user_role == "admin":\n        return True\n    if resource_type == "public":\n        return True\n    if is_owner:\n        return True\n    return False\n',
        'def check_access(user_role, resource_type, is_owner, is_published):\n    """Check if user can access resource."""\n    if user_role == "admin":\n        return True\n    if resource_type == "public" and is_published:\n        return True\n    if resource_type == "private" and is_owner:\n        return True\n    if resource_type == "shared" and (is_owner or is_published):\n        return True\n    return False\n',
        'from access_ctrl import check_access\n\ndef test_admin():\n    assert check_access("admin", "private", False, False) is True\n\ndef test_public_published():\n    assert check_access("user", "public", False, True) is True\n\ndef test_public_unpublished():\n    assert check_access("user", "public", False, False) is False\n\ndef test_private_owner():\n    assert check_access("user", "private", True, False) is True\n\ndef test_private_non_owner():\n    assert check_access("user", "private", False, False) is False\n',
        '`check_access("user", "public", False, False)` returns True for unpublished public resources.\n\nMissing `is_published` check and resource type logic.\n\nRun: `python -m pytest tests/test_access_ctrl.py`'),

    # off-by-one (harder)
    make_task("bugfix_268", "off_by_one", "medium", "pagination",
        'def paginate(items, page, per_page):\n    """Return items for given page (1-indexed)."""\n    start = page * per_page\n    end = start + per_page\n    return items[start:end]\n',
        'def paginate(items, page, per_page):\n    """Return items for given page (1-indexed)."""\n    if page < 1 or per_page < 1:\n        return []\n    start = (page - 1) * per_page\n    end = start + per_page\n    return items[start:end]\n',
        'from pagination import paginate\n\ndef test_first_page():\n    assert paginate([1,2,3,4,5], 1, 2) == [1, 2]\n\ndef test_second_page():\n    assert paginate([1,2,3,4,5], 2, 2) == [3, 4]\n\ndef test_last_partial():\n    assert paginate([1,2,3,4,5], 3, 2) == [5]\n\ndef test_out_of_range():\n    assert paginate([1,2,3], 5, 2) == []\n',
        '`paginate([1,2,3,4,5], 1, 2)` returns `[3, 4]` instead of `[1, 2]`.\n\nPage is 1-indexed but code uses 0-indexed calculation.\n\nRun: `python -m pytest tests/test_pagination.py`'),

    # type conversion (harder)
    make_task("bugfix_269", "type_conversion", "medium", "json_util",
        'import json\n\ndef deep_merge(base, override):\n    """Deep merge two dicts."""\n    result = base.copy()\n    for key, val in override.items():\n        if key in result and isinstance(result[key], dict) and isinstance(val, dict):\n            result[key] = deep_merge(result[key], val)\n        else:\n            result[key] = val\n    return result\n\ndef load_json_file(path):\n    """Load JSON file and return dict."""\n    with open(path) as f:\n        return json.load(f)\n',
        'import json\n\ndef deep_merge(base, override):\n    """Deep merge two dicts (non-destructive)."""\n    result = base.copy()\n    for key, val in override.items():\n        if key in result and isinstance(result[key], dict) and isinstance(val, dict):\n            result[key] = deep_merge(result[key], val)\n        else:\n            result[key] = val\n    return result\n\ndef load_json_file(path):\n    """Load JSON file and return dict, return empty dict on error."""\n    try:\n        with open(path) as f:\n            return json.load(f)\n    except (FileNotFoundError, json.JSONDecodeError):\n        return {}\n',
        'import tempfile, os, json\nfrom json_util import deep_merge, load_json_file\n\ndef test_merge():\n    assert deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}\n\ndef test_nested():\n    assert deep_merge({"a": {"x": 1}}, {"a": {"y": 2}}) == {"a": {"x": 1, "y": 2}}\n\ndef test_load_missing():\n    assert load_json_file("/nonexistent.json") == {}\n\ndef test_load_invalid():\n    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:\n        f.write("not json")\n        f.flush()\n        assert load_json_file(f.name) == {}\n        os.unlink(f.name)\n',
        '`load_json_file("/nonexistent.json")` raises FileNotFoundError instead of returning {}.\n\nNo error handling for missing or invalid files.\n\nRun: `python -m pytest tests/test_json_util.py`'),
]

TASKS.extend(EXTRA_TASKS)


def build_task_dir(root: Path, task: dict):
    """Create task directory structure."""
    task_dir = root / task["task_id"]
    task_dir.mkdir(parents=True, exist_ok=True)

    # repo/
    repo_dir = task_dir / "repo"
    repo_dir.mkdir(exist_ok=True)
    (repo_dir / task["target_file"]).write_text(task["buggy_code"], encoding="utf-8")

    # tests/
    tests_dir = repo_dir / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    test_filename = f"test_{task['module']}.py"
    (tests_dir / test_filename).write_text(task["test_code"], encoding="utf-8")

    # issue.md
    (task_dir / "issue.md").write_text(task["issue"], encoding="utf-8")

    # metadata.json
    test_cmd = f"python -m pytest tests/{test_filename}"
    meta = {
        "task_id": task["task_id"],
        "bug_type": task["bug_type"],
        "language": "python",
        "test_command": test_cmd,
        "target_files": [task["target_file"]],
        "difficulty": task["difficulty"],
        "timeout": 30,
        "scripted_fix": task["scripted_fix"],
    }
    (task_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def main():
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"

    print(f"Building {len(TASKS)} tasks...")
    for task in TASKS:
        build_task_dir(tasks_root, task)
        print(f"  {task['task_id']}: {task['bug_type']} ({task['difficulty']})")

    # Generate split file
    splits_dir = root / "outputs" / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    new100_path = splits_dir / "new100_heldout_tasks.txt"
    new100_path.write_text("\n".join(t["task_id"] for t in TASKS) + "\n", encoding="utf-8")
    print(f"\nSplit file: {new100_path}")

    # Stats
    bug_types = {}
    difficulties = {}
    for t in TASKS:
        bug_types[t["bug_type"]] = bug_types.get(t["bug_type"], 0) + 1
        difficulties[t["difficulty"]] = difficulties.get(t["difficulty"], 0) + 1

    print(f"\nTotal: {len(TASKS)} tasks")
    print(f"Bug types: {bug_types}")
    print(f"Difficulties: {difficulties}")


if __name__ == "__main__":
    main()
