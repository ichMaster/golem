"""The Golem server: ``create_app()`` and the ``golem-server`` command.

Routes stay thin: they parse input, call the core, and shape the JSON. Every error response is
``{"error": "<code>", "detail": "<text>"}`` (ARCHITECTURE.md §HTTP API).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

import golem
from golem.core.level import LevelError
from golem.core.levels import BudgetsError, budget_for, list_levels, load_budgets, load_level
from golem.interp.run import run_with_frames
from golem.server.config import ConfigError, Settings, load_settings
from golem.server.programs import BadProgram, UnknownProgram, list_programs, read_program
from golem.server.ws import install_ws

LOG = logging.getLogger("golem")
LOG_FILE = "server.log"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 3
HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}
# Found through the package, so the server serves the same page from any working directory.
SCREEN_DIR = Path(golem.__file__).resolve().parent / "screen"


class StartupError(RuntimeError):
    """The server cannot start with these settings."""


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app; refuse to start without a training set and a valid budgets.toml."""
    settings = settings or load_settings(os.environ)
    _check_levels(settings.levels_dir)
    _setup_logging(settings.log_dir)

    app = FastAPI(title="Golem", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    _install_error_handlers(app)
    _install_level_routes(app, settings.levels_dir)
    _install_screen_routes(app)
    _install_program_routes(app, settings)
    install_ws(app, settings.levels_dir, settings.port, settings.game_file)
    return app


def error_response(status: int, code: str, detail: str) -> JSONResponse:
    """The one error body: ``{"error", "detail"}``."""
    return JSONResponse({"error": code, "detail": detail}, status_code=status)


def _check_levels(levels_dir: Path) -> None:
    if not (levels_dir / "training").is_dir():
        raise StartupError(
            f"{levels_dir} has no training/ directory; set GOLEM_LEVELS_DIR to the levels root"
        )
    try:
        load_budgets(levels_dir)
    except (BudgetsError, OSError) as error:
        raise StartupError(f"{levels_dir / 'budgets.toml'}: {error}") from error


def _setup_logging(log_dir: Path) -> None:
    """Log to <log_dir>/server.log (1 MB x 3) and the console; safe to call more than once."""
    log_dir.mkdir(parents=True, exist_ok=True)
    for handler in list(LOG.handlers):
        if getattr(handler, "golem_handler", False):
            LOG.removeHandler(handler)
            handler.close()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(
        log_dir / LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUPS, encoding="utf-8"
    )
    for handler in (file_handler, logging.StreamHandler()):
        handler.setFormatter(formatter)
        handler.golem_handler = True
        LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)
    LOG.propagate = False


def _install_level_routes(app: FastAPI, levels_dir: Path) -> None:
    @app.get("/api/levels")
    def training_levels():
        """The training levels with their tier, size and budgets; never a map, never a hidden id."""
        try:
            budgets = load_budgets(levels_dir)
        except (BudgetsError, OSError) as error:
            LOG.error("budgets.toml does not load: %s", error)
            return error_response(500, "budgets_error", str(error))
        entries = []
        for level_id in list_levels("training", levels_dir):
            try:
                level = load_level(level_id, levels_dir)
                budget = budget_for(level_id, budgets)
            except (LevelError, BudgetsError) as error:
                LOG.error("training level %s does not load: %s", level_id, error)
                return error_response(500, "level_error", str(error))
            entries.append({
                "id": level_id,
                "tier": level_id.split("/")[1],
                "width": level.width,
                "height": level.height,
                "budget": {"steps": budget.steps, "instructions": budget.instructions},
            })
        return {"levels": entries}


def _install_program_routes(app: FastAPI, settings: Settings) -> None:
    """The programs the screen lists, shows and runs (v2.4): by name, from one folder only.

    The routes are plain ``def`` functions, so FastAPI runs them in its thread pool and a run never
    blocks the event loop that carries the human game.
    """
    folder, levels_dir = settings.programs_dir, settings.levels_dir

    def source_of(name: object) -> str | JSONResponse:
        try:
            return read_program(folder, name)
        except UnknownProgram:
            return error_response(404, "not_found", "unknown program")
        except BadProgram as error:
            return error_response(422, "bad_program", str(error))

    @app.get("/api/programs")
    def programs():
        return {"programs": list_programs(folder)}

    @app.get("/api/programs/{name}")
    def program(name: str):
        source = source_of(name)
        if isinstance(source, JSONResponse):
            return source
        return {"name": name, "source": source}

    @app.post("/api/programs/{name}/run")
    def run(name: str, body: Annotated[dict | None, Body()] = None):
        fields = body if isinstance(body, dict) else {}
        source = source_of(name)
        if isinstance(source, JSONResponse):
            return source
        # The program swapped in when the first one gives up or returns (v2.5); absent or null means
        # no swap.
        second_name = fields.get("swap")
        second = None
        if second_name is not None:
            second = source_of(second_name)
            if isinstance(second, JSONResponse):
                return second
        level_id = fields.get("level")
        # Training ids only; a hidden, unknown, missing or non-string id gets the same answer.
        if not isinstance(level_id, str) or level_id not in list_levels("training", levels_dir):
            return error_response(404, "unknown_level", "unknown level")
        try:
            level = load_level(level_id, levels_dir)
            budget = budget_for(level_id, load_budgets(levels_dir))
        except (LevelError, BudgetsError, OSError) as error:
            LOG.error("training level %s does not load: %s", level_id, error)
            return error_response(500, "level_error", str(error))
        report, frames = run_with_frames(level, budget, source, settings.interp, second=second)
        swapped = f" with {second_name} swapped in" if second is not None else ""
        LOG.info("ran %s%s on %s: %s %s", name, swapped, level_id, report["status"],
                 report["reason"])
        return {"report": report, "frames": frames}


class _ScreenFiles(StaticFiles):
    """The screen's files, each sent with ``Cache-Control: no-cache``.

    The browser then revalidates every load (a cheap ``304`` when nothing changed), so a changed
    ``screen.js`` is never run from a stale cache (v2.2 code review #1).
    """

    def file_response(self, full_path, stat_result, scope, status_code: int = 200) -> Response:
        response = super().file_response(full_path, stat_result, scope, status_code)
        response.headers["Cache-Control"] = "no-cache"
        return response


def _install_screen_routes(app: FastAPI) -> None:
    """``GET /`` is the page; ``/screen/…`` serves the files of ``golem/screen/`` and nothing else.

    ``StaticFiles`` refuses a path that resolves outside its directory, lists no directory, and
    raises the 404 that the app's handler turns into ``{"error", "detail"}``.
    """
    files = _ScreenFiles(directory=SCREEN_DIR)

    @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
    async def screen_page(request: Request) -> Response:
        return await files.get_response("index.html", request.scope)

    app.mount("/screen", files, name="screen")


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        code = HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(422, "bad_request", "the request does not match the route")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        LOG.exception("internal error on %s %s", request.method, request.url.path)
        return error_response(500, "internal", "internal server error")


def main() -> None:
    """``uv run golem-server``: read .env, check the settings, and serve on loopback."""
    import uvicorn
    from dotenv import load_dotenv

    env_file = Path.cwd() / ".env"  # this directory only, never a parent's .env
    if env_file.is_file():
        load_dotenv(env_file, override=False)
    try:
        settings = load_settings(os.environ)
        app = create_app(settings)
    except (ConfigError, StartupError) as error:
        print(f"golem-server: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    LOG.info("listening on http://%s:%d", settings.host, settings.port)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
