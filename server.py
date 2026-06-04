#!/usr/bin/env python3
"""Dockyard server — lightweight HTTP UI for Docker.

Talks the Docker Engine API over a Unix socket (Colima, OrbStack,
Docker Desktop, native Linux). Serves a single-page HTML UI plus a
small JSON API. Python 3.10+ stdlib only — no pip install.

Run:
    python3 server.py                  # uses dockyard.config.json
    python3 server.py --port 5000      # override
    DOCKER_HOST=unix:///… python3 server.py
"""

from __future__ import annotations

import argparse
import datetime as _dt
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

# Make the package importable when run as a script:
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from dockyard.lib.socket import load_config, resolve_socket  # noqa: E402

WEB_ROOT = HERE / "web"
INDEX_HTML = WEB_ROOT / "index.html"
STATIC_ROOT = WEB_ROOT / "static"

# ---------------------------------------------------------------------------
# Docker socket transport
# ---------------------------------------------------------------------------


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    """``http.client.HTTPConnection`` that speaks over a Unix socket."""

    def __init__(self, socket_path: str, timeout: Optional[float] = None) -> None:
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:  # type: ignore[override]
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout is not None:
            sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


def docker_request(
    socket_path: str,
    method: str,
    path: str,
    *,
    body: Optional[bytes] = None,
    headers: Optional[dict] = None,
    timeout: Optional[float] = 15.0,
) -> Tuple[int, dict, bytes]:
    """One-shot request to the Docker Engine API. Returns (status, headers, body)."""
    conn = UnixSocketHTTPConnection(socket_path, timeout=timeout)
    try:
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        return resp.status, dict(resp.getheaders()), resp.read()
    finally:
        conn.close()


def docker_stream(
    socket_path: str,
    method: str,
    path: str,
    *,
    body: Optional[bytes] = None,
    headers: Optional[dict] = None,
):
    """Open a streaming request — caller reads chunks from ``resp``."""
    conn = UnixSocketHTTPConnection(socket_path, timeout=None)
    conn.request(method, path, body=body, headers=headers or {})
    resp = conn.getresponse()
    return conn, resp


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


# ── Network-mode token gate (nephew Plan 0140 Phase 3) ───────────────
# Loopback is trusted (the DGX-local dashboard). This dashboard can
# stop/restart/prune Docker containers, so any NON-loopback request MUST present
# `Authorization: Bearer $DOCKYARD_API_TOKEN`. Fail CLOSED: if the token env is
# unset, every network request is denied — never network-exposed unauthenticated.
_DOCKYARD_API_TOKEN = os.environ.get("DOCKYARD_API_TOKEN", "").strip()


def _is_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "::1", "localhost", "")


class DockyardHandler(BaseHTTPRequestHandler):
    server_version = "Dockyard/0.2.0"

    def _auth_ok(self) -> bool:
        host = self.client_address[0] if self.client_address else ""
        if _is_loopback(host):
            return True
        if not _DOCKYARD_API_TOKEN:
            return False
        return self.headers.get("Authorization", "") == f"Bearer {_DOCKYARD_API_TOKEN}"

    # injected from server attrs
    socket_path: str
    engine: str
    config: dict

    # silence default access log
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        sys.stderr.write(
            "[dockyard] %s - %s\n" % (self.address_string(), format % args)
        )

    # ----- routing -----

    def do_GET(self) -> None:  # noqa: N802
        if not self._auth_ok():
            return self._send_json(401, {"error": "unauthorized — network access requires a token"})
        path, query = self._split_path()
        try:
            if path == "/" or path == "/index.html":
                return self._serve_index()
            if path.startswith("/static/"):
                return self._serve_static(path[len("/static/") :])
            if path == "/api/config":
                return self._serve_config()
            if path == "/api/sockets":
                return self._serve_sockets()
            if path == "/api/system":
                return self._proxy_json("GET", "/info")
            if path == "/api/system/df":
                return self._proxy_json("GET", "/system/df")
            if path == "/api/version":
                return self._proxy_json("GET", "/version")
            if path == "/api/containers":
                return self._proxy_json("GET", f"/containers/json?{query or 'all=1'}")
            if path == "/api/images":
                return self._proxy_json("GET", f"/images/json?{query}")
            if path == "/api/volumes":
                return self._proxy_json("GET", "/volumes")
            if path == "/api/networks":
                return self._proxy_json("GET", "/networks")
            if path == "/api/health":
                return self._serve_health()
            if path == "/api/host/disk":
                return self._serve_host_disk()
            if path.startswith("/api/containers/") and path.endswith("/logs"):
                cid = path.split("/")[3]
                return self._stream_logs(cid, query)
            if path.startswith("/api/containers/") and path.endswith("/stats"):
                cid = path.split("/")[3]
                return self._stream_stats(cid, query)
            if path.startswith("/api/containers/") and path.endswith("/inspect"):
                cid = path.split("/")[3]
                return self._proxy_json("GET", f"/containers/{cid}/json")
            if path.startswith("/api/images/") and path.endswith("/inspect"):
                iid = path.split("/")[3]
                return self._proxy_json("GET", f"/images/{iid}/json")
            self._send_json(404, {"error": "not found", "path": path})
        except BrokenPipeError:
            return
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def do_POST(self) -> None:  # noqa: N802
        if not self._auth_ok():
            return self._send_json(401, {"error": "unauthorized — network access requires a token"})
        path, query = self._split_path()
        try:
            if path.startswith("/api/containers/") and path.endswith("/start"):
                cid = path.split("/")[3]
                return self._proxy_action("POST", f"/containers/{cid}/start")
            if path.startswith("/api/containers/") and path.endswith("/stop"):
                cid = path.split("/")[3]
                return self._proxy_action("POST", f"/containers/{cid}/stop")
            if path.startswith("/api/containers/") and path.endswith("/restart"):
                cid = path.split("/")[3]
                return self._proxy_action("POST", f"/containers/{cid}/restart")
            if path.startswith("/api/containers/") and path.endswith("/pause"):
                cid = path.split("/")[3]
                return self._proxy_action("POST", f"/containers/{cid}/pause")
            if path.startswith("/api/containers/") and path.endswith("/unpause"):
                cid = path.split("/")[3]
                return self._proxy_action("POST", f"/containers/{cid}/unpause")
            if path == "/api/images/pull":
                return self._pull_image(query)
            if path == "/api/system/prune":
                return self._system_prune(query)
            if path == "/api/host/disk/snapshot":
                return self._serve_host_disk_snapshot()
            if path == "/api/socket/swap":
                return self._swap_socket()
            if path.startswith("/api/projects/") and path.endswith("/restart"):
                proj = urllib.parse.unquote(path.split("/")[3])
                return self._restart_project(proj)
            self._send_json(404, {"error": "not found", "path": path})
        except BrokenPipeError:
            return
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def do_DELETE(self) -> None:  # noqa: N802
        if not self._auth_ok():
            return self._send_json(401, {"error": "unauthorized — network access requires a token"})
        path, query = self._split_path()
        try:
            if path.startswith("/api/containers/"):
                cid = path.split("/")[3]
                qs = query or "force=1"
                return self._proxy_action("DELETE", f"/containers/{cid}?{qs}")
            if path.startswith("/api/images/"):
                iid = path.split("/")[3]
                return self._proxy_action("DELETE", f"/images/{iid}?{query}")
            if path.startswith("/api/volumes/"):
                name = path.split("/")[3]
                return self._proxy_action("DELETE", f"/volumes/{name}")
            self._send_json(404, {"error": "not found", "path": path})
        except BrokenPipeError:
            return
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    # ----- helpers -----

    def _split_path(self) -> Tuple[str, str]:
        parsed = urllib.parse.urlsplit(self.path)
        return parsed.path, parsed.query

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self) -> None:
        if not INDEX_HTML.exists():
            return self._send_json(500, {"error": "web/index.html missing"})
        body = INDEX_HTML.read_bytes()
        self._send_bytes(200, body, content_type="text/html; charset=utf-8")

    def _serve_static(self, relpath: str) -> None:
        # Resolve safely (no .. escapes)
        target = (STATIC_ROOT / relpath).resolve()
        try:
            target.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            return self._send_json(403, {"error": "forbidden"})
        if not target.is_file():
            return self._send_json(404, {"error": "not found"})
        ext = target.suffix.lower()
        content_type = {
            ".js": "application/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".ico": "image/x-icon",
            ".json": "application/json",
        }.get(ext, "application/octet-stream")
        self._send_bytes(200, target.read_bytes(), content_type=content_type)

    def _serve_health(self) -> None:
        status, _hdrs, body = docker_request(
            self.socket_path, "GET", "/version", timeout=3.0
        )
        if status >= 400:
            return self._send_json(
                503,
                {
                    "reachable": False,
                    "engine": self.engine,
                    "socket": self.socket_path,
                },
            )
        try:
            version = json.loads(body).get("Version")
        except json.JSONDecodeError:
            version = None
        self._send_json(
            200,
            {
                "reachable": True,
                "engine": self.engine,
                "socket": self.socket_path,
                "version": version,
            },
        )

    def _disk_block(self, path: str) -> dict | None:
        """Return {total, used, free, percent_used, path} or None if unreadable."""
        try:
            usage = shutil.disk_usage(path)
            total, used, free = usage.total, usage.used, usage.free
            return {
                "path": path,
                "total": total,
                "used": used,
                "free": free,
                "percent_used": round((used / total) * 100) if total > 0 else 0,
            }
        except Exception:  # noqa: BLE001
            return None

    def _docker_info_safe(self) -> dict:
        """Fetch Docker /info; empty dict on any failure."""
        try:
            status, _h, body = docker_request(self.socket_path, "GET", "/info", timeout=2.0)
            if status >= 400:
                return {}
            return json.loads(body)
        except Exception:  # noqa: BLE001
            return {}

    def _docker_layers_bytes_safe(self) -> int:
        """Sum of image LayersSize from /system/df; 0 on failure."""
        try:
            status, _h, body = docker_request(self.socket_path, "GET", "/system/df", timeout=3.0)
            if status >= 400:
                return 0
            df = json.loads(body)
            return int(df.get("LayersSize") or 0)
        except Exception:  # noqa: BLE001
            return 0

    def _serve_host_disk(self) -> None:
        try:
            host_block = self._disk_block("/")
            info = self._docker_info_safe()
            docker_root_path = info.get("DockerRootDir") or ""
            docker_root_block = None
            if docker_root_path and os.path.exists(docker_root_path):
                # Only readable when DockerRootDir is on the host (Linux native,
                # rootless, etc). On Colima/macOS this lives inside the VM —
                # path won't exist locally and we surface null.
                docker_root_block = self._disk_block(docker_root_path)
            self._send_json(
                200,
                {
                    "host": host_block,
                    "docker_root": docker_root_block,
                    "docker_layers_bytes": self._docker_layers_bytes_safe(),
                    # Legacy top-level fields — keep them so older clients don't break.
                    "total": host_block["total"] if host_block else 0,
                    "used": host_block["used"] if host_block else 0,
                    "free": host_block["free"] if host_block else 0,
                    "percent_used": host_block["percent_used"] if host_block else 0,
                },
            )
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def _serve_host_disk_snapshot(self) -> None:
        """Write a debug bundle (df + docker df + /info) to /tmp; return path.

        Plan 0005 Task G — snapshot-on-warn. The UI fires this once per session
        when the disk-warning threshold first trips, so a post-mortem has
        the exact state at the moment things went sideways.
        """
        try:
            ts = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
            out_path = os.path.join(tempfile.gettempdir(), f"dockyard-disk-warn-{ts}.txt")
            lines: list[str] = [
                f"# Dockyard disk-warn snapshot — {_dt.datetime.now().isoformat()}",
                f"# engine={self.engine} socket={self.socket_path}",
                "",
                "## df -h /",
            ]
            try:
                proc = subprocess.run(
                    ["df", "-h", "/"], capture_output=True, text=True, timeout=5
                )
                lines.append(proc.stdout.strip() or "(no output)")
                if proc.stderr.strip():
                    lines.append(f"stderr: {proc.stderr.strip()}")
            except Exception as e:  # noqa: BLE001
                lines.append(f"(df failed: {e})")

            info = self._docker_info_safe()
            lines += [
                "",
                "## docker /info (summary)",
                f"ServerVersion: {info.get('ServerVersion', '?')}",
                f"OperatingSystem: {info.get('OperatingSystem', '?')}",
                f"Driver: {info.get('Driver', '?')}",
                f"DockerRootDir: {info.get('DockerRootDir', '?')}",
                f"Containers: {info.get('Containers', '?')} "
                f"(running={info.get('ContainersRunning', '?')}, "
                f"stopped={info.get('ContainersStopped', '?')})",
                f"Images: {info.get('Images', '?')}",
            ]

            try:
                status, _h, body = docker_request(
                    self.socket_path, "GET", "/system/df", timeout=5.0
                )
                if status < 400:
                    df = json.loads(body)
                    lines += [
                        "",
                        "## docker /system/df",
                        f"LayersSize: {df.get('LayersSize', 0)}",
                    ]
                    imgs = sorted(
                        df.get("Images") or [], key=lambda i: i.get("Size", 0), reverse=True
                    )[:10]
                    if imgs:
                        lines.append("")
                        lines.append("Top 10 images by size:")
                        for img in imgs:
                            tags = ",".join(img.get("RepoTags") or []) or "<none>"
                            lines.append(f"  {img.get('Size', 0):>14}  {tags}")
                    vols = sorted(
                        df.get("Volumes") or [], key=lambda v: (v.get("UsageData") or {}).get("Size", 0), reverse=True
                    )[:10]
                    if vols:
                        lines.append("")
                        lines.append("Top 10 volumes by size:")
                        for vol in vols:
                            size = (vol.get("UsageData") or {}).get("Size", 0)
                            lines.append(f"  {size:>14}  {vol.get('Name', '?')}")
            except Exception as e:  # noqa: BLE001
                lines.append(f"\n(system/df failed: {e})")

            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            self._send_json(200, {"path": out_path, "bytes": os.path.getsize(out_path)})
        except Exception as e:  # noqa: BLE001
            self._send_json(500, {"error": str(e)})

    def _proxy_json(self, method: str, docker_path: str) -> None:
        status, _hdrs, body = docker_request(self.socket_path, method, docker_path)
        # Pass through whatever Docker returned (already JSON-shaped)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _proxy_action(self, method: str, docker_path: str) -> None:
        status, _hdrs, body = docker_request(self.socket_path, method, docker_path)
        if status >= 400:
            # Pass body through (Docker returns a JSON {"message": "..."} on error)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self._send_json(200, {"ok": True})

    def _stream_logs(self, container_id: str, query: str) -> None:
        # Default to last 200 lines, both streams, follow
        params = urllib.parse.parse_qs(query)
        tail = (params.get("tail") or ["200"])[0]
        follow = (params.get("follow") or ["1"])[0]
        docker_path = (
            f"/containers/{container_id}/logs"
            f"?stdout=1&stderr=1&follow={follow}&tail={tail}&timestamps=1"
        )
        conn, resp = docker_stream(self.socket_path, "GET", docker_path)
        try:
            if resp.status >= 400:
                self._send_bytes(resp.status, resp.read())
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            # Docker multiplexes stdout/stderr with an 8-byte header per frame
            # when the container has no TTY. We strip the header and emit raw
            # bytes — the UI doesn't need to distinguish streams in V0.
            while True:
                header = resp.read(8)
                if not header or len(header) < 8:
                    break
                # header[0] = stream type (1=stdout, 2=stderr), header[4:8] = size
                size = int.from_bytes(header[4:8], "big")
                if size == 0:
                    continue
                payload = resp.read(size)
                self._write_chunk(payload)
            self._write_chunk(b"")  # terminator
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    def _stream_stats(self, container_id: str, query: str) -> None:
        params = urllib.parse.parse_qs(query)
        one_shot = (params.get("stream") or ["1"])[0] == "0"
        docker_path = (
            f"/containers/{container_id}/stats"
            f"?stream={'0' if one_shot else '1'}"
        )
        if one_shot:
            return self._proxy_json("GET", docker_path)
        conn, resp = docker_stream(self.socket_path, "GET", docker_path)
        try:
            if resp.status >= 400:
                self._send_bytes(resp.status, resp.read())
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            buf = b""
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    if line.strip():
                        self._write_chunk(line + b"\n")
            self._write_chunk(b"")
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    def _write_chunk(self, data: bytes) -> None:
        # HTTP/1.1 chunked encoding
        self.wfile.write(b"%X\r\n" % len(data))
        self.wfile.write(data)
        self.wfile.write(b"\r\n")
        self.wfile.flush()

    def _pull_image(self, query: str) -> None:
        # POST /images/create?fromImage=nginx&tag=latest
        params = urllib.parse.parse_qs(query)
        from_image = (params.get("fromImage") or params.get("from") or [None])[0]
        tag = (params.get("tag") or ["latest"])[0]
        if not from_image:
            return self._send_json(400, {"error": "missing fromImage"})
        docker_path = (
            f"/images/create?fromImage={urllib.parse.quote(from_image)}"
            f"&tag={urllib.parse.quote(tag)}"
        )
        conn, resp = docker_stream(self.socket_path, "POST", docker_path)
        try:
            self.send_response(resp.status)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            while True:
                chunk = resp.read(4096)
                if not chunk:
                    break
                self._write_chunk(chunk)
            self._write_chunk(b"")
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass

    def _system_prune(self, query: str) -> None:
        # Convenience: prune containers + images + volumes + networks in one call
        # Each is a separate Docker endpoint.
        results = {}
        for kind, ep in [
            ("containers", "/containers/prune"),
            ("images", "/images/prune"),
            ("volumes", "/volumes/prune"),
            ("networks", "/networks/prune"),
        ]:
            status, _h, body = docker_request(self.socket_path, "POST", ep)
            try:
                results[kind] = (
                    json.loads(body) if status < 400 else {"error": body.decode()}
                )
            except json.JSONDecodeError:
                results[kind] = {"raw": body.decode("utf-8", errors="replace")}
        self._send_json(200, results)

    # ----- new endpoints (plan 0013) -----

    def _serve_config(self) -> None:
        """Return the runtime config — UI uses this for branding + theme defaults."""
        from dockyard.lib.socket import load_config  # local import to avoid cycle
        cfg = dict(load_config())
        cfg["_runtime"] = {
            "engine": self.engine,
            "socket": self.socket_path,
        }
        self._send_json(200, cfg)

    def _serve_sockets(self) -> None:
        """Enumerate all detected Docker sockets so the UI can offer a swapper."""
        from dockyard.lib.socket import detect_socket, _candidates  # type: ignore
        # Walk every candidate, not just the first that's reachable
        home_env = {"HOME": os.path.expanduser("~")}
        all_sockets = []
        seen = set()
        for cand in _candidates(Path(os.path.expanduser("~")), dict(os.environ)):
            if cand.path in seen:
                continue
            seen.add(cand.path)
            # Re-stat to confirm reachability
            try:
                exists = os.path.exists(cand.path)
            except OSError:
                exists = False
            all_sockets.append(
                {
                    "path": cand.path,
                    "engine": cand.engine,
                    "profile": cand.profile,
                    "reachable": exists,
                    "active": cand.path == self.socket_path,
                }
            )
        self._send_json(200, all_sockets)

    def _swap_socket(self) -> None:
        """Switch the active Docker socket at runtime.

        POST /api/socket/swap   body={"path": "/Users/.../docker.sock"}
        """
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return self._send_json(400, {"error": "invalid JSON body"})
        new_path = (body.get("path") or "").strip()
        if not new_path:
            return self._send_json(400, {"error": "missing 'path'"})
        if not os.path.exists(new_path):
            return self._send_json(404, {"error": f"socket not found: {new_path}"})
        # Probe before swapping
        try:
            status, _h, _b = docker_request(new_path, "GET", "/_ping", timeout=3)
            if status != 200:
                return self._send_json(
                    503, {"error": f"socket reachable but /_ping returned {status}"}
                )
        except Exception as e:  # noqa: BLE001
            return self._send_json(
                503, {"error": f"socket unreachable: {e}"}
            )
        # Best-effort engine label
        engine = "custom"
        for keyword, label in [
            ("colima", "colima"),
            ("orbstack", "orbstack"),
            ("docker.docker", "docker-desktop"),
            ("/var/run/docker.sock", "native"),
        ]:
            if keyword in new_path:
                engine = label
                break
        DockyardHandler.socket_path = new_path
        DockyardHandler.engine = engine
        self._send_json(
            200, {"ok": True, "engine": engine, "socket": new_path}
        )

    def _restart_project(self, project: str) -> None:
        """Restart every container whose com.docker.compose.project label matches."""
        # Find containers
        filt = json.dumps({"label": [f"com.docker.compose.project={project}"]})
        qs = f"all=1&filters={urllib.parse.quote(filt)}"
        status, _h, body = docker_request(
            self.socket_path, "GET", f"/containers/json?{qs}"
        )
        if status >= 400:
            return self._send_json(status, {"error": body.decode("utf-8", errors="replace")})
        try:
            containers = json.loads(body)
        except json.JSONDecodeError:
            return self._send_json(500, {"error": "could not parse container list"})
        if not containers:
            return self._send_json(
                404, {"error": f"no containers found for project {project!r}"}
            )
        results = []
        for c in containers:
            cid = c["Id"]
            name = (c.get("Names") or ["?"])[0].lstrip("/")
            try:
                s, _h2, b2 = docker_request(
                    self.socket_path, "POST", f"/containers/{cid}/restart", timeout=30
                )
                results.append(
                    {"id": cid[:12], "name": name, "ok": s < 400, "status": s}
                )
            except Exception as e:  # noqa: BLE001
                results.append({"id": cid[:12], "name": name, "ok": False, "error": str(e)})
        self._send_json(200, {"project": project, "containers": results})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def _lan_ip() -> Optional[str]:
    """Best-effort detection of the LAN-facing IP without resolving DNS."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 8.8.8.8 is just a routing hint; nothing is actually sent.
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])
    except Exception:  # noqa: BLE001
        return None
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:  # noqa: BLE001
                pass


def _ascii_banner(
    name: str,
    url: str,
    engine: str,
    version: Optional[str],
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> str:
    engine_label = f"{engine}" + (f" {version}" if version else "")
    network_line = ""
    if host == "0.0.0.0" and port is not None:
        ip = _lan_ip()
        if ip:
            network_line = f"  Network   http://{ip}:{port}  (reachable on your Wi-Fi)\n"
    mode = (
        "Localhost + Wi-Fi · press Ctrl+C to stop"
        if host == "0.0.0.0"
        else "Localhost · press Ctrl+C to stop"
    )
    return (
        "\n"
        f"  🚢  {name}\n\n"
        f"  URL       {url}\n"
        f"{network_line}"
        f"  Engine    {engine_label}\n"
        f"  Mode      {mode}\n\n"
    )


def _parse_args(argv: list) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Dockyard — Docker manager UI")
    p.add_argument("--port", type=int, default=None, help="override config port")
    p.add_argument("--host", default="127.0.0.1", help="bind address")
    p.add_argument("--no-open", action="store_true", help="don't open browser")
    return p.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    config = load_config()
    port = args.port or int(os.environ.get("DOCKYARD_PORT", config.get("port", 4321)))

    try:
        socket_path, engine = resolve_socket(config)
    except RuntimeError as e:
        sys.stderr.write(f"[dockyard] {e}\n")
        return 2

    DockyardHandler.socket_path = socket_path
    DockyardHandler.engine = engine
    DockyardHandler.config = config

    httpd = ThreadingHTTPServer((args.host, port), DockyardHandler)
    url = f"http://{args.host}:{port}"

    # Print banner immediately so the user knows the port is bound,
    # then probe the engine asynchronously for the version pill.
    sys.stdout.write(
        _ascii_banner(
            config.get("branding", {}).get("name", "Dockyard"),
            url,
            engine,
            None,  # version filled in async
            host=args.host,
            port=port,
        )
    )
    sys.stdout.flush()

    def _probe_version() -> None:
        try:
            status, _h, body = docker_request(
                socket_path, "GET", "/version", timeout=3
            )
            if status < 400:
                v = json.loads(body).get("Version")
                if v:
                    sys.stdout.write(f"  Engine v {v} reachable.\n")
                    sys.stdout.flush()
            else:
                sys.stdout.write(
                    f"  ⚠️  Engine returned {status} on /version — "
                    "UI works, actions will fail until engine is restarted.\n"
                )
                sys.stdout.flush()
        except Exception as e:  # noqa: BLE001
            sys.stdout.write(
                f"  ⚠️  Engine not reachable ({e}). "
                "UI loads but data calls will time out. Try `make doctor`.\n"
            )
            sys.stdout.flush()

    threading.Thread(target=_probe_version, daemon=True).start()

    if not args.no_open:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\n[dockyard] stopping…\n")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
