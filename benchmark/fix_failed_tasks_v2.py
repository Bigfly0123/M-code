"""Fix the remaining failed tasks with proper bugs."""
from __future__ import annotations

import json
from pathlib import Path

FIXED_TASKS = {
    # bugfix_062: 需要真正的bug - 默认排序是case-sensitive
    "bugfix_062": {
        "buggy_code": '''def sort_strings(strings):
    """Sort strings case-insensitively."""
    return sorted(strings, key=str.upper)
''',
        "fixed_code": '''def sort_strings(strings):
    """Sort strings case-insensitively."""
    return sorted(strings, key=str.lower)
''',
        "test_code": '''from sort_case import sort_strings


def test_case_sort():
    result = sort_strings(["banana", "apple", "Cherry"])
    assert result == ["apple", "banana", "Cherry"]


def test_all_lower():
    result = sort_strings(["c", "a", "b"])
    assert result == ["a", "b", "c"]
''',
        "scripted_fix": {"path": "sort_case.py", "old": "return sorted(strings, key=str.upper)", "new": "return sorted(strings, key=str.lower)"},
    },
    # bugfix_063: 运算符优先级bug
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
    # bugfix_066: bare except
    "bugfix_066": {
        "buggy_code": '''def safe_divide(a, b):
    """Divide a by b, return None on error."""
    try:
        return a / b
    except:
        return None
''',
        "fixed_code": '''def safe_divide(a, b):
    """Divide a by b, return None on error."""
    try:
        return a / b
    except ZeroDivisionError:
        return None
''',
        "test_code": '''from safe_div import safe_divide


def test_normal():
    assert safe_divide(10, 2) == 5.0


def test_zero():
    assert safe_divide(10, 0) is None


def test_bare_except():
    import inspect
    source = inspect.getsource(safe_divide)
    assert "except:" not in source or "except ZeroDivisionError" in source
''',
        "scripted_fix": {"path": "safe_div.py", "old": "    except:", "new": "    except ZeroDivisionError:"},
    },
    # bugfix_068: 文件未关闭
    "bugfix_068": {
        "buggy_code": '''def read_file(path):
    """Read file content."""
    f = open(path)
    content = f.read()
    return content
''',
        "fixed_code": '''def read_file(path):
    """Read file content."""
    with open(path) as f:
        return f.read()
''',
        "test_code": '''import tempfile
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


def test_uses_context_manager():
    import inspect
    source = inspect.getsource(read_file)
    assert "with open" in source
''',
        "scripted_fix": {"path": "file_reader.py", "old": "def read_file(path):\n    \"\"\"Read file content.\"\"\"\n    f = open(path)\n    content = f.read()\n    return content", "new": "def read_file(path):\n    \"\"\"Read file content.\"\"\"\n    with open(path) as f:\n        return f.read()"},
    },
    # bugfix_071: 负索引处理
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
    # bugfix_074: 对称差集顺序
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
        "test_code": '''from sym_diff import symmetric_difference


def test_basic():
    result = symmetric_difference([1, 2, 3], [3, 4, 5])
    assert result == [1, 2, 4, 5]


def test_order():
    result = symmetric_difference([3, 1, 2], [2, 3, 4])
    assert result == [1, 4]
''',
    },
    # bugfix_081: CSV解析
    "bugfix_081": {
        "buggy_code": '''def parse_csv_line(line):
    """Parse a CSV line into fields."""
    return line.split(",")


def parse_csv_to_dicts(header_line, data_lines):
    """Parse CSV lines into list of dicts."""
    headers = header_line.split(",")
    result = []
    for line in data_lines:
        values = line.split(",")
        result.append(dict(zip(headers, values)))
    return result
''',
        "fixed_code": '''import csv
import io


def parse_csv_line(line):
    """Parse a CSV line into fields."""
    reader = csv.reader(io.StringIO(line))
    return next(reader)


def parse_csv_to_dicts(header_line, data_lines):
    """Parse CSV lines into list of dicts."""
    reader = csv.reader(io.StringIO(header_line + "\\n" + "\\n".join(data_lines)))
    headers = next(reader)
    result = []
    for row in reader:
        result.append(dict(zip(headers, row)))
    return result
''',
        "test_code": '''from csv_parse import parse_csv_line, parse_csv_to_dicts


def test_simple():
    assert parse_csv_line("a,b,c") == ["a", "b", "c"]


def test_quoted():
    assert parse_csv_line('"hello, world",b,c') == ["hello, world", "b", "c"]


def test_to_dicts():
    result = parse_csv_to_dicts("name,age", ["Alice,30", "Bob,25"])
    assert result == [{"name": "Alice", "age": "30"}, {"name": "Bob", "age": "25"}]
''',
        "scripted_fix": {"path": "csv_parse.py", "old": "def parse_csv_line(line):\n    \"\"\"Parse a CSV line into fields.\"\"\"\n    return line.split(\",\")", "new": "import csv\nimport io\n\n\ndef parse_csv_line(line):\n    \"\"\"Parse a CSV line into fields.\"\"\"\n    reader = csv.reader(io.StringIO(line))\n    return next(reader)"},
    },
    # bugfix_084: URL解析
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


def test_with_port():
    assert get_domain("https://example.com:8080/path") == "example.com:8080"
''',
        "scripted_fix": {"path": "url_parse.py", "old": "def get_domain(url):\n    \"\"\"Extract domain from URL.\"\"\"\n    if \"//\" in url:\n        return url.split(\"//\")[1].split(\"/\")[0]\n    return url.split(\"/\")[0]", "new": "from urllib.parse import urlparse\n\n\ndef get_domain(url):\n    \"\"\"Extract domain from URL.\"\"\"\n    parsed = urlparse(url)\n    return parsed.netloc"},
    },
    # bugfix_087: 温度转换精度
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
    assert result == 98.6


def test_negative():
    assert celsius_to_fahrenheit(-40) == -40.0
''',
        "scripted_fix": {"path": "temp_conv.py", "old": "    return c * 9 / 5 + 32", "new": "    return round(c * 9 / 5 + 32, 2)"},
    },
    # bugfix_100: 计数器nonlocal问题
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


def test_with_step():
    c = create_counter()
    assert c(5) == 5
    assert c(3) == 8
''',
        "scripted_fix": {"path": "counter.py", "old": "def create_counter(start=0):\n    \"\"\"Create a counter that increments.\"\"\"\n    count = start\n    def increment(step=1):\n        nonlocal count\n        count += step\n        return count\n    return increment", "new": "def create_counter(start=0):\n    \"\"\"Create a counter that increments.\"\"\"\n    count = [start]\n    def increment(step=1):\n        count[0] += step\n        return count[0]\n    return increment"},
    },
}


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    tasks_root = root / "benchmark" / "tasks"

    fixed_count = 0
    for task_id, fixes in FIXED_TASKS.items():
        task_dir = tasks_root / task_id
        if not task_dir.exists():
            print(f"Skipping {task_id}: directory not found")
            continue

        repo_dir = task_dir / "repo"
        module_files = list(repo_dir.glob("*.py"))
        if not module_files:
            print(f"Skipping {task_id}: no module file found")
            continue

        module_file = module_files[0]
        module_name = module_file.stem

        # Update buggy_code if provided
        if "buggy_code" in fixes:
            module_file.write_text(fixes["buggy_code"], encoding="utf-8")

        # Update test_code if provided
        if "test_code" in fixes:
            test_dir = repo_dir / "tests"
            test_file = test_dir / f"test_{module_name}.py"
            test_file.write_text(fixes["test_code"], encoding="utf-8")

        # Update scripted_fix if provided
        if "scripted_fix" in fixes:
            meta_path = task_dir / "metadata.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["scripted_fix"] = fixes["scripted_fix"]
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        fixed_count += 1
        print(f"Fixed {task_id}")

    print(f"\nTotal fixed: {fixed_count}")


if __name__ == "__main__":
    main()
