"""Runtime guard to prevent invalid loops and enforce agent workflow.

Guards:
1. Repeat action reminder - if same action+args repeated
2. Edit after test reminder - if edit_file but no run_tests after
3. Tests passed submit reminder - if tests passed but no submit
4. Submit requires passed test - if submit without passed test
"""
from __future__ import annotations

from evocode_orchard_lite.schema import Step, Task


class ProgressGuard:
    """Runtime guard to prevent invalid loops and enforce workflow."""

    def __init__(self):
        self.last_actions: list[tuple[str, dict]] = []
        self.tests_passed_after_edit = False
        self.edited_since_last_test = False
        self.last_test_passed = False

    def check(self, task: Task, history: list[Step], proposed_action: str, proposed_args: dict) -> tuple[bool, str]:
        """Check if proposed action is allowed.
        
        Returns:
            (allowed, message) - if not allowed, message explains why
        """
        # Track state
        self._update_state(history)
        
        # Guard 1: Repeat action reminder
        if self._is_repeat(proposed_action, proposed_args):
            return False, "You already executed the same action with the same arguments. Choose a different action that makes progress."
        
        # Guard 2: Edit after test reminder
        if proposed_action == "edit_file" and self.edited_since_last_test:
            return False, "The code has been edited. Run tests before making further edits or submitting."
        
        # Guard 3: Tests passed submit reminder
        if self.last_test_passed and proposed_action not in ("submit_patch", "git_diff", "run_tests"):
            return False, "Tests have passed. Review the diff and submit the patch."
        
        # Guard 4: Submit requires passed test
        if proposed_action == "submit_patch" and not self.last_test_passed:
            return False, "Submission requires a passing test after the latest edit. Run tests first."
        
        return True, ""

    def _update_state(self, history: list[Step]) -> None:
        """Update internal state from history."""
        self.last_actions = []
        self.tests_passed_after_edit = False
        self.edited_since_last_test = False
        self.last_test_passed = False
        
        for step in history:
            action = step.action.get("name", "")
            args = step.action.get("arguments", {})
            self.last_actions.append((action, args))
            
            if action == "run_tests":
                self.edited_since_last_test = False
                if "passed" in step.observation.lower():
                    self.last_test_passed = True
                else:
                    self.last_test_passed = False
            
            if action == "edit_file":
                self.edited_since_last_test = True

    def _is_repeat(self, action: str, args: dict) -> bool:
        """Check if action+args was executed in last 2 steps."""
        if len(self.last_actions) < 2:
            return False
        
        # Check last 2 actions
        for prev_action, prev_args in self.last_actions[-2:]:
            if prev_action == action and prev_args == args:
                return True
        
        return False


def apply_guard(task: Task, history: list[Step], proposed_action: str, proposed_args: dict) -> tuple[bool, str]:
    """Apply progress guard to proposed action.
    
    Returns:
        (allowed, message) - if not allowed, message explains why
    """
    guard = ProgressGuard()
    return guard.check(task, history, proposed_action, proposed_args)
