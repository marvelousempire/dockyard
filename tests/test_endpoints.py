"""Integration tests for the Dockyard server endpoints.

Requires:
  - Python 3.9+
  - A reachable Docker socket (Colima recommended, or any of the
    engines socket.py probes)

Spins up the server in a thread on an ephemeral port, hits each
endpoint, asserts shape. Skips automatically if no engine is
reachable so tests stay green on machines without Docker.
"""

from __future__ import annotations

import json
import socket as socket_module
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from dockyard.lib.socket import detect_socket  # noqa: E402
from dockyard.server import (  # noqa: E402
    DockyardHandler,
    docker_request,
)
from http.server import ThreadingHTTPServer  # noqa: E402


def _free_port() -> int:
    with socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _docker_ok(socket_path: str) -> bool:
    try:
        status, _, _ = docker_request(socket_path, "GET", "/_ping", timeout=2)
        return status == 200
    except Exception:  # noqa: BLE001
        return False


def _start_server(socket_path: str, engine: str) -> tuple[ThreadingHTTPServer, str]:
    """Boot the server on a free port. Returns (server, base_url)."""
    DockyardHandler.socket_path = socket_path
    DockyardHandler.engine = engine
    DockyardHandler.config = {}
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), DockyardHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(0.1)
    return server, f"http://127.0.0.1:{port}"


class TestServerOnly(unittest.TestCase):
    """Server-side endpoints that DON'T require a reachable Docker engine.

    Plan 0013 added /api/config, /api/sockets, /api/socket/swap, static
    favicon — all served by Dockyard itself. These should pass even
    when Docker is dead.
    """

    server: "ThreadingHTTPServer | None" = None
    base: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        # Use a sentinel path; these tests don't talk to Docker
        cls.server, cls.base = _start_server(
            "/var/run/nonexistent-docker.sock", "test"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server is not None:
            cls.server.shutdown()
            cls.server.server_close()

    def _get_json(self, path: str, timeout: float = 5.0):
        with urllib.request.urlopen(self.base + path, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())

    def test_config_endpoint(self) -> None:
        """Plan 0013 Track G1 — /api/config returns merged config + runtime."""
        status, body = self._get_json("/api/config")
        self.assertEqual(status, 200)
        self.assertEqual(body["port"], 4321)
        self.assertIn("branding", body)
        self.assertIn("accent", body["branding"])
        self.assertIn("_runtime", body)
        self.assertIn("engine", body["_runtime"])

    def test_sockets_endpoint(self) -> None:
        """Plan 0013 Track E-G — /api/sockets enumerates engines."""
        status, body = self._get_json("/api/sockets")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        engines = {s["engine"] for s in body}
        self.assertTrue(
            {"colima", "orbstack", "docker-desktop", "native"} & engines
        )

    def test_favicon_served(self) -> None:
        """Plan 0013 Track G5 — static SVG favicon."""
        with urllib.request.urlopen(self.base + "/static/favicon.svg", timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("image/svg", resp.getheader("Content-Type") or "")

    def test_socket_swap_validates(self) -> None:
        """Plan 0013 Track E-G — swap rejects nonexistent path."""
        req = urllib.request.Request(
            self.base + "/api/socket/swap",
            data=json.dumps({"path": "/nonexistent.sock"}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            self.fail("expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_index_html_served(self) -> None:
        with urllib.request.urlopen(self.base + "/", timeout=5) as resp:
            body = resp.read()
        self.assertEqual(resp.status, 200)
        self.assertTrue(body.startswith(b"<!doctype html>") or body.startswith(b"<!DOCTYPE html>"))


class TestEndpoints(unittest.TestCase):
    """Endpoints that DO require a reachable Docker engine."""

    server: "ThreadingHTTPServer | None" = None
    base: str = ""
    skip_reason: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        info = detect_socket()
        if info is None:
            cls.skip_reason = "no docker socket detected"
            return
        if not _docker_ok(info.path):
            cls.skip_reason = f"docker engine unreachable via {info.path}"
            return
        cls.server, cls.base = _start_server(info.path, info.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server is not None:
            cls.server.shutdown()
            cls.server.server_close()

    def setUp(self) -> None:
        if self.skip_reason:
            self.skipTest(self.skip_reason)

    def _get_json(self, path: str, timeout: float = 5.0):
        with urllib.request.urlopen(self.base + path, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())

    def test_health_returns_engine(self) -> None:
        status, body = self._get_json("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["reachable"])
        self.assertIn("engine", body)
        self.assertIn("version", body)

    def test_containers_returns_list(self) -> None:
        status, body = self._get_json("/api/containers?all=1")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        # If any container is running, sanity-check shape
        if body:
            c = body[0]
            self.assertIn("Id", c)
            self.assertIn("Image", c)

    def test_images_returns_list(self) -> None:
        status, body = self._get_json("/api/images")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)

    def test_networks_returns_list(self) -> None:
        status, body = self._get_json("/api/networks")
        self.assertEqual(status, 200)
        self.assertIsInstance(body, list)
        names = {n.get("Name") for n in body}
        # The default bridge network is always there
        self.assertTrue("bridge" in names or "host" in names)

    def test_system_returns_info(self) -> None:
        status, body = self._get_json("/api/system")
        self.assertEqual(status, 200)
        self.assertIn("ServerVersion", body)
        self.assertIn("OperatingSystem", body)

    def test_unknown_route_404(self) -> None:
        try:
            self._get_json("/api/nope")
            self.fail("expected 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)

    def test_index_html_served(self) -> None:
        with urllib.request.urlopen(self.base + "/", timeout=5) as resp:
            body = resp.read()
        self.assertEqual(resp.status, 200)
        self.assertTrue(body.startswith(b"<!doctype html>") or body.startswith(b"<!DOCTYPE html>"))

if __name__ == "__main__":
    unittest.main()
