from __future__ import annotations

from evocode_orchard_lite.schema import Step, Task


# Tool descriptions with required parameters
TOOL_DESCRIPTIONS = {
    "list_files": {
        "description": "List files in the workspace",
        "parameters": {},
        "example": '{"thought": "I need to see the file structure", "action": "list_files", "arguments": {}}'
    },
    "read_file": {
        "description": "Read the content of a file",
        "parameters": {"path": "File path relative to workspace"},
        "example": '{"thought": "I need to read the file", "action": "read_file", "arguments": {"path": "auth.py"}}'
    },
    "search_code": {
        "description": "Search for a pattern in the codebase",
        "parameters": {"pattern": "Search pattern (regex supported)"},
        "example": '{"thought": "I need to find where the bug is", "action": "search_code", "arguments": {"pattern": "def authenticate"}}'
    },
    "edit_file": {
        "description": "Edit a file by replacing old text with new text",
        "parameters": {
            "path": "File path relative to workspace (REQUIRED)",
            "old": "Exact old text to replace (REQUIRED)",
            "new": "New text to replace with (REQUIRED)"
        },
        "example": '{"thought": "I need to fix the bug", "action": "edit_file", "arguments": {"path": "auth.py", "old": "return token expired", "new": "return token is expired"}}'
    },
    "run_tests": {
        "description": "Run pytest on the test files",
        "parameters": {},
        "example": '{"thought": "I need to run the tests", "action": "run_tests", "arguments": {}}'
    },
    "git_diff": {
        "description": "Show the current diff of changes",
        "parameters": {},
        "example": '{"thought": "I need to see what I changed", "action": "git_diff", "arguments": {}}'
    },
    "submit_patch": {
        "description": "Submit the final patch (must run tests first)",
        "parameters": {},
        "example": '{"thought": "Tests pass, I can submit", "action": "submit_patch", "arguments": {}}'
    }
}


class PromptBuilder:
    def build(self, task: Task, history: list[Step], tools: list[str]) -> str:
        history_text = "\n".join(
            f"{step.step}. action={step.action} success={step.tool_success}\nobservation={step.observation[:1000]}"
            for step in history
        )
        
        # Build tool descriptions
        tool_desc_lines = []
        for tool_name in tools:
            if tool_name in TOOL_DESCRIPTIONS:
                desc = TOOL_DESCRIPTIONS[tool_name]
                params = desc["parameters"]
                param_str = ", ".join(f"{k}: {v}" for k, v in params.items()) if params else "none"
                tool_desc_lines.append(f"- {tool_name}: {desc['description']}")
                tool_desc_lines.append(f"  Parameters: {param_str}")
                tool_desc_lines.append(f"  Example: {desc['example']}")
            else:
                tool_desc_lines.append(f"- {tool_name}")
        
        tool_desc = "\n".join(tool_desc_lines)
        
        return f"""You are a coding repair agent.

Issue:
{task.issue}

Metadata:
{task.metadata}

Available tools:
{tool_desc}

IMPORTANT RULES:
1. Respond with exactly one JSON object, NO markdown formatting, NO code blocks
2. For edit_file, you MUST provide all three parameters: "path", "old", "new"
3. The "old" text must be EXACTLY as it appears in the file
4. Always run tests before submitting
5. DO NOT use ```json or ``` blocks, just raw JSON

Response format:
{{"thought": "...", "action": "tool_name", "arguments": {{...}}}}

History:
{history_text or "(empty)"}
"""
