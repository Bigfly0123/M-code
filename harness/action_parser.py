from __future__ import annotations

import json

from evocode_orchard_lite.schema import Action


class ActionParseError(ValueError):
    pass


def parse_action(response: str) -> Action:
    try:
        payload = json.loads(response)
    except json.JSONDecodeError as exc:
        raise ActionParseError(f"Response is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise ActionParseError("Response must be a JSON object.")
    if "action" not in payload:
        raise ActionParseError("Response must include an 'action' field.")

    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        raise ActionParseError("'arguments' must be a JSON object.")

    return Action(
        thought=str(payload.get("thought", "")),
        name=str(payload["action"]),
        arguments=arguments,
    )
