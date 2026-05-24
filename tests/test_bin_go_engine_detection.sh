#!/usr/bin/env bash
# Plan 0005 Task H — exercise bin/go's detect_engine for the colima-hung path.
#
# Sources detect_engine() from bin/go after stubbing `colima` and `curl` on
# PATH, asserts ENGINE lands in the right terminal state.
#
# Run directly:  bash tests/test_bin_go_engine_detection.sh
# Via make:      make test-unit  (wired through Makefile)

set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

pass=0
fail=0

note() { printf "  • %s\n" "$1"; }
ok()   { printf "  \033[32m✅\033[0m %s\n" "$1"; pass=$((pass + 1)); }
bad()  { printf "  \033[31m❌\033[0m %s\n" "$1"; fail=$((fail + 1)); }

# Write a controllable stub script for a binary on PATH.
#   $1 = name, $2 = exit code
stub_bin() {
  local name="$1" code="$2"
  cat > "$TMP/$name" <<EOF
#!/usr/bin/env bash
exit $code
EOF
  chmod +x "$TMP/$name"
}

run_case() {
  local label="$1" colima_code="$2" curl_code="$3" want_engine="$4"
  stub_bin colima "$colima_code"
  stub_bin curl   "$curl_code"
  # Source bin/go's detect_engine in a clean subshell so each case starts fresh.
  local got
  got=$(PATH="$TMP:$PATH" bash -c "
    set -u
    HOME='$TMP'
    mkdir -p \"\$HOME/.colima/default\"
    touch \"\$HOME/.colima/default/docker.sock\"
    # Source bin/go without executing its main body — pull out the function.
    awk '/^detect_engine\\(\\) \\{/,/^\\}/' '$HERE/bin/go' > '$TMP/detect_engine.sh'
    # Provide globals detect_engine reads.
    ENGINE=unknown SOCKET=
    source '$TMP/detect_engine.sh'
    detect_engine
    printf '%s' \"\$ENGINE\"
  ")
  if [ "$got" = "$want_engine" ]; then
    ok "$label  → ENGINE=$got"
  else
    bad "$label  → got ENGINE=$got, want $want_engine"
  fi
}

echo "▸ tests/test_bin_go_engine_detection.sh"
# colima exits 0 (running) + curl exits 0 (socket answers) → colima
run_case "colima running, socket OK" 0 0 colima
# colima exits 0 (running) + curl exits 1 (socket dead)   → colima-hung
run_case "colima running, socket dead" 0 1 colima-hung

echo ""
echo "  $pass passed, $fail failed"
[ "$fail" -eq 0 ] || exit 1
