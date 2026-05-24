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

.PHONY: help boot ui ui-local run open doctor test test-unit test-integration mcp clean status docker-build docker-run brain-up brain-down brain-status tw-build tw-watch

BRAIN_DIR := brain

help:
	@echo "Dockyard targets (port=$(PORT)):"
	@echo "  ${YELLOW}make ui${RESET}             ${BOLD}One-keystroke boot from zero${RESET} — heals Docker Desktop"
	@echo "                       hangs, installs/starts Colima if needed, opens"
	@echo "                       browser, exposes on Wi-Fi LAN (alias: make boot)"
	@echo "  make ui-local       Same as ui, but bind to 127.0.0.1 only"
	@echo "  make run            Bare server, NO heal/install/browser (for CI)"
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

# THE entry point — heals + installs + starts engine, then Dockyard, opens browser.
ui boot:
	@bash bin/go

ui-local:
	@DOCKYARD_HOST=127.0.0.1 bash bin/go

# Bare server — no heal, no install, no browser. For scripts / CI / debugging.
run:
	@$(PY) server.py --port $(PORT) --no-open

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
	@bash tests/test_bin_go_engine_detection.sh

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

brain-up:
	@cd $(BRAIN_DIR) && test -f .env || cp .env.example .env
	@cd $(BRAIN_DIR) && docker compose up -d

brain-down:
	@cd $(BRAIN_DIR) && docker compose down

brain-status:
	@cd $(BRAIN_DIR) && docker compose ps
	@cd $(BRAIN_DIR) && docker compose exec -T db pg_isready -U dockyard -d dockyard_brain || true

# Tailwind v4 — one-shot compile from web/styles/input.css → web/static/dockyard.css.
# bin/go also runs this on boot when the source is newer than the artifact.
tw-build:
	@bash bin/tw -i web/styles/input.css -o web/static/dockyard.css --minify

# Tailwind v4 — watch mode for active CSS development.
tw-watch:
	@bash bin/tw -i web/styles/input.css -o web/static/dockyard.css --watch
