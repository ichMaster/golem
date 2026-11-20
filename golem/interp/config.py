"""The interpreter's settings, read from the environment.

``load_interp_settings`` is a pure function over a mapping, so tests pass a plain dict.
"""

from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_LUA_MAX_MEMORY = 64 * 1024 * 1024
DEFAULT_HOOK_EVERY = 1000


class InterpConfigError(ValueError):
    """A setting that the interpreter refuses to run with."""


@dataclass(frozen=True)
class InterpSettings:
    """The Lua memory cap per run, in bytes, and the instructions between two count-hook calls."""

    lua_max_memory: int = DEFAULT_LUA_MAX_MEMORY
    hook_every: int = DEFAULT_HOOK_EVERY


def load_interp_settings(environ: Mapping[str, str]) -> InterpSettings:
    return InterpSettings(
        lua_max_memory=_positive_int(environ, "LUA_MAX_MEMORY", DEFAULT_LUA_MAX_MEMORY),
        hook_every=_positive_int(environ, "HOOK_EVERY", DEFAULT_HOOK_EVERY),
    )


def _positive_int(environ: Mapping[str, str], name: str, default: int) -> int:
    text = environ.get(name) or str(default)
    try:
        value = int(text)
    except ValueError:
        raise InterpConfigError(f"{name}={text!r} is not an integer") from None
    if value <= 0:
        raise InterpConfigError(f"{name}={value} must be positive")
    return value
