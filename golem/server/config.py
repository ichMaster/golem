"""The server's settings, read from the environment (``golem-server`` loads ``.env`` first).

``load_settings`` is a pure function over a mapping, so tests pass a plain dict.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8700
DEFAULT_LEVELS_DIR = "levels"
DEFAULT_LOG_DIR = "data/logs"
DEFAULT_GAME_FILE = "data/human-game.json"
DEFAULT_PROGRAMS_DIR = "programs"


class ConfigError(ValueError):
    """A setting that the server refuses to start with."""


@dataclass(frozen=True)
class Settings:
    """Where the server listens, where the levels are, where it logs, and where it saves the game.

    ``game_file`` is where the human game is saved after every change and restored from at start;
    ``None`` turns saving off. ``programs_dir`` is the folder of programs the screen runs (v2.4);
    ``None`` lists none.
    """

    host: str
    port: int
    levels_dir: Path
    log_dir: Path
    game_file: Path | None = None
    programs_dir: Path | None = None


def load_settings(environ: Mapping[str, str]) -> Settings:
    """Build the settings; relative paths are resolved once, against the working directory."""
    host = environ.get("GOLEM_HOST") or DEFAULT_HOST
    if host not in LOOPBACK_HOSTS:
        raise ConfigError(
            f"GOLEM_HOST={host!r} is not a loopback address; the server listens only on "
            "127.0.0.1, localhost or ::1"
        )

    port_text = environ.get("GOLEM_PORT") or str(DEFAULT_PORT)
    try:
        port = int(port_text)
    except ValueError:
        raise ConfigError(f"GOLEM_PORT={port_text!r} is not a port number") from None
    if not 1 <= port <= 65535:
        raise ConfigError(f"GOLEM_PORT={port} is outside 1..65535")

    levels_dir = Path(environ.get("GOLEM_LEVELS_DIR") or DEFAULT_LEVELS_DIR).resolve()
    log_dir = Path(DEFAULT_LOG_DIR).resolve()
    game_file = Path(DEFAULT_GAME_FILE).resolve()
    programs_dir = Path(environ.get("GOLEM_PROGRAMS_DIR") or DEFAULT_PROGRAMS_DIR).resolve()
    return Settings(
        host=host, port=port, levels_dir=levels_dir, log_dir=log_dir, game_file=game_file,
        programs_dir=programs_dir,
    )
