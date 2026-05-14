"""Docker socket auto-detection.

Probes for the Docker Engine API socket in this order:

1. ``DOCKER_HOST`` environment variable (unix:// or tcp://)
2. ``~/.colima/default/docker.sock``
3. ``~/.colima/<profile>/docker.sock`` for each profile dir
4. ``~/.orbstack/run/docker.sock``
5. ``~/Library/Containers/com.docker.docker/Data/docker.raw.sock``
6. ``/var/run/docker.sock`` (Linux native)

Returns a ``(path, engine_type)`` tuple where engine_type is one of:
``colima``, ``orbstack``, ``docker-desktop``, ``native``, ``env``.

This module is stdlib-only (Python 3.10+). It does NOT import third-party
packages; it works on a stock Python install.

CLI usage::

    python -m dockyard.lib.socket detect

Library usage::

    from dockyard.lib.socket import detect_socket, SocketInfo
    info = detect_socket()
    print(info.path, info.engine)
"""

from __future__ import annotations

import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True)
class SocketInfo:
    """Result of socket detection."""

    path: str
    engine: str  # colima | orbstack | docker-desktop | native | env
    profile: Optional[str] = None  # Colima profile name (default: "default")

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.profile:
            return f"{self.path} (engine: {self.engine}, profile: {self.profile})"
        return f"{self.path} (engine: {self.engine})"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_socket(
    *,
    home: Optional[Path] = None,
    env: Optional[dict] = None,
) -> Optional[SocketInfo]:
    """Return the first reachable Docker socket, or None if nothing works.

    Parameters
    ----------
    home : Path, optional
        Override the home directory for testing.
    env : dict, optional
        Override the environment for testing. Defaults to ``os.environ``.
    """
    home = home or Path(os.path.expanduser("~"))
    env = env if env is not None else dict(os.environ)

    for candidate in _candidates(home, env):
        if _is_socket(candidate.path):
            return candidate
    return None


def _candidates(home: Path, env: dict) -> Iterable[SocketInfo]:
    """Yield candidate sockets in priority order."""
    # 1. DOCKER_HOST env var (unix:// only — tcp:// not supported here)
    docker_host = env.get("DOCKER_HOST", "").strip()
    if docker_host.startswith("unix://"):
        yield SocketInfo(path=docker_host[len("unix://") :], engine="env")
    elif docker_host:
        # We don't support tcp:// or ssh:// in V0, but report it so the
        # caller can decide whether to fall through.
        # Tracked: PRD § "Out of scope (V0)" — remote daemons land in V1.
        pass

    # 2. Colima default
    yield SocketInfo(
        path=str(home / ".colima" / "default" / "docker.sock"),
        engine="colima",
        profile="default",
    )

    # 3. Colima other profiles (iterate ~/.colima/* excluding "default")
    colima_root = home / ".colima"
    if colima_root.is_dir():
        for child in sorted(colima_root.iterdir()):
            if not child.is_dir():
                continue
            if child.name == "default":
                continue  # already covered
            sock = child / "docker.sock"
            yield SocketInfo(path=str(sock), engine="colima", profile=child.name)

    # 4. OrbStack
    yield SocketInfo(
        path=str(home / ".orbstack" / "run" / "docker.sock"),
        engine="orbstack",
    )

    # 5. Docker Desktop (macOS)
    yield SocketInfo(
        path=str(
            home
            / "Library"
            / "Containers"
            / "com.docker.docker"
            / "Data"
            / "docker.raw.sock"
        ),
        engine="docker-desktop",
    )

    # 6. Linux / native (also works under WSL2 when the daemon is on the host)
    yield SocketInfo(path="/var/run/docker.sock", engine="native")


def _is_socket(path: str) -> bool:
    """Return True if `path` is a Unix domain socket we can stat()."""
    try:
        st = os.stat(path)
    except (FileNotFoundError, PermissionError, OSError):
        return False
    return stat.S_ISSOCK(st.st_mode)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load dockyard.config.json or return defaults.

    Default config matches the schema in the Dockyard PRD § "Configuration".
    """
    defaults = {
        "port": 4321,
        "socket": "auto",
        "auth": {"mode": "none"},
        "branding": {"name": "Dockyard", "accent": "#0E7C66"},
    }
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "dockyard.config.json"
    if not config_path.exists():
        return defaults
    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return defaults
    # Shallow merge over defaults (one level deep for "auth" + "branding")
    merged = {**defaults, **loaded}
    for key in ("auth", "branding"):
        if key in loaded and isinstance(loaded[key], dict):
            merged[key] = {**defaults[key], **loaded[key]}
    return merged


def resolve_socket(config: Optional[dict] = None) -> Tuple[str, str]:
    """Resolve the socket path from config, falling back to auto-detect.

    Returns ``(path, engine)``. Raises ``RuntimeError`` if no socket
    can be found.
    """
    cfg = config or load_config()
    setting = (cfg.get("socket") or "auto").strip()
    if setting and setting != "auto":
        # User pinned a specific path
        engine = "env" if setting.startswith("/var/run/") else "custom"
        if not _is_socket(setting):
            raise RuntimeError(
                f"Configured Docker socket not found or not a socket: {setting}"
            )
        return setting, engine
    info = detect_socket()
    if info is None:
        raise RuntimeError(
            "No Docker socket detected. Is Colima running? Try: "
            "`colima start` or set DOCKER_HOST in your environment."
        )
    return info.path, info.engine


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _main(argv: list) -> int:
    if len(argv) >= 2 and argv[1] == "detect":
        info = detect_socket()
        if info is None:
            print("No Docker socket found.", file=sys.stderr)
            return 1
        print(str(info))
        return 0
    if len(argv) >= 2 and argv[1] == "config":
        print(json.dumps(load_config(), indent=2))
        return 0
    print("Usage: python -m dockyard.lib.socket {detect|config}", file=sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main(sys.argv))
