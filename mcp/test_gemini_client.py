"""Offline tests for gemini_client.py — no Gemini key, no MCP server needed."""

from __future__ import annotations

import asyncio
import types

import gemini_client as gc


# ----------------------------------------------------------------- schema bridge

MCP_TOOL = {
    "name": "careloop_close_card",
    "description": "Close a card as verified done because external evidence exists.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "card_id": {"type": "integer", "description": "CareLoop card id", "minimum": 1},
            "evidence": {"type": "string", "description": "Proof phrase"},
        },
        "required": ["card_id", "evidence"],
    },
}


def test_declaration_conversion():
    d = gc.McpToolBridge.to_gemini_declaration(MCP_TOOL)
    assert d["type"] == "function"
    assert d["name"] == "careloop_close_card"
    assert d["parameters"]["type"] == "object"
    assert set(d["parameters"]["required"]) == {"card_id", "evidence"}
    assert d["parameters"]["properties"]["card_id"]["type"] == "integer"


def test_declaration_strips_pydantic_extras():
    """FastMCP/Pydantic schema → Gemini-safe OpenAPI subset."""
    tool = {
        "name": "careloop_list_cards",
        "description": "List cards.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "patient_id": {
                    "anyOf": [{"type": "integer", "minimum": 1}, {"type": "null"}],
                    "default": None,
                    "description": "Restrict to this patient id.",
                },
                "status": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "default": None,
                    "description": "Filter by status.",
                },
                "limit": {"type": "integer", "default": 50, "maximum": 200},
            },
            "required": [],
        },
    }
    p = gc.McpToolBridge.to_gemini_declaration(tool)["parameters"]
    pid = p["properties"]["patient_id"]
    assert pid["type"] == "integer" and "anyOf" not in pid
    assert pid["description"] == "Restrict to this patient id."  # description kept through anyOf unwrap
    assert "minimum" not in pid and "default" not in pid
    assert p["properties"]["limit"] == {"type": "integer"}
    assert p["required"] == []


# ----------------------------------------------------------------- fake MCP side

class FakeMcp:
    """Stands in for McpClient; records calls, returns canned data."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.results: list = []

    def initialize(self):
        return {}

    def tools_list(self):
        return [MCP_TOOL]

    def tools_call(self, name, arguments):
        self.calls.append((name, arguments))
        return self.results.pop(0)


def make_bridge(results):
    bridge = gc.McpToolBridge.__new__(gc.McpToolBridge)
    bridge.mcp = FakeMcp()
    bridge.mcp.results = list(results)
    bridge.mcp_tools = bridge.mcp.tools_list()
    bridge.names = {t["name"] for t in bridge.mcp_tools}
    return bridge


# ----------------------------------------------------------------- fake Gemini side

def step_fc(call_id, name, args):
    return types.SimpleNamespace(type="function_call", id=call_id, name=name, arguments=args)


def step_out(text):
    return types.SimpleNamespace(type="model_output", content=[types.SimpleNamespace(text=text)])


class FakeInteractions:
    """First create() → function_call; after results are replayed → final text."""

    def __init__(self, script):
        self.script = list(script)
        self.inputs: list = []

    def create(self, **kwargs):
        self.inputs.append(kwargs)
        action = self.script.pop(0)
        if action == "call":
            return types.SimpleNamespace(
                id="ixn-1",
                output_text=None,
                steps=[step_fc("gth-1", "careloop_close_card", {"card_id": 12, "evidence": "MRI done"})],
            )
        return types.SimpleNamespace(id="ixn-2", output_text=action, steps=[step_out(action)])


def test_gemini_turn_executes_mcp_call_and_answers():
    bridge = make_bridge(results=[{"ok": True, "card_id": 12, "status": "verified_closed"}])
    fake = FakeInteractions(script=["call", "Closed card 12."])
    interaction = types.SimpleNamespace(interactions=fake)

    answer = gc.gemini_turn(interaction, bridge, "close card 12", verbose=False)

    assert answer == "Closed card 12."
    # The MCP bridge really ran the tool, with args passed through flat.
    assert bridge.mcp.calls == [("careloop_close_card", {"card_id": 12, "evidence": "MRI done"})]
    # The function_result was replayed to Gemini as a step with call_id.
    replay = fake.inputs[-1]["input"]
    fr = [s for s in replay if isinstance(s, dict) and s.get("type") == "function_result"]
    assert fr and fr[0]["call_id"] == "gth-1"
    import json as _json
    assert _json.loads(fr[0]["result"])["ok"] is True  # result is a JSON string


def test_gemini_turn_survives_double_encoded_result():
    bridge = make_bridge(results=['{"ok": true, "card_id": 12}'])  # double-encoded output
    fake = FakeInteractions(script=["call", "Done."])
    interaction = types.SimpleNamespace(interactions=fake)

    gc.gemini_turn(interaction, bridge, "close 12", verbose=False)

    assert bridge.mcp.calls[0][0] == "careloop_close_card"


def test_unknown_tool_is_reported_not_raised():
    bridge = make_bridge(results=[])  # never popped: unknown tool is rejected before dispatch
    scripted = _Scripted([step_fc("gth-2", "careloop_nope", {}), "Recovered."])

    answer = gc.gemini_turn(scripted, bridge, "do a thing", verbose=False)
    assert answer == "Recovered."


class _Scripted:
    """Fake genai.Client whose interactions.create pops a script of
    function_call steps (asked-for tools) and final text answers."""

    def __init__(self, script):
        self.script = list(script)
        self.inputs: list = []
        self.interactions = self  # gemini_turn calls client.interactions.create

    def create(self, **kwargs):
        self.inputs.append(kwargs)
        action = self.script.pop(0)
        if isinstance(action, types.SimpleNamespace):
            return types.SimpleNamespace(id="ixn-x", output_text=None, steps=[action])
        return types.SimpleNamespace(id="ixn-y", output_text=action, steps=[step_out(action)])
