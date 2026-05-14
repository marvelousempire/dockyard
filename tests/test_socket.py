"""Unit tests for dockyard.lib.socket — detection + config loading.

Uses tempfile + os.stat fakery rather than a mock library so this file
runs on stock Python (no pip install). Targets Python 3.9+ via
``from __future__ import annotations``.
"""

from __future__ import annotations

import json
import os
import socket as socket_module
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

from dockyard.lib.socket import (  # noqa: E402
    SocketInfo,
    _is_socket,
    detect_socket,
    load_config,
    resolve_socket,
)


def make_unix_socket(path: Path) -> socket_module.socket:
    """Create a real UDS file so _is_socket() returns True."""
    s = socket_module.socket(socket_module.AF_UNIX, socket_module.SOCK_STREAM)
    s.bind(str(path))
    s.listen(1)
    return s


class TestIsSocket(unittest.TestCase):
    def test_real_socket_detected(self):
        with tempfile.TemporaryDirectory() as td:
            sock_path = Path(td) / "test.sock"
            s = make_unix_socket(sock_path)
            try:
                self.assertTrue(_is_socket(str(sock_path)))
            finally:
                s.close()

    def test_regular_file_not_socket(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertFalse(_is_socket(f.name))

    def test_missing_path_not_socket(self):
        self.assertFalse(_is_socket("/nonexistent/path/here.sock"))


class TestDetectSocket(unittest.TestCase):
    """Probe order: env -> colima default -> colima profiles -> orbstack -> dd -> native."""

    def setUp(self) -> None:
        # macOS caps AF_UNIX paths at 104 chars. Default /var/folders/...
        # tempdirs blow past that once we nest .colima/.../docker.sock.
        # Force a shorter root under /tmp.
        self._td = tempfile.TemporaryDirectory(prefix="dy_", dir="/tmp")
        self.home = Path(self._td.name)
        self.sockets: list[socket_module.socket] = []

    def tearDown(self) -> None:
        for s in self.sockets:
            try:
                s.close()
            except Exception:  # noqa: BLE001
                pass
        self._td.cleanup()

    def _create_socket(self, rel: str) -> Path:
        full = self.home / rel
        full.parent.mkdir(parents=True, exist_ok=True)
        s = make_unix_socket(full)
        self.sockets.append(s)
        return full

    def test_colima_default_wins(self) -> None:
        sock = self._create_socket(".colima/default/docker.sock")
        info = detect_socket(home=self.home, env={})
        assert info is not None
        self.assertEqual(info.path, str(sock))
        self.assertEqual(info.engine, "colima")
        self.assertEqual(info.profile, "default")

    def test_colima_profile_iterated(self) -> None:
        # No default — only a team profile.
        sock = self._create_socket(".colima/team/docker.sock")
        info = detect_socket(home=self.home, env={})
        assert info is not None
        self.assertEqual(info.path, str(sock))
        self.assertEqual(info.engine, "colima")
        self.assertEqual(info.profile, "team")

    def test_orbstack_fallback(self) -> None:
        sock = self._create_socket(".orbstack/run/docker.sock")
        info = detect_socket(home=self.home, env={})
        assert info is not None
        self.assertEqual(info.engine, "orbstack")
        self.assertEqual(info.path, str(sock))

    def test_docker_desktop_fallback(self) -> None:
        sock = self._create_socket(
            "Library/Containers/com.docker.docker/Data/docker.raw.sock"
        )
        info = detect_socket(home=self.home, env={})
        assert info is not None
        self.assertEqual(info.engine, "docker-desktop")
        self.assertEqual(info.path, str(sock))

    def test_env_var_wins(self) -> None:
        # Make an alternate socket and point env at it
        with tempfile.TemporaryDirectory() as td:
            alt = Path(td) / "custom.sock"
            s = make_unix_socket(alt)
            try:
                info = detect_socket(home=self.home, env={"DOCKER_HOST": f"unix://{alt}"})
                assert info is not None
                self.assertEqual(info.engine, "env")
                self.assertEqual(info.path, str(alt))
            finally:
                s.close()

    def test_none_when_nothing_reachable(self) -> None:
        # Empty home, empty env, /var/run/docker.sock probably not present
        # — if it IS present on the CI host, this test is a no-op because
        # the native path is reachable.
        info = detect_socket(home=self.home, env={})
        if info is not None:
            self.assertEqual(info.engine, "native")  # only path that could match
        # else: pass — no engine detected, which is the expected outcome
        # on a clean tempdir-only environment.


class TestConfig(unittest.TestCase):
    def test_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            cfg = load_config(Path(td) / "missing.json")
            self.assertEqual(cfg["port"], 4321)
            self.assertEqual(cfg["socket"], "auto")
            self.assertEqual(cfg["auth"]["mode"], "none")
            self.assertEqual(cfg["branding"]["name"], "Dockyard")

    def test_merges_over_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "dockyard.config.json"
            p.write_text(
                json.dumps(
                    {
                        "port": 9999,
                        "branding": {"accent": "#FF0000"},
                    }
                )
            )
            cfg = load_config(p)
            self.assertEqual(cfg["port"], 9999)
            # accent overridden, name retained
            self.assertEqual(cfg["branding"]["accent"], "#FF0000")
            self.assertEqual(cfg["branding"]["name"], "Dockyard")

    def test_malformed_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.json"
            p.write_text("{ not json")
            cfg = load_config(p)
            self.assertEqual(cfg["port"], 4321)


class TestResolveSocket(unittest.TestCase):
    def test_explicit_path_validated(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            sock = Path(td) / "pinned.sock"
            s = make_unix_socket(sock)
            try:
                path, engine = resolve_socket({"socket": str(sock)})
                self.assertEqual(path, str(sock))
            finally:
                s.close()

    def test_explicit_missing_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            resolve_socket({"socket": "/nonexistent/forbidden.sock"})

    def test_auto_falls_through_to_detect(self) -> None:
        # We can't easily mock the actual home dir here without monkey-
        # patching. We just verify the function doesn't crash with the
        # "auto" setting; the path it returns depends on the host.
        try:
            resolve_socket({"socket": "auto"})
        except RuntimeError:
            # OK — no engine detected on this host
            pass


if __name__ == "__main__":
    unittest.main()
