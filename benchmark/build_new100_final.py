"""Generate final batch of new100 tasks (bugfix_301-350)."""
import json
from pathlib import Path

TASKS = []

def add(tid, bug_type, diff, module, buggy, fixed, tests, issue):
    TASKS.append({
        "task_id": tid, "bug_type": bug_type, "difficulty": diff, "module": module,
        "buggy_code": buggy, "fixed_code": fixed, "test_code": tests, "issue": issue,
        "target_file": f"{module}.py",
    })

# === regex (5 more) ===
add("bugfix_301", "regex", "medium", "password_check",
    'import re\n\ndef is_strong_password(pw):\n    """Check password has upper, lower, digit, 8+ chars."""\n    return len(pw) >= 8 and bool(re.search(r"[A-Za-z0-9]", pw))\n',
    'import re\n\ndef is_strong_password(pw):\n    """Check password has upper, lower, digit, 8+ chars."""\n    return (len(pw) >= 8 and bool(re.search(r"[A-Z]", pw))\n            and bool(re.search(r"[a-z]", pw)) and bool(re.search(r"[0-9]", pw)))\n',
    'from password_check import is_strong_password\n\ndef test_strong():\n    assert is_strong_password("Abc12345") is True\n\ndef test_no_upper():\n    assert is_strong_password("abc12345") is False\n\ndef test_no_digit():\n    assert is_strong_password("Abcdefgh") is False\n\ndef test_short():\n    assert is_strong_password("Ab1") is False\n',
    '`is_strong_password("abc12345")` returns True (no uppercase required).\n\nRun: `python -m pytest tests/test_password_check.py`')

add("bugfix_302", "regex", "medium", "log_parser",
    'import re\n\ndef parse_log_line(line):\n    """Parse log line: [LEVEL] message."""\n    match = re.match(r"\\[(\\w+)\\] (.*)", line)\n    if match:\n        return {"level": match.group(1), "message": match.group(2)}\n    return None\n',
    'import re\n\ndef parse_log_line(line):\n    """Parse log line: [YYYY-MM-DD HH:MM:SS] [LEVEL] message."""\n    match = re.match(r"(?:\\[.*?\\] )?\\[(\\w+)\\] (.*)", line)\n    if match:\n        return {"level": match.group(1), "message": match.group(2)}\n    return None\n',
    'from log_parser import parse_log_line\n\ndef test_basic():\n    r = parse_log_line("[INFO] Server started")\n    assert r == {"level": "INFO", "message": "Server started"}\n\ndef test_with_timestamp():\n    r = parse_log_line("[2024-01-01 12:00:00] [ERROR] Connection failed")\n    assert r["level"] == "ERROR"\n    assert r["message"] == "Connection failed"\n\ndef test_invalid():\n    assert parse_log_line("no brackets") is None\n',
    '`parse_log_line("[2024-01-01 12:00:00] [ERROR] msg")` returns None.\n\nPattern doesn\'t handle optional timestamp prefix.\n\nRun: `python -m pytest tests/test_log_parser.py`')

add("bugfix_303", "regex", "easy", "file_ext",
    'import re\n\ndef get_extension(filename):\n    """Get file extension."""\n    match = re.search(r"\\.(.+)$", filename)\n    return match.group(1) if match else None\n',
    'import re\n\ndef get_extension(filename):\n    """Get file extension (lowercase, without dot)."""\n    match = re.search(r"\\.([^.]+)$", filename)\n    return match.group(1).lower() if match else None\n',
    'from file_ext import get_extension\n\ndef test_basic():\n    assert get_extension("file.txt") == "txt"\n\ndef test_multiple_dots():\n    assert get_extension("archive.tar.gz") == "gz"\n\ndef test_no_ext():\n    assert get_extension("Makefile") is None\n\ndef test_uppercase():\n    assert get_extension("FILE.PDF") == "pdf"\n',
    '`get_extension("FILE.PDF")` returns "PDF" instead of "pdf".\n\nRun: `python -m pytest tests/test_file_ext.py`')

add("bugfix_304", "regex", "medium", "markdown_util",
    'import re\n\ndef extract_headers(md_text):\n    """Extract markdown headers."""\n    return re.findall(r"#+ (.*)", md_text)\n',
    'import re\n\ndef extract_headers(md_text):\n    """Extract markdown headers (lines starting with #)."""\n    return [m.group(2) for m in re.finditer(r"^(#{1,6}) (.+)$", md_text, re.MULTILINE)]\n',
    'from markdown_util import extract_headers\n\ndef test_basic():\n    assert extract_headers("# Hello\\n## World") == ["Hello", "World"]\n\ndef test_in_text():\n    assert extract_headers("text # not header\\n# Real") == ["Real"]\n\ndef test_levels():\n    assert extract_headers("# H1\\n### H3\\n###### H6") == ["H1", "H3", "H6"]\n',
    '`extract_headers("text # not header")` incorrectly picks up inline #.\n\nShould only match # at start of line.\n\nRun: `python -m pytest tests/test_markdown_util.py`')

add("bugfix_305", "regex", "medium", "number_util",
    'import re\n\ndef extract_numbers(text):\n    """Extract all numbers from text."""\n    return [int(x) for x in re.findall(r"\\d+", text)]\n',
    'import re\n\ndef extract_numbers(text):\n    """Extract all numbers (int and float) from text."""\n    return [float(x) if "." in x else int(x) for x in re.findall(r"-?\\d+\\.?\\d*", text)]\n',
    'from number_util import extract_numbers\n\ndef test_ints():\n    assert extract_numbers("a1b2c3") == [1, 2, 3]\n\ndef test_floats():\n    assert extract_numbers("pi=3.14 e=2.72") == [3.14, 2.72]\n\ndef test_negative():\n    assert extract_numbers("temp=-5.2") == [-5.2]\n\ndef test_mixed():\n    assert extract_numbers("x=1 y=2.5 z=-3") == [1, 2.5, -3]\n',
    '`extract_numbers("pi=3.14")` returns [3, 14] instead of [3.14].\n\nDoes not handle decimal numbers.\n\nRun: `python -m pytest tests/test_number_util.py`')

# === date_time (5 more) ===
add("bugfix_306", "date_time", "medium", "countdown_util",
    'from datetime import datetime, timedelta\n\ndef time_until(target_str, now_str):\n    """Return hours until target time."""\n    target = datetime.strptime(target_str, "%H:%M")\n    now = datetime.strptime(now_str, "%H:%M")\n    diff = target - now\n    return diff.total_seconds() / 3600\n',
    'from datetime import datetime, timedelta\n\ndef time_until(target_str, now_str):\n    """Return hours until target time (handles next day)."""\n    target = datetime.strptime(target_str, "%H:%M")\n    now = datetime.strptime(now_str, "%H:%M")\n    diff = (target - now).total_seconds()\n    if diff < 0:\n        diff += 86400  # next day\n    return diff / 3600\n',
    'from countdown_util import time_until\n\ndef test_future():\n    assert time_until("15:00", "12:00") == 3.0\n\ndef test_past():\n    assert time_until("09:00", "23:00") == 10.0\n\ndef test_same():\n    assert time_until("12:00", "12:00") == 24.0\n',
    '`time_until("09:00", "23:00")` returns -14.0 instead of 10.0.\n\nDoes not handle crossing midnight.\n\nRun: `python -m pytest tests/test_countdown_util.py`')

add("bugfix_307", "date_time", "easy", "month_util",
    'def days_in_month(month, year=2024):\n    """Return number of days in given month."""\n    days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\n    return days[month]\n',
    'def days_in_month(month, year=2024):\n    """Return number of days in given month."""\n    days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]\n    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):\n        return 29\n    return days[month]\n',
    'from month_util import days_in_month\n\ndef test_jan():\n    assert days_in_month(1) == 31\n\ndef test_feb():\n    assert days_in_month(2) == 28\n\ndef test_leap():\n    assert days_in_month(2, 2024) == 29\n\ndef test_not_leap():\n    assert days_in_month(2, 1900) == 28\n',
    '`days_in_month(2, 2024)` returns 28 instead of 29 (2024 is a leap year).\n\nRun: `python -m pytest tests/test_month_util.py`')

add("bugfix_308", "date_time", "medium", "schedule_util",
    'def merge_intervals(intervals):\n    """Merge overlapping time intervals."""\n    intervals.sort()\n    result = [intervals[0]]\n    for start, end in intervals[1:]:\n        if start <= result[-1][1]:\n            result[-1][1] = end\n        else:\n            result.append([start, end])\n    return result\n',
    'def merge_intervals(intervals):\n    """Merge overlapping time intervals."""\n    if not intervals:\n        return []\n    intervals.sort()\n    result = [list(intervals[0])]\n    for start, end in intervals[1:]:\n        if start <= result[-1][1]:\n            result[-1][1] = max(result[-1][1], end)\n        else:\n            result.append([start, end])\n    return result\n',
    'from schedule_util import merge_intervals\n\ndef test_basic():\n    assert merge_intervals([[1,3],[2,4],[5,6]]) == [[1,4],[5,6]]\n\ndef test_contained():\n    assert merge_intervals([[1,5],[2,3]]) == [[1,5]]\n\ndef test_empty():\n    assert merge_intervals([]) == []\n',
    '`merge_intervals([[1,5],[2,3]])` returns [[1,3]] instead of [[1,5]].\n\nContained interval shrinks the merge.\n\nRun: `python -m pytest tests/test_schedule_util.py`')

add("bugfix_309", "date_time", "easy", "timestamp_util",
    'import time\n\ndef elapsed_str(seconds):\n    """Format seconds as Xm Ys."""\n    m = int(seconds) // 60\n    s = int(seconds) % 60\n    return f"{m}m {s}s"\n',
    'def elapsed_str(seconds):\n    """Format seconds as Xh Ym Zs."""\n    h = int(seconds) // 3600\n    m = (int(seconds) % 3600) // 60\n    s = int(seconds) % 60\n    if h > 0:\n        return f"{h}h {m}m {s}s"\n    return f"{m}m {s}s"\n',
    'from timestamp_util import elapsed_str\n\ndef test_short():\n    assert elapsed_str(65) == "1m 5s"\n\ndef test_exact_min():\n    assert elapsed_str(120) == "2m 0s"\n\ndef test_hours():\n    assert elapsed_str(3661) == "1h 1m 1s"\n',
    '`elapsed_str(3661)` returns "61m 1s" instead of "1h 1m 1s".\n\nDoes not handle hours.\n\nRun: `python -m pytest tests/test_timestamp_util.py`')

add("bugfix_310", "date_time", "medium", "biz_day_util",
    'from datetime import date, timedelta\n\ndef add_business_days(start, days):\n    """Add business days to a date."""\n    current = start\n    for _ in range(days):\n        current += timedelta(days=1)\n    return current\n',
    'from datetime import date, timedelta\n\ndef add_business_days(start, days):\n    """Add business days to a date."""\n    current = start\n    added = 0\n    while added < days:\n        current += timedelta(days=1)\n        if current.weekday() < 5:\n            added += 1\n    return current\n',
    'from datetime import date\nfrom biz_day_util import add_business_days\n\ndef test_basic():\n    result = add_business_days(date(2024, 1, 1), 5)\n    assert result == date(2024, 1, 8)\n\ndef test_cross_weekend():\n    result = add_business_days(date(2024, 1, 5), 1)  # Friday\n    assert result == date(2024, 1, 8)  # Monday\n',
    '`add_business_days(Friday, 1)` returns Saturday instead of Monday.\n\nDoes not skip weekends.\n\nRun: `python -m pytest tests/test_biz_day_util.py`')

# === nested_condition (5 more) ===
add("bugfix_311", "nested_condition", "medium", "loan_calc",
    'def monthly_payment(principal, rate, years):\n    """Calculate monthly loan payment."""\n    if rate == 0:\n        return principal / (years * 12)\n    monthly_rate = rate / 12\n    n = years * 12\n    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -n)\n\ndef total_interest(principal, rate, years):\n    """Calculate total interest paid."""\n    payment = monthly_payment(principal, rate, years)\n    return payment * years * 12 - principal\n',
    'def monthly_payment(principal, rate, years):\n    """Calculate monthly loan payment."""\n    if principal <= 0 or years <= 0:\n        return 0\n    if rate == 0:\n        return principal / (years * 12)\n    monthly_rate = rate / 12\n    n = years * 12\n    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -n)\n\ndef total_interest(principal, rate, years):\n    """Calculate total interest paid."""\n    payment = monthly_payment(principal, rate, years)\n    return payment * years * 12 - principal\n',
    'from loan_calc import monthly_payment, total_interest\n\ndef test_basic():\n    p = monthly_payment(100000, 0.05, 30)\n    assert 500 < p < 600\n\ndef test_zero_rate():\n    assert monthly_payment(120000, 0, 10) == 1000\n\ndef test_zero_principal():\n    assert monthly_payment(0, 0.05, 30) == 0\n\ndef test_negative():\n    assert monthly_payment(-100, 0.05, 30) == 0\n',
    '`monthly_payment(0, 0.05, 30)` causes division by zero error.\n\nNo validation for zero/negative principal.\n\nRun: `python -m pytest tests/test_loan_calc.py`')

add("bugfix_312", "nested_condition", "medium", "signal_util",
    'def classify_signal(value, low_thresh, high_thresh):\n    """Classify signal as LOW, NORMAL, or HIGH."""\n    if value < low_thresh:\n        return "LOW"\n    if value > high_thresh:\n        return "HIGH"\n    return "NORMAL"\n\ndef is_alert(value, low_thresh, high_thresh):\n    """Check if signal needs alert."""\n    return classify_signal(value, low_thresh, high_thresh) != "NORMAL"\n',
    'def classify_signal(value, low_thresh, high_thresh):\n    """Classify signal as LOW, NORMAL, or HIGH."""\n    if value <= low_thresh:\n        return "LOW"\n    if value >= high_thresh:\n        return "HIGH"\n    return "NORMAL"\n\ndef is_alert(value, low_thresh, high_thresh):\n    """Check if signal needs alert."""\n    return classify_signal(value, low_thresh, high_thresh) != "NORMAL"\n',
    'from signal_util import classify_signal, is_alert\n\ndef test_normal():\n    assert classify_signal(50, 10, 90) == "NORMAL"\n\ndef test_at_low():\n    assert classify_signal(10, 10, 90) == "LOW"\n\ndef test_at_high():\n    assert classify_signal(90, 10, 90) == "HIGH"\n\ndef test_alert():\n    assert is_alert(5, 10, 90) is True\n',
    '`classify_signal(10, 10, 90)` returns "NORMAL" instead of "LOW".\n\nBoundary values should trigger LOW/HIGH.\n\nRun: `python -m pytest tests/test_signal_util.py`')

add("bugfix_313", "nested_condition", "hard", "game_state",
    'def check_winner(board):\n    """Check tic-tac-toe winner. Board is 3x3 list of X/O/None."""\n    for row in board:\n        if row[0] == row[1] == row[2] and row[0]:\n            return row[0]\n    for col in range(3):\n        if board[0][col] == board[1][col] == board[2][col] and board[0][col]:\n            return board[0][col]\n    return None\n',
    'def check_winner(board):\n    """Check tic-tac-toe winner. Board is 3x3 list of X/O/None."""\n    for row in board:\n        if row[0] == row[1] == row[2] and row[0]:\n            return row[0]\n    for col in range(3):\n        if board[0][col] == board[1][col] == board[2][col] and board[0][col]:\n            return board[0][col]\n    if board[0][0] == board[1][1] == board[2][2] and board[0][0]:\n        return board[0][0]\n    if board[0][2] == board[1][1] == board[2][0] and board[0][2]:\n        return board[0][2]\n    return None\n',
    'from game_state import check_winner\n\ndef test_row():\n    assert check_winner([["X","X","X"],["","",""],["","",""]]) == "X"\n\ndef test_col():\n    assert check_winner([["O","",""],["O","",""],["O","",""]]) == "O"\n\ndef test_diag():\n    assert check_winner([["X","",""],["","X",""],["","","X"]]) == "X"\n\ndef test_anti_diag():\n    assert check_winner([["","","X"],["","X",""],["X","",""]]) == "X"\n\ndef test_none():\n    assert check_winner([["X","O","X"],["O","X","O"],["O","X","O"]]) is None\n',
    '`check_winner` misses diagonal wins.\n`[["X","",""],["","X",""],["","","X"]]` returns None.\n\nRun: `python -m pytest tests/test_game_state.py`')

add("bugfix_314", "nested_condition", "medium", "water_bill",
    'def calculate_bill(gallons):\n    """Calculate water bill."""\n    if gallons <= 1000:\n        return 5.0\n    if gallons <= 5000:\n        return 5.0 + (gallons - 1000) * 0.005\n    return 5.0 + 4000 * 0.005 + (gallons - 5000) * 0.003\n',
    'def calculate_bill(gallons):\n    """Calculate water bill."""\n    if gallons < 0:\n        return 0\n    if gallons <= 1000:\n        return 5.0\n    if gallons <= 5000:\n        return 5.0 + (gallons - 1000) * 0.005\n    return 5.0 + 4000 * 0.005 + (gallons - 5000) * 0.003\n',
    'from water_bill import calculate_bill\n\ndef test_min():\n    assert calculate_bill(500) == 5.0\n\ndef test_mid():\n    assert calculate_bill(3000) == 15.0\n\ndef test_high():\n    assert calculate_bill(10000) == 40.0\n\ndef test_negative():\n    assert calculate_bill(-100) == 0\n',
    '`calculate_bill(-100)` returns negative value.\n\nNo validation for negative input.\n\nRun: `python -m pytest tests/test_water_bill.py`')

add("bugfix_315", "nested_condition", "medium", "parking_fee",
    'def parking_fee(hours):\n    """Calculate parking fee: $5/hr first 3, $3/hr after."""\n    if hours <= 3:\n        return hours * 5\n    return 15 + (hours - 3) * 3\n',
    'def parking_fee(hours):\n    """Calculate parking fee: $5/hr first 3, $3/hr after, max $50."""\n    if hours <= 0:\n        return 0\n    if hours <= 3:\n        fee = hours * 5\n    else:\n        fee = 15 + (hours - 3) * 3\n    return min(fee, 50.0)\n',
    'from parking_fee import parking_fee\n\ndef test_short():\n    assert parking_fee(2) == 10\n\ndef test_long():\n    assert parking_fee(5) == 21\n\ndef test_max():\n    assert parking_fee(20) == 50.0\n\ndef test_zero():\n    assert parking_fee(0) == 0\n',
    '`parking_fee(20)` returns 66 instead of 50 (no maximum cap).\n\nRun: `python -m pytest tests/test_parking_fee.py`')

# === type_conversion (5 more) ===
add("bugfix_316", "type_conversion", "easy", "bool_util",
    'def to_bool(value):\n    """Convert value to boolean."""\n    return bool(value)\n',
    'def to_bool(value):\n    """Convert value to boolean with string support."""\n    if isinstance(value, str):\n        return value.lower() in ("true", "yes", "1", "on")\n    return bool(value)\n',
    'from bool_util import to_bool\n\ndef test_true():\n    assert to_bool(True) is True\n\ndef test_string_true():\n    assert to_bool("true") is True\n    assert to_bool("yes") is True\n\ndef test_string_false():\n    assert to_bool("false") is False\n    assert to_bool("no") is False\n\ndef test_zero():\n    assert to_bool(0) is False\n',
    '`to_bool("false")` returns True (non-empty string is truthy).\n\nRun: `python -m pytest tests/test_bool_util.py`')

add("bugfix_317", "type_conversion", "medium", "serialize_util",
    'def to_json(obj):\n    """Serialize object to JSON string."""\n    import json\n    return json.dumps(obj)\n',
    'def to_json(obj):\n    """Serialize object to JSON string, handle special types."""\n    import json\n    from datetime import datetime, date\n    def default(o):\n        if isinstance(o, (datetime, date)):\n            return o.isoformat()\n        if isinstance(o, set):\n            return list(o)\n        raise TypeError(f"Object of type {type(o)} is not JSON serializable")\n    return json.dumps(obj, default=default)\n',
    'from datetime import datetime\nfrom serialize_util import to_json\nimport json\n\ndef test_dict():\n    result = to_json({"a": 1})\n    assert json.loads(result) == {"a": 1}\n\ndef test_datetime():\n    d = datetime(2024, 1, 1, 12, 0)\n    result = json.loads(to_json({"ts": d}))\n    assert "2024-01-01" in result["ts"]\n\ndef test_set():\n    result = json.loads(to_json({"s": {1, 2, 3}}))\n    assert sorted(result["s"]) == [1, 2, 3]\n',
    '`to_json({"ts": datetime.now()})` raises TypeError.\n\nCannot serialize datetime objects.\n\nRun: `python -m pytest tests/test_serialize_util.py`')

add("bugfix_318", "type_conversion", "medium", "range_parse",
    'def parse_range(s):\n    """Parse range string like "1-5" into list."""\n    parts = s.split("-")\n    return list(range(int(parts[0]), int(parts[1]) + 1))\n',
    'def parse_range(s):\n    """Parse range string like "1-5" or "1,3,5" into list."""\n    result = []\n    for part in s.split(","):\n        part = part.strip()\n        if "-" in part:\n            start, end = part.split("-", 1)\n            result.extend(range(int(start), int(end) + 1))\n        else:\n            result.append(int(part))\n    return result\n',
    'from range_parse import parse_range\n\ndef test_simple():\n    assert parse_range("1-5") == [1, 2, 3, 4, 5]\n\ndef test_list():\n    assert parse_range("1,3,5") == [1, 3, 5]\n\ndef test_mixed():\n    assert parse_range("1-3,7,9-10") == [1, 2, 3, 7, 9, 10]\n',
    '`parse_range("1,3,5")` raises ValueError.\n\nOnly supports "start-end" format, not comma-separated.\n\nRun: `python -m pytest tests/test_range_parse.py`')

add("bugfix_319", "type_conversion", "easy", "hex_util",
    'def rgb_to_hex(r, g, b):\n    """Convert RGB to hex color string."""\n    return f"#{r}{g}{b}"\n',
    'def rgb_to_hex(r, g, b):\n    """Convert RGB to hex color string."""\n    return f"#{r:02x}{g:02x}{b:02x}"\n',
    'from hex_util import rgb_to_hex\n\ndef test_basic():\n    assert rgb_to_hex(255, 128, 0) == "#ff8000"\n\ndef test_black():\n    assert rgb_to_hex(0, 0, 0) == "#000000"\n\ndef test_white():\n    assert rgb_to_hex(255, 255, 255) == "#ffffff"\n',
    '`rgb_to_hex(255, 128, 0)` returns "#2551280" instead of "#ff8000".\n\nMissing hex formatting.\n\nRun: `python -m pytest tests/test_hex_util.py`')

add("bugfix_320", "type_conversion", "medium", "num_util",
    'def ordinal(n):\n    """Return ordinal string for number."""\n    if n % 10 == 1:\n        return f"{n}st"\n    if n % 10 == 2:\n        return f"{n}nd"\n    if n % 10 == 3:\n        return f"{n}rd"\n    return f"{n}th"\n',
    'def ordinal(n):\n    """Return ordinal string for number."""\n    if 11 <= (n % 100) <= 13:\n        return f"{n}th"\n    if n % 10 == 1:\n        return f"{n}st"\n    if n % 10 == 2:\n        return f"{n}nd"\n    if n % 10 == 3:\n        return f"{n}rd"\n    return f"{n}th"\n',
    'from num_util import ordinal\n\ndef test_basic():\n    assert ordinal(1) == "1st"\n    assert ordinal(2) == "2nd"\n    assert ordinal(3) == "3rd"\n    assert ordinal(4) == "4th"\n\ndef test_teens():\n    assert ordinal(11) == "11th"\n    assert ordinal(12) == "12th"\n    assert ordinal(13) == "13th"\n\ndef test_21():\n    assert ordinal(21) == "21st"\n',
    '`ordinal(11)` returns "11st" instead of "11th".\n\nSpecial case for 11-13 not handled.\n\nRun: `python -m pytest tests/test_num_util.py`')

# === list_mutation / off_by_one / exception (remaining) ===
add("bugfix_321", "list_mutation", "medium", "merge_util",
    'def merge_sorted(a, b):\n    """Merge two sorted lists."""\n    return sorted(a + b)\n',
    'def merge_sorted(a, b):\n    """Merge two sorted lists efficiently."""\n    result = []\n    i = j = 0\n    while i < len(a) and j < len(b):\n        if a[i] <= b[j]:\n            result.append(a[i])\n            i += 1\n        else:\n            result.append(b[j])\n            j += 1\n    result.extend(a[i:])\n    result.extend(b[j:])\n    return result\n',
    'from merge_util import merge_sorted\n\ndef test_basic():\n    assert merge_sorted([1,3,5], [2,4,6]) == [1,2,3,4,5,6]\n\ndef test_empty():\n    assert merge_sorted([], [1,2]) == [1,2]\n\ndef test_dupes():\n    assert merge_sorted([1,2], [2,3]) == [1,2,2,3]\n\ndef test_large():\n    a = list(range(0, 1000, 2))\n    b = list(range(1, 1000, 2))\n    result = merge_sorted(a, b)\n    assert result == list(range(1000))\n',
    '`merge_sorted` uses `sorted()` which is O(n log n).\nShould use O(n) merge for already-sorted inputs.\n\nRun: `python -m pytest tests/test_merge_util.py`')

add("bugfix_322", "off_by_one", "medium", "window_util",
    'def sliding_window(lst, size):\n    """Generate sliding windows of given size."""\n    return [lst[i:i+size] for i in range(len(lst) - size + 1)]\n\ndef moving_average(data, window):\n    """Calculate moving average."""\n    return [sum(w)/len(w) for w in sliding_window(data, window)]\n',
    'def sliding_window(lst, size):\n    """Generate sliding windows of given size."""\n    if size <= 0 or size > len(lst):\n        return []\n    return [lst[i:i+size] for i in range(len(lst) - size + 1)]\n\ndef moving_average(data, window):\n    """Calculate moving average."""\n    if window <= 0:\n        return []\n    return [sum(w)/len(w) for w in sliding_window(data, window)]\n',
    'from window_util import sliding_window, moving_average\n\ndef test_basic():\n    assert sliding_window([1,2,3,4], 2) == [[1,2],[2,3],[3,4]]\n\ndef test_too_large():\n    assert sliding_window([1,2], 5) == []\n\ndef test_zero():\n    assert sliding_window([1,2,3], 0) == []\n\ndef test_avg():\n    assert moving_average([1,2,3,4,5], 3) == [2.0, 3.0, 4.0]\n',
    '`sliding_window([1,2], 5)` causes negative range.\n\nNo validation for window > list length.\n\nRun: `python -m pytest tests/test_window_util.py`')

add("bugfix_323", "off_by_one", "medium", "binary_search",
    'def binary_search(arr, target):\n    """Binary search, return index or -1."""\n    lo, hi = 0, len(arr)\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid\n        else:\n            hi = mid\n    return -1\n',
    'def binary_search(arr, target):\n    """Binary search, return index or -1."""\n    lo, hi = 0, len(arr) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n',
    'from binary_search import binary_search\n\ndef test_found():\n    assert binary_search([1,3,5,7,9], 5) == 2\n\ndef test_not_found():\n    assert binary_search([1,3,5,7,9], 4) == -1\n\ndef test_first():\n    assert binary_search([1,3,5,7,9], 1) == 0\n\ndef test_last():\n    assert binary_search([1,3,5,7,9], 9) == 4\n\ndef test_empty():\n    assert binary_search([], 1) == -1\n',
    '`binary_search([1,3,5,7,9], 9)` infinite loops.\n\n`lo = mid` never advances past found element.\n\nRun: `python -m pytest tests/test_binary_search.py`')

add("bugfix_324", "exception_handling", "medium", "json_patch",
    'import json\n\ndef merge_json(base_json, patch_json):\n    """Merge patch JSON into base."""\n    base = json.loads(base_json)\n    patch = json.loads(patch_json)\n    base.update(patch)\n    return json.dumps(base)\n',
    'import json\n\ndef merge_json(base_json, patch_json):\n    """Merge patch JSON into base."""\n    try:\n        base = json.loads(base_json)\n    except json.JSONDecodeError:\n        base = {}\n    try:\n        patch = json.loads(patch_json)\n    except json.JSONDecodeError:\n        return json.dumps(base)\n    if not isinstance(base, dict) or not isinstance(patch, dict):\n        return json.dumps(base)\n    base.update(patch)\n    return json.dumps(base)\n',
    'from json_patch import merge_json\nimport json\n\ndef test_basic():\n    result = json.loads(merge_json(\'{"a":1}\', \'{"b":2}\'))\n    assert result == {"a": 1, "b": 2}\n\ndef test_invalid_base():\n    result = json.loads(merge_json("invalid", \'{"a":1}\'))\n    assert result == {"a": 1}\n\ndef test_invalid_patch():\n    result = json.loads(merge_json(\'{"a":1}\', "bad"))\n    assert result == {"a": 1}\n',
    '`merge_json("invalid", \'{"a":1}\')` raises JSONDecodeError.\n\nRun: `python -m pytest tests/test_json_patch.py`')

add("bugfix_325", "default_arg", "easy", "env_util",
    'def get_env(key, default=""):\n    """Get environment variable."""\n    import os\n    return os.environ.get(key, default)\n\ndef get_env_int(key, default=0):\n    """Get environment variable as int."""\n    import os\n    return int(os.environ.get(key, default))\n',
    'def get_env(key, default=""):\n    """Get environment variable."""\n    import os\n    return os.environ.get(key, default)\n\ndef get_env_int(key, default=0):\n    """Get environment variable as int."""\n    import os\n    val = os.environ.get(key)\n    if val is None:\n        return default\n    try:\n        return int(val)\n    except ValueError:\n        return default\n',
    'import os\nfrom env_util import get_env, get_env_int\n\ndef test_get():\n    os.environ["TEST_KEY"] = "hello"\n    assert get_env("TEST_KEY") == "hello"\n    del os.environ["TEST_KEY"]\n\ndef test_missing():\n    assert get_env("NONEXISTENT_KEY", "default") == "default"\n\ndef test_int():\n    os.environ["TEST_INT"] = "42"\n    assert get_env_int("TEST_INT") == 42\n    del os.environ["TEST_INT"]\n\ndef test_int_invalid():\n    os.environ["TEST_INT"] = "abc"\n    assert get_env_int("TEST_INT", -1) == -1\n    del os.environ["TEST_INT"]\n',
    '`get_env_int("TEST_INT")` when env var is "abc" raises ValueError.\n\nRun: `python -m pytest tests/test_env_util.py`')

# === Fill remaining with more variations ===
for i, (tid, bt, diff, mod, bug, fix, test, iss) in enumerate([
    ("bugfix_326", "boundary_empty", "easy", "median_util",
     'def median(lst):\n    """Find median of list."""\n    s = sorted(lst)\n    n = len(s)\n    if n % 2 == 1:\n        return s[n // 2]\n    return (s[n//2 - 1] + s[n//2]) / 2\n',
     'def median(lst):\n    """Find median of list."""\n    if not lst:\n        return None\n    s = sorted(lst)\n    n = len(s)\n    if n % 2 == 1:\n        return s[n // 2]\n    return (s[n//2 - 1] + s[n//2]) / 2\n',
     'from median_util import median\n\ndef test_odd():\n    assert median([3,1,2]) == 2\n\ndef test_even():\n    assert median([1,2,3,4]) == 2.5\n\ndef test_empty():\n    assert median([]) is None\n',
     '`median([])` raises IndexError.\n\nRun: `python -m pytest tests/test_median_util.py`'),

    ("bugfix_327", "string_norm", "medium", "name_util",
     'def normalize_name(name):\n    """Normalize person name."""\n    return name.strip().title()\n',
     'def normalize_name(name):\n    """Normalize person name."""\n    parts = name.strip().split()\n    return " ".join(p.capitalize() for p in parts if p)\n',
     'from name_util import normalize_name\n\ndef test_basic():\n    assert normalize_name("john doe") == "John Doe"\n\ndef test_extra_spaces():\n    assert normalize_name("  john   doe  ") == "John Doe"\n\ndef test_mc():\n    assert normalize_name("MCDONALD") == "Mcdonald"\n',
     '`normalize_name("  john   doe  ")` returns "John   Doe" (extra spaces preserved).\n\nRun: `python -m pytest tests/test_name_util.py`'),

    ("bugfix_328", "regex", "medium", "mention_parse",
     'import re\n\ndef extract_mentions(text):\n    """Extract @mentions from text."""\n    return re.findall(r"@\\w+", text)\n',
     'import re\n\ndef extract_mentions(text):\n    """Extract @mentions from text."""\n    return re.findall(r"(?<![\\w])@(\\w+)", text)\n',
     'from mention_parse import extract_mentions\n\ndef test_basic():\n    assert extract_mentions("hello @user1 and @user2") == ["user1", "user2"]\n\ndef test_email():\n    assert extract_mentions("email@test.com @real_mention") == ["real_mention"]\n\ndef test_none():\n    assert extract_mentions("no mentions here") == []\n',
     '`extract_mentions("email@test.com")` incorrectly extracts "test" as mention.\n\nShould not match @ in email addresses.\n\nRun: `python -m pytest tests/test_mention_parse.py`'),

    ("bugfix_329", "multi_branch", "medium", "weather_util",
     'def describe_temp(celsius):\n    """Describe temperature."""\n    if celsius < 0:\n        return "freezing"\n    if celsius < 10:\n        return "cold"\n    if celsius < 20:\n        return "cool"\n    if celsius < 30:\n        return "warm"\n    return "hot"\n',
     'def describe_temp(celsius):\n    """Describe temperature."""\n    if celsius <= 0:\n        return "freezing"\n    if celsius <= 10:\n        return "cold"\n    if celsius <= 20:\n        return "cool"\n    if celsius <= 30:\n        return "warm"\n    return "hot"\n',
     'from weather_util import describe_temp\n\ndef test_freezing():\n    assert describe_temp(-5) == "freezing"\n\ndef test_zero():\n    assert describe_temp(0) == "freezing"\n\ndef test_ten():\n    assert describe_temp(10) == "cold"\n\ndef test_hot():\n    assert describe_temp(35) == "hot"\n',
     '`describe_temp(0)` returns "cold" instead of "freezing".\n\nBoundary at 0 should be freezing.\n\nRun: `python -m pytest tests/test_weather_util.py`'),

    ("bugfix_330", "stateful_counter", "medium", "rate_limiter",
     'class RateLimiter:\n    def __init__(self, max_calls):\n        self.max_calls = max_calls\n        self.calls = 0\n\n    def allow(self):\n        self.calls += 1\n        return self.calls <= self.max_calls\n\n    def reset(self):\n        self.calls = 0\n',
     'import time\n\nclass RateLimiter:\n    def __init__(self, max_calls, window=60):\n        self.max_calls = max_calls\n        self.window = window\n        self.calls = []\n\n    def allow(self):\n        now = time.time()\n        self.calls = [t for t in self.calls if now - t < self.window]\n        if len(self.calls) < self.max_calls:\n            self.calls.append(now)\n            return True\n        return False\n\n    def reset(self):\n        self.calls = []\n',
     'import time\nfrom rate_limiter import RateLimiter\n\ndef test_basic():\n    rl = RateLimiter(3)\n    assert rl.allow() is True\n    assert rl.allow() is True\n    assert rl.allow() is True\n    assert rl.allow() is False\n\ndef test_reset():\n    rl = RateLimiter(2)\n    rl.allow()\n    rl.allow()\n    rl.reset()\n    assert rl.allow() is True\n',
     'Rate limiter never resets: after max_calls, all future calls rejected forever.\n\nRun: `python -m pytest tests/test_rate_limiter.py`'),
]):
    TASKS.append({
        "task_id": tid, "bug_type": bt, "difficulty": diff, "module": mod,
        "buggy_code": bug, "fixed_code": fix, "test_code": test, "issue": iss,
        "target_file": f"{mod}.py",
    })

# Continue filling to reach 50
for i, (tid, bt, diff, mod, bug, fix, test, iss) in enumerate([
    ("bugfix_331", "config_parse", "medium", "env_config",
     'def parse_env_file(content):\n    """Parse .env file content."""\n    result = {}\n    for line in content.split("\\n"):\n        if "=" in line:\n            key, val = line.split("=", 1)\n            result[key.strip()] = val.strip()\n    return result\n',
     'def parse_env_file(content):\n    """Parse .env file content."""\n    result = {}\n    for line in content.split("\\n"):\n        line = line.strip()\n        if not line or line.startswith("#"):\n            continue\n        if "=" in line:\n            key, val = line.split("=", 1)\n            key = key.strip()\n            val = val.strip().strip("\\"").strip("\'")\n            result[key] = val\n    return result\n',
     'from env_config import parse_env_file\n\ndef test_basic():\n    assert parse_env_file("KEY=value") == {"KEY": "value"}\n\ndef test_quoted():\n    assert parse_env_file("KEY=\\"hello world\\"") == {"KEY": "hello world"}\n\ndef test_comment():\n    r = parse_env_file("# comment\\nKEY=val")\n    assert r == {"KEY": "val"}\n\ndef test_empty():\n    assert parse_env_file("") == {}\n',
     '`parse_env_file("KEY=\\"hello\\"")` returns value with quotes included.\n\nRun: `python -m pytest tests/test_env_config.py`'),

    ("bugfix_332", "multi_file", "hard", "plugin_sys",
     'class PluginManager:\n    def __init__(self):\n        self.plugins = {}\n\n    def register(self, name, func):\n        self.plugins[name] = func\n\n    def run(self, name, *args):\n        return self.plugins[name](*args)\n\n    def list_plugins(self):\n        return list(self.plugins.keys())\n',
     'class PluginManager:\n    def __init__(self):\n        self.plugins = {}\n\n    def register(self, name, func):\n        if name in self.plugins:\n            raise ValueError(f"Plugin {name} already registered")\n        self.plugins[name] = func\n\n    def run(self, name, *args):\n        if name not in self.plugins:\n            raise KeyError(f"Plugin {name} not found")\n        return self.plugins[name](*args)\n\n    def list_plugins(self):\n        return list(self.plugins.keys())\n',
     'import pytest\nfrom plugin_sys import PluginManager\n\ndef test_basic():\n    pm = PluginManager()\n    pm.register("add", lambda a, b: a + b)\n    assert pm.run("add", 1, 2) == 3\n\ndef test_not_found():\n    pm = PluginManager()\n    with pytest.raises(KeyError):\n        pm.run("missing")\n\ndef test_duplicate():\n    pm = PluginManager()\n    pm.register("x", lambda: 1)\n    with pytest.raises(ValueError):\n        pm.register("x", lambda: 2)\n',
     'No error handling for missing or duplicate plugins.\n\nRun: `python -m pytest tests/test_plugin_sys.py`'),

    ("bugfix_333", "boundary_empty", "medium", "chunk_text",
     'def chunk_text(text, max_len):\n    """Split text into chunks of max_len characters."""\n    return [text[i:i+max_len] for i in range(0, len(text), max_len)]\n\ndef summarize_chunks(chunks):\n    """Return first chunk as summary."""\n    return chunks[0]\n',
     'def chunk_text(text, max_len):\n    """Split text into chunks of max_len characters."""\n    if max_len <= 0:\n        return [text] if text else []\n    return [text[i:i+max_len] for i in range(0, len(text), max_len)]\n\ndef summarize_chunks(chunks):\n    """Return first chunk as summary."""\n    if not chunks:\n        return ""\n    return chunks[0]\n',
     'from chunk_text import chunk_text, summarize_chunks\n\ndef test_basic():\n    assert chunk_text("hello world", 5) == ["hello", " worl", "d"]\n\ndef test_empty():\n    assert chunk_text("", 5) == []\n\ndef test_summarize_empty():\n    assert summarize_chunks([]) == ""\n\ndef test_zero_len():\n    assert chunk_text("abc", 0) == ["abc"]\n',
     '`summarize_chunks([])` raises IndexError.\n`chunk_text("abc", 0)` causes infinite loop.\n\nRun: `python -m pytest tests/test_chunk_text.py`'),

    ("bugfix_334", "type_conversion", "medium", "roman_util",
     'def to_roman(num):\n    """Convert integer to Roman numeral."""\n    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]\n    syms = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]\n    result = ""\n    for v, s in zip(vals, syms):\n        while num >= v:\n            result += s\n            num -= v\n    return result\n\ndef from_roman(s):\n    """Convert Roman numeral to integer."""\n    return 0  # TODO\n',
     'def to_roman(num):\n    """Convert integer to Roman numeral."""\n    if not 1 <= num <= 3999:\n        return ""\n    vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]\n    syms = ["M","CM","D","CD","C","XC","L","XL","X","IX","V","IV","I"]\n    result = ""\n    for v, s in zip(vals, syms):\n        while num >= v:\n            result += s\n            num -= v\n    return result\n\ndef from_roman(s):\n    """Convert Roman numeral to integer."""\n    vals = {"M":1000,"D":500,"C":100,"L":50,"X":10,"V":5,"I":1}\n    result = 0\n    for i in range(len(s)):\n        if i + 1 < len(s) and vals[s[i]] < vals[s[i+1]]:\n            result -= vals[s[i]]\n        else:\n            result += vals[s[i]]\n    return result\n',
     'from roman_util import to_roman, from_roman\n\ndef test_to():\n    assert to_roman(3) == "III"\n    assert to_roman(4) == "IV"\n    assert to_roman(1994) == "MCMXCIV"\n\ndef test_from():\n    assert from_roman("III") == 3\n    assert from_roman("IV") == 4\n    assert from_roman("MCMXCIV") == 1994\n\ndef test_invalid_range():\n    assert to_roman(0) == ""\n    assert to_roman(4000) == ""\n',
     '`from_roman("IV")` returns 0 (not implemented).\n`to_roman(0)` returns "I" instead of "".\n\nRun: `python -m pytest tests/test_roman_util.py`'),

    ("bugfix_335", "nested_condition", "medium", "interest_calc",
     'def compound_interest(principal, rate, n, t):\n    """Calculate compound interest: A = P(1 + r/n)^(nt)"""\n    return principal * (1 + rate / n) ** (n * t)\n\ndef simple_interest(principal, rate, t):\n    """Calculate simple interest: A = P(1 + rt)"""\n    return principal * (1 + rate * t)\n',
     'def compound_interest(principal, rate, n, t):\n    """Calculate compound interest: A = P(1 + r/n)^(nt)"""\n    if principal <= 0 or n <= 0 or t < 0:\n        return principal\n    return principal * (1 + rate / n) ** (n * t)\n\ndef simple_interest(principal, rate, t):\n    """Calculate simple interest: A = P(1 + rt)"""\n    if principal <= 0 or t < 0:\n        return principal\n    return principal * (1 + rate * t)\n',
     'from interest_calc import compound_interest, simple_interest\n\ndef test_compound():\n    result = compound_interest(1000, 0.05, 12, 5)\n    assert 1280 < result < 1290\n\ndef test_simple():\n    assert simple_interest(1000, 0.05, 5) == 1250\n\ndef test_zero_principal():\n    assert compound_interest(0, 0.05, 12, 5) == 0\n\ndef test_negative():\n    assert simple_interest(-100, 0.05, 5) == -100\n',
     '`compound_interest(0, 0.05, 12, 5)` returns 0 but code has no guard.\n\nRun: `python -m pytest tests/test_interest_calc.py`'),

    ("bugfix_336", "string_norm", "easy", "filename_util",
     'def sanitize_filename(name):\n    """Make string safe for use as filename."""\n    return name\n',
     'def sanitize_filename(name):\n    """Make string safe for use as filename."""\n    import re\n    name = re.sub(r"[^\\w\\s.-]", "", name)\n    name = re.sub(r"\\s+", "_", name.strip())\n    return name[:200]\n',
     'from filename_util import sanitize_filename\n\ndef test_basic():\n    assert sanitize_filename("my file.txt") == "my_file.txt"\n\ndef test_special():\n    assert sanitize_filename("file/name:with*special") == "filenamewithspecial"\n\ndef test_long():\n    result = sanitize_filename("a" * 300)\n    assert len(result) <= 200\n',
     '`sanitize_filename("file/name")` returns "file/name" (invalid filename character).\n\nRun: `python -m pytest tests/test_filename_util.py`'),

    ("bugfix_337", "list_mutation", "medium", "pair_util",
     'def find_pairs(lst, target):\n    """Find pairs that sum to target."""\n    result = []\n    for i in range(len(lst)):\n        for j in range(i, len(lst)):\n            if lst[i] + lst[j] == target:\n                result.append((lst[i], lst[j]))\n    return result\n',
     'def find_pairs(lst, target):\n    """Find pairs that sum to target."""\n    result = []\n    for i in range(len(lst)):\n        for j in range(i + 1, len(lst)):\n            if lst[i] + lst[j] == target:\n                result.append((lst[i], lst[j]))\n    return result\n',
     'from pair_util import find_pairs\n\ndef test_basic():\n    result = find_pairs([1,2,3,4,5], 6)\n    assert (1,5) in result and (2,4) in result\n\ndef test_no_self():\n    result = find_pairs([3,3,3], 6)\n    assert (3,3) in result\n    assert len(result) == 1  # not (3,3) from same index\n\ndef test_none():\n    assert find_pairs([1,2], 10) == []\n',
     '`find_pairs([3,3,3], 6)` includes (3,3) from the same index twice.\n\nInner loop starts at `i` instead of `i+1`.\n\nRun: `python -m pytest tests/test_pair_util.py`'),

    ("bugfix_338", "off_by_one", "easy", "page_util",
     'def total_pages(items, per_page):\n    """Calculate total pages needed."""\n    return items // per_page\n',
     'def total_pages(items, per_page):\n    """Calculate total pages needed."""\n    if per_page <= 0:\n        return 0\n    return -(-items // per_page)  # ceiling division\n',
     'from page_util import total_pages\n\ndef test_exact():\n    assert total_pages(10, 5) == 2\n\ndef test_remainder():\n    assert total_pages(11, 5) == 3\n\ndef test_one():\n    assert total_pages(1, 10) == 1\n\ndef test_zero():\n    assert total_pages(0, 10) == 0\n',
     '`total_pages(11, 5)` returns 2 instead of 3.\n\nInteger division truncates remainder.\n\nRun: `python -m pytest tests/test_page_util.py`'),

    ("bugfix_339", "exception_handling", "medium", "retry_util",
     'def retry(func, max_attempts=3):\n    """Retry function on failure."""\n    for i in range(max_attempts):\n        try:\n            return func()\n        except Exception:\n            pass\n    return None\n',
     'def retry(func, max_attempts=3, delay=0):\n    """Retry function on failure."""\n    import time\n    last_error = None\n    for i in range(max_attempts):\n        try:\n            return func()\n        except Exception as e:\n            last_error = e\n            if delay > 0:\n                time.sleep(delay)\n    raise last_error\n',
     'import pytest\nfrom retry_util import retry\n\ndef test_success():\n    counter = [0]\n    def f():\n        counter[0] += 1\n        if counter[0] < 3:\n            raise ValueError("not yet")\n        return "ok"\n    assert retry(f, max_attempts=5) == "ok"\n\ndef test_all_fail():\n    def f():\n        raise ValueError("always fails")\n    with pytest.raises(ValueError):\n        retry(f, max_attempts=2)\n',
     '`retry(failing_func)` silently returns None on exhaustion.\nShould raise the last error.\n\nRun: `python -m pytest tests/test_retry_util.py`'),

    ("bugfix_340", "config_parse", "medium", "flags_util",
     'def parse_flags(args):\n    """Parse command-line flags like --key=value."""\n    result = {}\n    for arg in args:\n        if arg.startswith("--"):\n            key, val = arg[2:].split("=", 1)\n            result[key] = val\n    return result\n',
     'def parse_flags(args):\n    """Parse command-line flags like --key=value or --flag."""\n    result = {}\n    for arg in args:\n        if arg.startswith("--"):\n            if "=" in arg:\n                key, val = arg[2:].split("=", 1)\n                result[key] = val\n            else:\n                result[arg[2:]] = True\n    return result\n',
     'from flags_util import parse_flags\n\ndef test_kv():\n    assert parse_flags(["--name=test"]) == {"name": "test"}\n\ndef test_bool():\n    assert parse_flags(["--verbose"]) == {"verbose": True}\n\ndef test_mixed():\n    r = parse_flags(["--name=test", "--debug"])\n    assert r == {"name": "test", "debug": True}\n',
     '`parse_flags(["--verbose"])` raises ValueError (no = sign).\n\nRun: `python -m pytest tests/test_flags_util.py`'),
]):
    TASKS.append({
        "task_id": tid, "bug_type": bt, "difficulty": diff, "module": mod,
        "buggy_code": bug, "fixed_code": fix, "test_code": test, "issue": iss,
        "target_file": f"{mod}.py",
    })


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
    print(f"Building {len(TASKS)} final tasks...")
    for task in TASKS:
        build_task_dir(tasks_root, task)
        print(f"  {task['task_id']}: {task['bug_type']} ({task['difficulty']})")

    all_new = sorted([p.name for p in tasks_root.iterdir()
                     if p.is_dir() and p.name.startswith("bugfix_")
                     and int(p.name.split("_")[1]) >= 251])
    splits_dir = root / "outputs" / "data" / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    (splits_dir / "new100_heldout_tasks.txt").write_text("\n".join(all_new) + "\n", encoding="utf-8")
    print(f"\nTotal new tasks: {len(all_new)}")


if __name__ == "__main__":
    main()
