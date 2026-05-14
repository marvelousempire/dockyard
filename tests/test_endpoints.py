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


class TestEndpoints(unittest.TestCase):
    """Boot the server once for the whole class."""

    server: "ThreadingHTTPServer | None" = None
    thread: "threading.Thread | None" = None
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

        DockyardHandler.socket_path = info.path
        DockyardHandler.engine = info.engine
        DockyardHandler.config = {}

        port = _free_port()
        cls.server = ThreadingHTTPServer(("127.0.0.1", port), DockyardHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{port}"
        # Give the server a beat
        time.sleep(0.1)

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
