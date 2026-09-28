#!/usr/bin/env python3
"""CareLoop MCP demo client — talks to the CareLoop MCP server like a real AI portal.

Runs the exact integration story from the docs:
  1. initialize + initialized handshake            (MCP lifecycle)
  2. tools/list                                    (discover the six CareLoop tools)
  3. careloop_list_patients                        (who is in the system?)
  4. careloop_list_cards                           (find the demo patient's open cards)
  5. careloop_get_card                             (inspect the MRI card + its dependents)
  6. careloop_close_card with evidence             (the loop-closing write)
  7. careloop_get_card again                       (verified_closed + risk cleared downstream)

No external MCP SDK required — it speaks JSON-RPC 2.0 over the Streamable HTTP
endpoint directly, the same wire protocol ChatGPT/Claude use.

Usage:
    uv run --system-certs python demo_client.py [--base http://localhost:8100]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

ACCEPT = "application/json, text/event-stream"
TIMEOUT = 30


class McpClient:
    """Minimal MCP client over Streamable HTTP (JSON-RPC 2.0)."""

    def __init__(self, base: str):
        self.endpoint = base.rstrip("/") + "/mcp"
        self.session_id: str | None = None
        self._next_id = 0

    def _post(self, payload: dict) -> dict | None:
        """POST one JSON-RPC message; parse the SSE `data:` line if streamed."""
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Accept": ACCEPT},
            method="POST",
        )
        if self.session_id:
            req.add_header("mcp-session-id", self.session_id)
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            sid = resp.headers.get("mcp-session-id")
            if sid:
                self.session_id = sid
            body = resp.read().decode()

        if not body.strip():
            return None
        # Streamable HTTP may answer as SSE; take the last `data:` line.
        if body.lstrip().startswith("event:") or "\ndata:" in body or body.startswith("data:"):
            data_lines = [ln[5:].strip() for ln in body.splitlines() if ln.startswith("data:")]
            if not data_lines:
                return None
            return json.loads(data_lines[-1])
        return json.loads(body)

    def request(self, method: str, params: dict | None = None) -> dict:
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            payload["params"] = params
        resp = self._post(payload)
        if resp is None:
            raise RuntimeError(f"{method}: empty response")
        if "error" in resp:
            raise RuntimeError(f"{method}: JSON-RPC error {resp['error']}")
        return resp["result"]

    def notify(self, method: str, params: dict | None = None) -> None:
        payload: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._post(payload)

    # -- MCP lifecycle ---------------------------------------------------

    def initialize(self) -> dict:
        result = self.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "careloop-demo-client", "version": "1.0"},
            },
        )
        self.notify("notifications/initialized")
        return result

    def tools_list(self) -> list[dict]:
        return self.request("tools/list")["tools"]

    def tools_call(self, name: str, arguments: dict) -> dict | list:
        # FastMCP binds the whole argument dict to the tool's single `params`
        # model, so arguments ride under the "params" key.
        result = self.request("tools/call", {"name": name, "arguments": {"params": arguments}})
        content = result.get("content", [])
        text = content[0]["text"] if content else "{}"
        # FastMCP may return the tool's JSON string as-is or double-encoded;
        # unwrap until we have real data.
        data = text
        while isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return {"raw": data}
        return data


def hr(title: str) -> None:
    print(f"\n{'─' * 62}\n{title}\n{'─' * 62}")


def tool_result_banner(name: str, data: dict) -> None:
    ok = data.get("ok", True)
    marker = "✓" if ok else "✗"
    print(f"{marker} {name} → {json.dumps(data, indent=2, ensure_ascii=False)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://localhost:8100", help="MCP server base URL")
    ap.add_argument("--patient", type=int, default=1, help="patient id to demo with")
    args = ap.parse_args()

    client = McpClient(args.base)

    hr("1 · MCP handshake — initialize")
    info = client.initialize()
    print(f"server   : {info['serverInfo']['name']} v{info['serverInfo']['version']}")
    print(f"protocol : {info['protocolVersion']}")
    print(f"session  : {client.session_id}")

    hr("2 · tools/list — what can the AI portal do?")
    tools = client.tools_list()
    for t in tools:
        ro = t.get("annotations", {}).get("readOnlyHint", "?")
        kind = "read " if ro else "WRITE"
        print(f"  [{kind}] {t['name']}")

    hr("3 · careloop_list_patients")
    patients = client.tools_call("careloop_list_patients", {})
    for p in patients:
        print(f"  patient {p['id']}: {p['name']}")

    hr(f"4 · careloop_list_cards (patient {args.patient}, open only)")
    cards = client.tools_call("careloop_list_cards", {"patient_id": args.patient, "status": "open"})
    for c in cards:
        print(f"  card {c['id']:>3} [{c['type']:>12}] {c['description']}")
    if not cards:
        print("  (no open cards — nothing to demo)")
        return 1

    # Pick the demo card: an open card that something else depends on, else any open card.
    dependents: dict[int, list[dict]] = {}
    for c in cards:
        detail = client.tools_call("careloop_get_card", {"card_id": c["id"]})
        for dep in detail.get("depends_on", []):
            dependents.setdefault(dep["upstream_card_id"], []).append(detail)
    demo = next((c for c in cards if c["id"] in dependents), cards[0])
    demo_detail = client.tools_call("careloop_get_card", {"card_id": demo["id"]})

    hr(f"5 · careloop_get_card — inspecting card {demo['id']}")
    print(json.dumps(demo_detail, indent=2, ensure_ascii=False))

    hr(f"6 · careloop_close_card — closing card {demo['id']} with evidence")
    evidence = "Scan completed and reviewed this morning"
    result = client.tools_call("careloop_close_card", {"card_id": demo["id"], "evidence": evidence})
    tool_result_banner("careloop_close_card", result)
    if not result.get("ok"):
        print("\nDemo cannot continue: the close was rejected.")
        return 1

    hr("7 · verify — card state after the evidence-based close")
    after = client.tools_call("careloop_get_card", {"card_id": demo["id"]})
    print(f"  card {after['id']}: {after['status']}")

    if demo["id"] in dependents:
        print("\n  downstream cards that depended on it:")
        for dep_detail in dependents[demo["id"]]:
            refreshed = client.tools_call("careloop_get_card", {"card_id": dep_detail["id"]})
            print(f"    card {refreshed['id']}: {refreshed['status']} — {refreshed['risk_reason'] or 'risk cleared ✓'}")

    hr("Demo complete")
    print("The AI portal closed a care-plan loop through MCP, and the commitment")
    print("graph re-checked everything downstream — exactly like the in-app flow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
