"""The server skeleton: settings, the loopback bind, start-up checks, errors and the log."""

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from golem.server import app as server_app
from golem.server.app import StartupError, create_app
from golem.server.config import ConfigError, Settings, load_settings

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"


def settings_for(tmp_path: Path, levels_dir: Path = LEVELS) -> Settings:
    return Settings(host="127.0.0.1", port=8700, levels_dir=levels_dir, log_dir=tmp_path / "logs")


# --- settings ---------------------------------------------------------------------------------


def test_the_defaults_bind_loopback():
    settings = load_settings({})
    assert settings.host == "127.0.0.1"
    assert settings.port == 8700
    assert settings.levels_dir == Path("levels").resolve()
    assert settings.levels_dir.is_absolute()
    assert settings.log_dir == Path("data/logs").resolve()
    assert settings.game_file == Path("data/human-game.json").resolve()
    assert settings.programs_dir == Path("programs").resolve()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_hosts_are_accepted(host):
    assert load_settings({"GOLEM_HOST": host}).host == host


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.5", "::", "example.com"])
def test_a_host_that_is_not_loopback_is_refused(host):
    with pytest.raises(ConfigError) as caught:
        load_settings({"GOLEM_HOST": host})
    assert "loopback" in str(caught.value)


def test_the_port_and_the_levels_dir_come_from_the_environment(tmp_path):
    settings = load_settings({"GOLEM_PORT": "8801", "GOLEM_LEVELS_DIR": str(tmp_path)})
    assert settings.port == 8801
    assert settings.levels_dir == tmp_path.resolve()


@pytest.mark.parametrize("port", ["abc", "0", "65536", "-1", "80.5"])
def test_a_bad_port_is_refused(port):
    with pytest.raises(ConfigError):
        load_settings({"GOLEM_PORT": port})


def test_env_example_names_the_variables():
    names = {
        line.split("=", 1)[0]
        for line in (REPO / ".env.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }
    assert names == {
        "GOLEM_LEVELS_DIR", "GOLEM_HOST", "GOLEM_PORT", "LUA_MAX_MEMORY", "HOOK_EVERY",
        "GOLEM_PROGRAMS_DIR"}


# --- start-up checks (v1 code review #4) -------------------------------------------------------


def test_create_app_refuses_a_levels_dir_without_a_training_set(tmp_path):
    (tmp_path / "budgets.toml").write_text("[tier1]\nsteps = 1\ninstructions = 1\n")
    with pytest.raises(StartupError) as caught:
        create_app(settings_for(tmp_path, levels_dir=tmp_path))
    assert str(tmp_path) in str(caught.value)
    assert "training" in str(caught.value)


@pytest.mark.parametrize("budgets", [None, "[tier1\n", "[tier1]\nsteps = 0\ninstructions = 1\n"])
def test_create_app_refuses_a_missing_or_broken_budgets_file(tmp_path, budgets):
    (tmp_path / "training").mkdir()
    if budgets is not None:
        (tmp_path / "budgets.toml").write_text(budgets)
    with pytest.raises(StartupError) as caught:
        create_app(settings_for(tmp_path, levels_dir=tmp_path))
    assert "budgets.toml" in str(caught.value)


def test_main_refuses_a_non_loopback_host(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOLEM_HOST", "0.0.0.0")
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: pytest.fail("the server must not start"))
    with pytest.raises(SystemExit) as caught:
        server_app.main()
    assert caught.value.code == 2
    assert "loopback" in capsys.readouterr().err


# --- the error body and the log -----------------------------------------------------------------


def test_an_unknown_route_answers_with_the_error_body(tmp_path):
    client = TestClient(create_app(settings_for(tmp_path)))
    response = client.get("/no/such/route")
    assert response.status_code == 404
    assert response.json() == {"error": "not_found", "detail": "Not Found"}


def test_the_log_file_is_created_and_handlers_are_not_duplicated(tmp_path):
    create_app(settings_for(tmp_path))
    create_app(settings_for(tmp_path))
    assert (tmp_path / "logs" / "server.log").is_file()
    ours = [h for h in logging.getLogger("golem").handlers if getattr(h, "golem_handler", False)]
    assert len(ours) == 2  # one file, one console


# --- code review #2: .env comes from the working directory only --------------------------------


def run_main(monkeypatch, cwd: Path) -> dict:
    """Run main() in `cwd` with a private copy of the environment; return what uvicorn got."""
    import os

    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items()
                                        if not k.startswith("GOLEM_")})
    os.environ["GOLEM_LEVELS_DIR"] = str(LEVELS)
    monkeypatch.chdir(cwd)
    started = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: started.update(kwargs))
    server_app.main()
    return started


def test_a_parent_directorys_env_is_not_read(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("GOLEM_PORT=9999\n")
    (tmp_path / "work").mkdir()
    started = run_main(monkeypatch, tmp_path / "work")
    assert started == {"host": "127.0.0.1", "port": 8700, "log_level": "info"}


def test_the_working_directorys_env_is_read(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("GOLEM_PORT=8801\n")
    started = run_main(monkeypatch, tmp_path)
    assert started["port"] == 8801
