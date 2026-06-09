"""Generate held-out tasks bugfix_235-250."""
from __future__ import annotations

import json
from pathlib import Path

TASKS: list[dict] = [
    {
        "task_id": "bugfix_235",
        "bug_type": "unit_conversion",
        "difficulty": "easy",
        "module": "temp_util",
        "buggy_code": '''def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return c * 9 / 5 + 32
''',
        "fixed_code": '''def celsius_to_fahrenheit(c):
    """Convert Celsius to Fahrenheit."""
    return round(c * 9 / 5 + 32, 2)
''',
        "test_code": '''from temp_util import celsius_to_fahrenheit


def test_boiling():
    assert celsius_to_fahrenheit(100) == 212.0


def test_body():
    result = celsius_to_fahrenheit(37)
    assert abs(result - 98.6) < 0.01
''',
        "issue": "`celsius_to_fahrenheit(37)` returns `98.60000000000001`.\n\nFloating point precision issue.\n\nRun: `python -m pytest tests/test_temp_util.py`",
        "scripted_fix": {"path": "temp_util.py", "old": "    return c * 9 / 5 + 32", "new": "    return round(c * 9 / 5 + 32, 2)"},
    },
    {
        "task_id": "bugfix_236",
        "bug_type": "time_delta",
        "difficulty": "easy",
        "module": "date_util",
        "buggy_code": '''from datetime import date


def days_until(target_str):
    """Calculate days until target date."""
    target = date.fromisoformat(target_str)
    today = date.today()
    delta = target - today
    return delta.days
''',
        "fixed_code": '''from datetime import date


def days_until(target_str, today_str=None):
    """Calculate days until target date."""
    target = date.fromisoformat(target_str)
    today = date.fromisoformat(today_str) if today_str else date.today()
    delta = target - today
    return delta.days
''',
        "test_code": '''from date_util import days_until


def test_future():
    assert days_until("2099-01-01") > 0


def test_specific():
    assert days_until("2025-06-01", today_str="2025-06-01") == 0
''',
        "issue": "Cannot test deterministically because it uses `date.today()`.\n\nAdd optional `today_str` parameter.\n\nRun: `python -m pytest tests/test_date_util.py`",
        "scripted_fix": {"path": "date_util.py", "old": "def days_until(target_str):\n    \"\"\"Calculate days until target date.\"\"\"\n    target = date.fromisoformat(target_str)\n    today = date.today()\n    delta = target - today\n    return delta.days", "new": "def days_until(target_str, today_str=None):\n    \"\"\"Calculate days until target date.\"\"\"\n    target = date.fromisoformat(target_str)\n    today = date.fromisoformat(today_str) if today_str else date.today()\n    delta = target - today\n    return delta.days"},
    },
    {
        "task_id": "bugfix_237",
        "bug_type": "config_defaults",
        "difficulty": "easy",
        "module": "cfg_util",
        "buggy_code": '''DEFAULTS = {"host": "localhost", "port": 8080}


def get_config(overrides=None):
    """Get config with overrides."""
    config = DEFAULTS
    if overrides:
        config.update(overrides)
    return config
''',
        "fixed_code": '''DEFAULTS = {"host": "localhost", "port": 8080}


def get_config(overrides=None):
    """Get config with overrides."""
    config = DEFAULTS.copy()
    if overrides:
        config.update(overrides)
    return config
''',
        "test_code": '''from cfg_util import get_config


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
        "issue": "After `get_config({\"host\": \"0.0.0.0\"})`, default is mutated.\n\nShould copy defaults.\n\nRun: `python -m pytest tests/test_cfg_util.py`",
        "scripted_fix": {"path": "cfg_util.py", "old": "    config = DEFAULTS", "new": "    config = DEFAULTS.copy()"},
    },
    {
        "task_id": "bugfix_238",
        "bug_type": "error_message",
        "difficulty": "easy",
        "module": "err_util",
        "buggy_code": '''def validate_age(age):
    """Validate age."""
    if age < 0 or age > 150:
        raise ValueError("Invalid age")
    return age
''',
        "fixed_code": '''def validate_age(age):
    """Validate age."""
    if age < 0 or age > 150:
        raise ValueError(f"Age must be 0-150, got {age}")
    return age
''',
        "test_code": '''from err_util import validate_age


def test_valid():
    assert validate_age(25) == 25


def test_invalid():
    try:
        validate_age(200)
        assert False
    except ValueError as e:
        assert "200" in str(e)
''',
        "issue": "Error message doesn't include the invalid value.\n\nShould include actual age in error.\n\nRun: `python -m pytest tests/test_err_util.py`",
        "scripted_fix": {"path": "err_util.py", "old": 'raise ValueError("Invalid age")', "new": 'raise ValueError(f"Age must be 0-150, got {age}")'},
    },
    {
        "task_id": "bugfix_239",
        "bug_type": "deduplication",
        "difficulty": "easy",
        "module": "dedup_util",
        "buggy_code":'''def deduplicate(lst):
    """Remove duplicates from list."""
    result = []
    for item in lst:
        if item not in result:
            result.append(item)
    return result
''',
        "fixed_code":'''def deduplicate(lst):
    """Remove duplicates from list."""
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
''',
        "test_code":'''from dedup_util import deduplicate


def test_basic():
    assert deduplicate([1, 2, 2, 3, 3, 3]) == [1, 2, 3]


def test_order():
    assert deduplicate([3, 1, 2, 1, 3]) == [3, 1, 2]
''',
        "issue": "Performance issue: `item not in result` is O(n) for each check.\n\nShould use set for O(1) lookup.\n\nRun: `python -m pytest tests/test_dedup_util.py`",
        "scripted_fix": {"path": "dedup_util.py", "old": "def deduplicate(lst):\n    \"\"\"Remove duplicates from list.\"\"\"\n    result = []\n    for item in lst:\n        if item not in result:\n            result.append(item)\n    return result", "new": "def deduplicate(lst):\n    \"\"\"Remove duplicates from list.\"\"\"\n    seen = set()\n    result = []\n    for item in lst:\n        if item not in seen:\n            seen.add(item)\n            result.append(item)\n    return result"},
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
