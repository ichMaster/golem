"""The Golem server: ``create_app()`` and the ``golem-server`` command.

Routes stay thin: they parse input, call the core, and shape the JSON. Every error response is
``{"error": "<code>", "detail": "<text>"}`` (ARCHITECTURE.md §HTTP API).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from golem.core.level import LevelError
from golem.core.levels import BudgetsError, budget_for, list_levels, load_budgets, load_level
from golem.server.config import ConfigError, Settings, load_settings
from golem.server.ws import install_ws

LOG = logging.getLogger("golem")
LOG_FILE = "server.log"
LOG_MAX_BYTES = 1_000_000
LOG_BACKUPS = 3
HTTP_ERROR_CODES = {404: "not_found", 405: "method_not_allowed"}


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
    install_ws(app, settings.levels_dir, settings.port)
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
