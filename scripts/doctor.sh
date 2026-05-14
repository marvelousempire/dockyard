#!/usr/bin/env bash
# Dockyard doctor — diagnose host, engine, socket. Auto-fix where safe.
#
# Run from anywhere:
#   make doctor
#   bash dockyard/scripts/doctor.sh
#
# Exit codes:
#   0 — all green
#   1 — at least one failure
#   2 — fixable but user declined

set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE" || exit 1

# Colors (gracefully degrade if not a tty)
if [ -t 1 ]; then
  G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; B=$'\033[36m'; D=$'\033[2m'; N=$'\033[0m'
else
  G=""; R=""; Y=""; B=""; D=""; N=""
fi

pass=0
fail=0

check() {
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf '  %s✅%s %s\n' "$G" "$N" "$label"
    pass=$((pass+1))
    return 0
  else
    printf '  %s❌%s %s\n' "$R" "$N" "$label"
    fail=$((fail+1))
    return 1
  fi
}

note() {
  printf '     %s%s%s\n' "$D" "$1" "$N"
}

echo ""
echo "${B}🩺  Dockyard doctor${N}"
echo "    $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 1. Python version
echo "${B}Python${N}"
if command -v python3 >/dev/null 2>&1; then
  PYV="$(python3 --version 2>&1)"
  note "found: $PYV"
  PYMAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
  PYMINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
  if [ "$PYMAJOR" -ge 3 ] && [ "$PYMINOR" -ge 9 ]; then
    check "Python 3.9+ available" true
  else
    check "Python 3.9+ available" false
  fi
else
  check "Python 3 available" false
fi
echo ""

# 2. Engine candidate
echo "${B}Docker engine${N}"
ENGINE=""
SOCKET=""
if command -v colima >/dev/null 2>&1; then
  note "colima installed: $(colima version 2>/dev/null | head -1)"
  if colima status 2>/dev/null | grep -qi "running"; then
    check "Colima running" true
    SOCKET="$HOME/.colima/default/docker.sock"
    ENGINE="colima"
  else
    printf '  %s⚠️ %s  Colima installed but not running\n' "$Y" "$N"
    note "fix: colima start"
    fail=$((fail+1))
  fi
elif command -v orb >/dev/null 2>&1; then
  note "orbstack installed"
  ENGINE="orbstack"
  SOCKET="$HOME/.orbstack/run/docker.sock"
elif [ -S "/var/run/docker.sock" ]; then
  ENGINE="native"
  SOCKET="/var/run/docker.sock"
  check "native /var/run/docker.sock present" true
elif [ -S "$HOME/Library/Containers/com.docker.docker/Data/docker.raw.sock" ]; then
  ENGINE="docker-desktop"
  SOCKET="$HOME/Library/Containers/com.docker.docker/Data/docker.raw.sock"
  check "Docker Desktop socket present" true
else
  check "any Docker engine installed" false
  note "fix: brew install colima  (recommended on Apple Silicon)"
fi
echo ""

# 3. Socket reachability
echo "${B}Socket${N}"
if [ -n "$SOCKET" ]; then
  note "socket: $SOCKET"
  note "engine: $ENGINE"
  if curl -fsS --max-time 3 --unix-socket "$SOCKET" http://localhost/_ping >/dev/null 2>&1; then
    check "Docker socket reachable (/_ping)" true
  else
    check "Docker socket reachable (/_ping)" false
    note "the socket file exists but /_ping timed out — engine may be hung"
    note "fix: restart the engine (colima restart / orb restart / Docker Desktop)"
  fi
else
  check "Socket path determined" false
fi
echo ""

# 4. Port availability
echo "${B}Port${N}"
PORT=$(python3 -c "import json,sys; sys.stdout.write(str(json.load(open('dockyard.config.json')).get('port',4321)))" 2>/dev/null || echo 4321)
note "configured port: $PORT"
if lsof -i ":$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  HOLDER=$(lsof -i ":$PORT" -sTCP:LISTEN -P -n 2>/dev/null | awk 'NR==2 {print $1" (pid "$2")"}')
  printf '  %s⚠️ %s  Port %s in use by %s\n' "$Y" "$N" "$PORT" "$HOLDER"
  note "fix: pkill -f 'dockyard/server.py'  or change \"port\" in dockyard.config.json"
else
  check "Port $PORT free" true
fi
echo ""

# Summary
echo "${B}Summary${N}"
printf "  ${G}passed${N}: %d   ${R}failed${N}: %d\n" "$pass" "$fail"
echo ""

if [ "$fail" -eq 0 ]; then
  echo "${G}✅ all green — \`make run\` to start${N}"
  exit 0
else
  echo "${R}❌ fix the items above, then re-run \`make doctor\`${N}"
  exit 1
fi
