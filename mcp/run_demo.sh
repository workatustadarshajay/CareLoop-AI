#!/usr/bin/env bash
# CareLoop x Gemini MCP demo - interactive launcher.
#
#   bash mcp/run_demo.sh                 # interactive menu (type your own asks)
#   bash mcp/run_demo.sh "your task"     # one-shot task, then exit
#   bash mcp/run_demo.sh --chat          # straight into Gemini chat mode
#
# Reuses a CareLoop API already running on :8000 (never kills yours),
# otherwise starts one. Starts the MCP server on :8100, resets the demo
# data, and cleans up only what it started. No `exec` anywhere, so your
# terminal always survives.

set -u
export PATH="$HOME/.local/bin:$PATH"

API_PORT=8000
MCP_PORT=8100
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

API_PID=""; MCP_PID=""

cleanup() {
  [ -n "$MCP_PID" ] && kill "$MCP_PID" 2>/dev/null
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null
  wait 2>/dev/null
}
trap cleanup EXIT INT TERM

# ---- pretty output (colors only when stdout is a terminal) -----------------
if [ -t 1 ]; then
  B=$'\033[1m'; D=$'\033[2m'; C=$'\033[36m'; G=$'\033[32m'; Y=$'\033[33m'; R=$'\033[31m'; N=$'\033[0m'
else
  B=""; D=""; C=""; G=""; Y=""; R=""; N=""
fi

banner() {
  cat <<'EOF'
   ____ _   _    _    ____  ____  _____ _        _ _____ ____
  / ___| | | |  / \  |  _ \|  _ \| ____| |      | | ____|  _ \
 | |   | |_| | / _ \ | |_) | | | |  _| | |   _  | |  _| | |_) |
 | |___|  _  |/ ___ \|  _ <| |_| | |___| |__| |_| | |___|  _ <
  \____|_| |_/_/   \_\_| \_\____/|_____|______\___/|_____|_| \_\

   Gemini ⇄ MCP ⇄ CareLoop API   ·   type a request, watch it work
EOF
}

step()  { printf "\n%s==> %s%s\n" "$C" "$*" "$N"; }
ok()    { printf "%s✓ %s%s\n" "$G" "$*" "$N"; }
fail()  { printf "%s✗ %s%s\n" "$R" "$*" "$N"; }

# ---- preflight --------------------------------------------------------------
for bin in uv curl python3; do
  command -v "$bin" >/dev/null || { fail "'$bin' not found in PATH"; exit 1; }
done
[ -f "$ROOT/mcp/.env" ] || { fail "$ROOT/mcp/.env missing (GEMINI_API_KEY / GEMINI_MODEL)"; exit 1; }

# Free only OUR leftover MCP server from a previous crashed run.
pkill -f "uvicorn server:app --port $MCP_PORT" 2>/dev/null
sleep 1

# ---- 1. CareLoop API: reuse one already running, else start ours -----------
api_up() { curl -s -m 2 -X POST "http://localhost:$API_PORT/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"dr_smith","password":"password"}' | grep -q '"token"'; }

if api_up; then
  step "reusing CareLoop API already running on :$API_PORT"
else
  step "starting CareLoop API on :$API_PORT"
  ( cd "$ROOT/Backend" && uv run --system-certs uvicorn app.main:app --port "$API_PORT" \
      > /tmp/careloop_api.log 2>&1 ) &
  API_PID=$!
  for i in $(seq 1 20); do api_up && break; sleep 1; done
  api_up || { fail "CareLoop API did not start (see /tmp/careloop_api.log)"; exit 1; }
fi

fresh_token() {
  # Logins mint new tokens and the API may invalidate the previous one, so
  # re-login before talking to the API directly (the Gemini/MCP calls do
  # their own logins and will invalidate whatever we cached).
  TOK=$(curl -s -m 5 -X POST "http://localhost:$API_PORT/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"username":"dr_smith","password":"password"}' \
    | python3 -c 'import sys,json;print(json.load(sys.stdin).get("token",""))')
  [ -n "$TOK" ] || { fail "could not log in to the CareLoop API"; return 1; }
}

fresh_token || exit 1

api() { curl -s -m 5 -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' "$@"; }

# ---- 2. reset + status helpers ----------------------------------------------
reset_demo_data() {
  fresh_token || return 1
  api -X PATCH "http://localhost:$API_PORT/api/cards/12" -d '{"status":"open"}'    > /dev/null
  api -X PATCH "http://localhost:$API_PORT/api/cards/10" -d '{"status":"at_risk"}' > /dev/null
  ok "demo data reset  ${D}(card 12 'MRI scan' open → card 10 'Neurology' at_risk)${N}"
}

show_status() {
  fresh_token || return 1
  printf "\n%bDemo data right now:%s\n" "$B" "$N"
  for id in 10 12; do
    api "http://localhost:$API_PORT/api/cards" | python3 -c "
import sys, json
try:
    cards = json.load(sys.stdin)
except Exception:
    cards = None
if not isinstance(cards, list):
    print('  (API said:', (cards or {}).get('detail', 'no response'), '-')
else:
    c = next((x for x in cards if x['id'] == $id), None)
    if c is None:
        print('  card $id : (missing)')
    else:
        risk = f\"  reason: {c['risk_reason']}\" if c.get('risk_reason') else ''
        print(f\"  card {c['id']:>2} : {c['status']:<16} {c['description']}{risk}\")
"
  done
}

gemini_task() {  # $1 = the ask
  # Run from mcp/ so uv picks up mcp/.venv (google-genai >= 2.x). From the
  # repo root, uv walks up and binds to a different environment.
  ( cd "$ROOT/mcp" && CARELOOP_API_URL="http://localhost:$API_PORT/api" \
      uv run --system-certs python gemini_client.py --task "$1" )
}

# ---- 3. start the MCP server -------------------------------------------------
step "starting MCP server on :$MCP_PORT"
( cd "$ROOT/mcp" && CARELOOP_API_URL="http://localhost:$API_PORT/api" \
    uv run --system-certs uvicorn server:app --port "$MCP_PORT" \
    > /tmp/careloop_mcp.log 2>&1 ) &
MCP_PID=$!
for i in $(seq 1 20); do
  curl -s -m 2 "http://localhost:$MCP_PORT/health" >/dev/null 2>&1 && break
  sleep 1
done
curl -s -m 2 "http://localhost:$MCP_PORT/health" >/dev/null 2>&1 \
  || { fail "MCP server did not start (see /tmp/careloop_mcp.log)"; exit 1; }
ok "MCP server up  ${D}(http://localhost:$MCP_PORT/mcp · 6 careloop tools)${N}"

reset_demo_data

# ---- 4. modes -----------------------------------------------------------------
CLASSIC_TASK="Alice Johnson has an at-risk care-plan card. Find it, work out which upstream card is blocking it, close that upstream card with evidence 'MRI completed on Monday at the outpatient center', then report exactly what changed."

# one-shot modes: pass a task or --chat on the command line
if [ $# -gt 0 ]; then
  if [ "$1" = "--chat" ]; then
    step "interactive Gemini chat (empty line to quit)"
    ( cd "$ROOT/mcp" && CARELOOP_API_URL="http://localhost:$API_PORT/api" \
        uv run --system-certs python gemini_client.py --chat )
  else
    step "running your task"
    gemini_task "$1"
  fi
  STATUS=$?
  [ $STATUS -eq 0 ] && ok "done" || fail "failed (exit $STATUS) - see /tmp/careloop_mcp.log"
  exit $STATUS
fi

# ---- interactive menu ----------------------------------------------------------
printf "\n%s%s%s\n" "$B" "──────────────────────────────────────────────────────────" "$N"
banner
printf "%s%s%s\n" "$B" "──────────────────────────────────────────────────────────" "$N"

menu() {
  cat <<EOF

  ${B}What should Gemini do?${N}
    ${C}1${N}  Run the classic demo   ${D}(find at-risk card → close the MRI → watch risk clear)${N}
    ${C}2${N}  Ask Gemini anything    ${D}(type your own request)${N}
    ${C}3${N}  Show demo data status  ${D}(cards 10 & 12 right now)${N}
    ${C}4${N}  Reset demo data        ${D}(card 12 open, card 10 at_risk again)${N}
    ${C}q${N}  Quit

EOF
  printf "%byou > %s" "$C" "$N"
}

while true; do
  menu
  read -r choice || break
  case "$choice" in
    1)
      printf "\n%s%s%s\n" "$D" "──────── Gemini, take it away ────────" "$N"
      gemini_task "$CLASSIC_TASK"
      show_status
      ;;
    2)
      printf "%bask > %s" "$C" "$N"
      read -r ask || break
      [ -z "$ask" ] && continue
      printf "\n%s%s%s\n" "$D" "──────── Gemini, take it away ────────" "$N"
      gemini_task "$ask"
      ;;
    3) show_status ;;
    4) reset_demo_data ;;
    q|Q|quit|exit) break ;;
    *) printf "%sPick 1-4 or q.%s\n" "$Y" "$N" ;;
  esac
done

printf "\n%sBye! The MCP server has been shut down; your API on :%s was left untouched.%s\n" "$G" "$API_PORT" "$N"
exit 0
