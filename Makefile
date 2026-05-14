# Dockyard — convenience targets
#
# Three canonical commands (BLUEPRINT.md pattern):
#   make run     — start the server (default port 4321 from dockyard.config.json)
#   make doctor  — diagnose host + engine + socket
#   make ui      — open the UI in a browser (starts server if needed)
#
# Plus:
#   make test    — run unit + integration tests (no extra deps)
#   make mcp     — start the MCP stdio server (for dispatcher / agent use)
#   make clean   — remove pycache, test artifacts
#
# Everything is stdlib-only. No pip install required.

SHELL    := /bin/bash
PORT     ?= $(shell python3 -c "import json,sys; sys.stdout.write(str(json.load(open('dockyard.config.json')).get('port',4321)))" 2>/dev/null || echo 4321)
PY       ?= python3
HERE     := $(shell pwd)

.PHONY: help run ui ui-local open doctor test test-unit test-integration mcp clean status docker-build docker-run

help:
	@echo "Dockyard targets (port=$(PORT)):"
	@echo "  make run            Start server, NO browser (logs in foreground)"
	@echo "  make ui             Start server + open browser"
	@echo "  make ui-local       127.0.0.1 only, no browser open"
	@echo "  make open           Open existing server's URL in browser (does not start)"
	@echo "  make doctor         Check host + engine + socket; offers fixes"
	@echo "  make test           Run unit + integration tests"
	@echo "  make test-unit      Unit tests only (socket detection)"
	@echo "  make test-integration Integration tests (needs Docker)"
	@echo "  make mcp            Start MCP stdio server (for AI agents)"
	@echo "  make status         Show what's running"
	@echo "  make docker-build   Build dockyard runtime image"
	@echo "  make docker-run     Run dockyard in a container against host socket"
	@echo "  make clean          Remove pycache + test artifacts"

run:
	@$(PY) server.py --port $(PORT) --no-open

ui:
	@$(PY) server.py --port $(PORT)

ui-local:
	@$(PY) server.py --port $(PORT) --host 127.0.0.1 --no-open

open:
	@URL="http://127.0.0.1:$(PORT)"; \
	if curl -fsS --max-time 1 "$$URL/api/config" >/dev/null 2>&1; then \
	  echo "Opening $$URL"; \
	  if command -v open >/dev/null; then open "$$URL"; \
	  elif command -v xdg-open >/dev/null; then xdg-open "$$URL"; \
	  else echo "(no opener found — visit $$URL)"; fi; \
	else echo "❌ Dockyard not running on port $(PORT). Try: make run"; exit 1; fi

docker-build:
	@docker build -f Dockerfile -t dockyard:0.3.0 -t dockyard:latest ..

docker-run:
	@docker run --rm -p $(PORT):4321 \
	  -v /var/run/docker.sock:/var/run/docker.sock \
	  -v $$(pwd)/dockyard.config.json:/app/dockyard/dockyard.config.json:ro \
	  dockyard:latest

doctor:
	@bash scripts/doctor.sh

test: test-unit test-integration

test-unit:
	@$(PY) -m unittest discover -s tests -p "test_socket.py" -v

test-integration:
	@$(PY) -m unittest discover -s tests -p "test_endpoints.py" -v

mcp:
	@$(PY) mcp.py

status:
	@if pgrep -f "dockyard/server.py" >/dev/null; then \
	  echo "✅ dockyard server running on port $(PORT)"; \
	  pgrep -lf "dockyard/server.py" | head -5; \
	else echo "❌ dockyard server not running"; fi

clean:
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@rm -f /tmp/dockyard-*.log 2>/dev/null || true
	@echo "✅ cleaned"
