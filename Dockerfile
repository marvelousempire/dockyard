# Dockyard — runtime image
#
# Tiny (single-layer + slim base ≈ 50 MB). Python 3 stdlib only — no
# pip install. Mounts the host's Docker socket into the container so it
# can manage the same engine the rest of the compose stack runs on.
#
# Build:    docker build -f dockyard/Dockerfile -t dockyard .
# Run:      docker run --rm -p 4321:4321 \
#             -v /var/run/docker.sock:/var/run/docker.sock \
#             dockyard
# Compose:  declared in ../docker-compose.yml as service `dockyard`

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Dockyard"
LABEL org.opencontainers.image.source="https://github.com/marvelousempire/claude-chat-reader"
LABEL org.opencontainers.image.description="Lightweight Docker manager UI — local-first, stdlib-only"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Bring in the package layout the server expects
COPY dockyard /app/dockyard

# Defaults — override at runtime via env or by mounting a config file
ENV DOCKYARD_PORT=4321 \
    DOCKER_HOST=unix:///var/run/docker.sock \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 4321

# Bind to all interfaces inside the container; Caddy/host port mapping
# handles external exposure.
CMD ["python3", "-m", "dockyard.server", "--host", "0.0.0.0", "--no-open"]
