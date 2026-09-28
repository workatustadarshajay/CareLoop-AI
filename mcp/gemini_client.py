#!/usr/bin/env python3
"""CareLoop × Gemini demo client — natural-language control of the MCP tools.

A real "AI portal" demo: Gemini sees the six CareLoop MCP tools (discovered
live over Streamable HTTP), decides which to call from plain English, and the
results feed back until it can answer. Wire format on both sides:

    Gemini ──Interactions API (function calling)──► this script
                  │  function_call(name, args)
                  ▼
    MCP server ──Streamable HTTP (JSON-RPC 2.0)──► mcp/server.py
                  │  httpx + Bearer token
                  ▼
            CareLoop API ──► Postgres

Usage:
    # one-shot demo script (good for recording):
    uv run --system-certs python gemini_client.py \
        --task "Check Alice Johnson's at-risk cards and close the MRI scan card with evidence 'MRI completed on Monday'"

    # interactive chat:
    uv run --system-certs python gemini_client.py --chat

Env:
    GEMINI_API_KEY     Google AI Studio API key (required)
    GEMINI_MODEL       model name (default gemini-3.8-flash)
    CARELOOP_API_URL   CareLoop API base URL (default http://localhost:8000/api)
    CARELOOP_USERNAME  service account (default dr_smith)   — set on the MCP server
    CARELOOP_PASSWORD  service account password (default password)

A sibling `.env` file (KEY=VALUE lines) is loaded automatically if present, so
you can keep GEMINI_API_KEY out of your shell history.

This makes a handful of real MCP tool calls (reads are free; writes only when
the task asks for them). A typical demo turn costs well under a cent on the
Gemini free tier / pay-as-you-go.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

MAX_STEPS = 8


def _load_dotenv(path: str | None = None) -> None:
    """Tiny .env loader (no dependency): KEY=VALUE lines, # comments, quotes stripped."""
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_dotenv()

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

SYSTEM_INSTRUCTION = (
    "You are the AI assistant inside a care-coordination portal that talks to "
    "CareLoop through MCP tools. Rules:\n"
    "1. Use the careloop_* tools to look up real data before answering.\n"
    "2. careloop_close_card needs concrete evidence the step actually happened. "
    "If the user does not supply evidence, ask for it — never invent it.\n"
    "3. After any write, re-read the affected card and report the new status.\n"
    "4. Answer in the user's language, concisely, leading with the outcome. "
    "Mention card ids when discussing specific care-plan items."
)

# --------------------------------------------------------------------------- MCP

from demo_client import McpClient  # same folder, no package needed


def _unwrap(data):  # FastMCP may double-JSON-encode tool output
    while isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return {"raw": data}
    return data


_GEMINI_SCHEMA_KEYS = ("type", "description", "enum", "items", "properties", "required")


def _sanitize_schema(node):
    """Prune a JSON Schema node to the OpenAPI subset the Gemini API accepts.

    FastMCP emits Pydantic JSON Schema: nullable fields become `anyOf`
    (integer | null) and validation keywords (minimum, default, maxLength, …)
    ride along — Gemini rejects those with 400 Invalid JSON payload. Unwrap
    anyOf to its non-null branch (nullable fields are optional anyway) and
    drop everything outside Gemini's parameter subset.
    """
    if not isinstance(node, dict):
        return node
    node = dict(node)
    if "anyOf" in node:
        desc = node.get("description")
        variants = [v for v in node["anyOf"] if isinstance(v, dict) and v.get("type") != "null"]
        node = dict(_sanitize_schema(variants[0])) if variants else {"type": "string"}
        if desc and "description" not in node:
            node["description"] = desc
    else:
        node = {k: v for k, v in node.items() if k in _GEMINI_SCHEMA_KEYS}
    if isinstance(node.get("properties"), dict):
        node["properties"] = {k: _sanitize_schema(v) for k, v in node["properties"].items()}
        node.setdefault("type", "object")
    if "items" in node:
        node["items"] = _sanitize_schema(node["items"])
    return node


class McpToolBridge:
    """Discovers MCP tools and executes calls on behalf of Gemini."""

    def __init__(self, mcp_base: str):
        self.mcp = McpClient(mcp_base)
        self.mcp.initialize()
        self.mcp_tools = self.mcp.tools_list()
        self.names = {t["name"] for t in self.mcp_tools}

    # -- discovery ----------------------------------------------------------

    @staticmethod
    def to_gemini_declaration(tool: dict) -> dict:
        """MCP tool schema → Gemini function declaration.

        MCP inputSchema is JSON Schema; Gemini accepts OpenAPI subset (object
        properties with type/description/enum/items/required). Tools whose
        schema needs more than that would need pruning — ours are simple.
        """
        params = _sanitize_schema(tool.get("inputSchema") or {})
        params.setdefault("type", "object")
        params.setdefault("properties", {})
        params.setdefault("required", [])
        return {
            "type": "function",
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": params,
        }

    def gemini_tools(self) -> list[dict]:
        return [self.to_gemini_declaration(t) for t in self.mcp_tools]

    # -- execution ----------------------------------------------------------

    async def execute(self, name: str, arguments: dict):
        """Run one Gemini function_call against the MCP server.

        Gemini emits the tool's arguments flat ({card_id: 12, evidence: ...});
        our FastMCP server binds them under the single `params` model, so wrap.
        """
        if name not in self.names:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        # The MCP tool descriptions mention `params`, and some models echo that
        # convention back. tools_call adds the real wrapper, so unwrap any
        # redundant top-level {"params": ...} the model emitted.
        if set(arguments) == {"params"} and isinstance(arguments.get("params"), dict):
            arguments = arguments["params"]
        # MCP tool calls are sync JSON-RPC over HTTP; keep the event loop free.
        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(None, self.mcp.tools_call, name, arguments)
        return _unwrap(raw)


# --------------------------------------------------------------------------- Gemini

def _steps(interaction) -> list:
    steps = getattr(interaction, "steps", None)
    if callable(steps):  # SDK may expose a method
        steps = steps()
    return list(steps or [])


def _new_interaction(client, gemini_tools: list[dict], user_input: str, *, system: str):
    """Every turn re-specifies tools + system instruction (interaction-scoped)."""
    return client.interactions.create(
        model=MODEL,
        input=user_input,
        tools=gemini_tools,
        system_instruction=system,
        store=False,
    )


def _next_interaction(client, gemini_tools: list[dict], conversation: list, *, system: str):
    """Continue the conversation by replaying it as input steps.

    The replayed conversation MUST start with the user turn: the API rejects a
    function_call step that does not immediately follow a user or
    function_response turn.
    """
    return client.interactions.create(
        model=MODEL,
        input=conversation,
        tools=gemini_tools,
        system_instruction=system,
        store=False,
    )


def gemini_turn(client, bridge: McpToolBridge, user_input: str, verbose: bool = True) -> str:
    """One full agentic turn: chat → tool calls → results → … → final answer.

    Returns Gemini's final text. All state stays local (store=False): each
    round-trip replays the conversation as input steps, mirroring the MCP loop.
    """
    system = SYSTEM_INSTRUCTION
    conversation: list = [{"type": "user_input", "content": [{"type": "text", "text": user_input}]}]
    interaction = _new_interaction(client, bridge.gemini_tools(), user_input, system=system)

    for _ in range(MAX_STEPS):
        steps = _steps(interaction)
        calls = [s for s in steps if getattr(s, "type", None) == "function_call"]
        if not calls:
            text = getattr(interaction, "output_text", None)
            return text or "(no answer)"

        # Show the reasoning, then execute every tool call this round.
        if verbose:
            for s in steps:
                if getattr(s, "type", None) == "model_output":
                    for c in getattr(s, "content", []) or []:
                        t = getattr(c, "text", None)
                        if t:
                            print(f"  Gemini: {t}")
        results = []
        for call in calls:
            name = getattr(call, "name", "")
            args = getattr(call, "arguments", None)
            if isinstance(args, str):  # defensive: JSON-encoded arguments
                args = json.loads(args)
            if verbose:
                print(f"  → MCP tool call: {name}({json.dumps(args, ensure_ascii=False)})")
            result = asyncio.run(bridge.execute(name, dict(args or {})))
            if verbose:
                print(f"  ← result: {json.dumps(result, ensure_ascii=False)[:300]}")
            results.append(
                {
                    "type": "function_result",
                    "name": name,
                    "call_id": getattr(call, "id", None),
                    # FunctionResultStep.result is str | list[content] — not a
                    # bare JSON value — so serialize the tool output.
                    "result": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

        # Accumulate: user turn → calls → results → (model calls again or answers).
        conversation.extend(steps)
        conversation.extend(results)
        interaction = _next_interaction(client, bridge.gemini_tools(), conversation, system=system)

    return "(stopped: tool-call budget exhausted)"


# --------------------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mcp-base", default=os.environ.get("MCP_BASE", "http://localhost:8100"))
    ap.add_argument("--task", help="one-shot task for Gemini (demo script)")
    ap.add_argument("--chat", action="store_true", help="interactive multi-turn chat")
    args = ap.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        print("error: GEMINI_API_KEY is not set.\n"
              "Get a key at https://aistudio.google.com/apikey and export it:\n"
              "  export GEMINI_API_KEY=...")
        return 1

    from google import genai  # imported late so --help works without the SDK

    client = genai.Client()
    bridge = McpToolBridge(args.mcp_base)
    gemini_tools = bridge.gemini_tools()

    print(f"MCP server  : {args.mcp_base} ({len(gemini_tools)} tools discovered)")
    for t in bridge.mcp_tools:
        print(f"  · {t['name']}")

    if args.chat:
        print("\nInteractive chat — empty line to quit.\n")
        while True:
            try:
                user = input("you > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user:
                break
            print()
            print(gemini_turn(client, bridge, user))
            print()
        return 0

    task = args.task or (
        "Check Alice Johnson's at-risk care-plan cards. If one depends on an "
        "unfinished test, close that test card with evidence 'MRI completed on "
        "Monday' and report how the dependent card's status changed."
    )
    print(f"\nTask: {task}\n")
    answer = gemini_turn(client, bridge, task)
    print("\nGemini's answer:\n" + answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
