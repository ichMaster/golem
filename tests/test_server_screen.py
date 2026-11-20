"""The game screen's files (a contract): ``GET /`` is the page, ``/screen/…`` serves
``golem/screen/`` from the package and nothing outside it, and no page file has an external URL."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from golem.server.app import SCREEN_DIR, create_app
from golem.server.config import Settings

REPO = Path(__file__).resolve().parent.parent
LEVELS = REPO / "levels"
CONTENT_TYPES = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}

# An external URL: a scheme with "//", or a protocol-relative "//host" where a URL is expected.
EXTERNAL_URL = re.compile(
    r"""(?ix)
    \b(?:https?|wss?):// |
    \b(?:src|href|action)\s*=\s*["']?\s*// |
    \burl\(\s*["']?\s*// |
    (?:\bimport|\bfrom|@import)\s*\(?\s*["']\s*//
    """
)


def client_for(tmp_path: Path) -> TestClient:
    return TestClient(create_app(Settings("127.0.0.1", 8700, LEVELS, tmp_path / "logs")))


class _References(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        self.found += [value for name, value in attrs if name in ("src", "href") and value]


def page_references() -> list[str]:
    parser = _References()
    parser.feed((SCREEN_DIR / "index.html").read_text(encoding="utf-8"))
    return parser.found


def screen_files() -> list[Path]:
    return sorted(p for p in SCREEN_DIR.rglob("*") if p.suffix in CONTENT_TYPES)


def test_the_page_is_served_at_the_root(tmp_path):
    response = client_for(tmp_path).get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.content == (SCREEN_DIR / "index.html").read_bytes()


def test_the_page_answers_head_like_the_files(tmp_path):
    client = client_for(tmp_path)
    for url in ("/", "/screen/screen.js"):
        response = client.head(url)
        assert response.status_code == 200, url
        assert response.content == b""


def test_every_file_the_page_references_is_served_with_its_content_type(tmp_path):
    client = client_for(tmp_path)
    references = page_references()
    assert "/screen/screen.js" in references
    for reference in references:
        response = client.get(reference)
        assert response.status_code == 200, reference
        expected = CONTENT_TYPES[Path(reference).suffix]
        assert response.headers["content-type"].startswith(expected), reference
        local = SCREEN_DIR / reference.removeprefix("/screen/")
        assert response.content == local.read_bytes(), reference


def test_every_screen_file_is_served_under_screen(tmp_path):
    client = client_for(tmp_path)
    for path in screen_files():
        url = "/screen/" + path.relative_to(SCREEN_DIR).as_posix()
        response = client.get(url)
        assert response.status_code == 200, url
        assert response.headers["content-type"].startswith(CONTENT_TYPES[path.suffix]), url


@pytest.mark.parametrize(
    "path",
    [
        "/screen/../server/app.py",
        "/screen/%2e%2e/server/app.py",
        "/screen/..%2fserver%2fapp.py",
        "/screen/%2e%2e%2f%2e%2e%2fpyproject.toml",
        "/screen/%2e%2e/__init__.py",
        "/screen/",
        "/screen",
        "/screen/missing.js",
    ],
)
def test_nothing_outside_the_screen_directory_is_served(tmp_path, path):
    # "/screen" first redirects to "/screen/"; the answer that ends the chain is what counts.
    response = client_for(tmp_path).get(path)
    assert response.status_code == 404, path
    body = response.json()
    assert body["error"] == "not_found"
    assert set(body) == {"error", "detail"}
    assert "def create_app" not in response.text
    assert "[project]" not in response.text


def test_the_screen_directory_is_found_from_the_package(tmp_path, monkeypatch):
    client = client_for(tmp_path)
    monkeypatch.chdir(tmp_path)
    response = client.get("/")
    assert response.status_code == 200
    assert response.content == (SCREEN_DIR / "index.html").read_bytes()
    assert client.get("/screen/screen.js").status_code == 200


@pytest.mark.parametrize(
    "text",
    [
        '<script src="https://cdn.example.org/lib.js"></script>',
        "<link href='//fonts.example.org/x.css'>",
        "new WebSocket('ws://127.0.0.1:8700/ws')",
        "fetch('http://example.org')",
        "@font-face { src: url(//fonts.example.org/a.woff2) }",
        '@import "//example.org/a.css";',
        "import x from '//example.org/x.js'",
    ],
)
def test_the_external_url_check_catches_external_urls(text):
    assert EXTERNAL_URL.search(text)


@pytest.mark.parametrize(
    "text",
    [
        "// a comment in a script",
        "const half = a // b",
        '<script src="/screen/screen.js"></script>',
        "const url = new URL('/ws', location.href);",
    ],
)
def test_the_external_url_check_lets_local_text_through(text):
    assert not EXTERNAL_URL.search(text)


def test_no_screen_file_references_an_external_url():
    files = screen_files()
    assert SCREEN_DIR / "index.html" in files
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            assert not EXTERNAL_URL.search(line), f"{path.relative_to(SCREEN_DIR)}:{number}: {line}"


# --- The text page (v2.2) -------------------------------------------------------------------------

SCRIPT = SCREEN_DIR / "screen.js"
SOLUTIONS = REPO / "tests" / "fixtures" / "solutions"


def test_the_page_loads_scripts_and_styles_only_from_screen():
    references = page_references()
    assert references
    for reference in references:
        assert reference.startswith("/screen/"), reference
        assert (SCREEN_DIR / reference.removeprefix("/screen/")).is_file(), reference


def test_the_script_builds_the_socket_url_from_the_page_location():
    text = SCRIPT.read_text(encoding="utf-8")
    for literal in ("127.0.0.1", "localhost", "[::1]", "8700"):
        assert literal not in text, literal
    assert 'new URL("/ws", location.href)' in text


def script_messages() -> set[str]:
    return set(re.findall(r"""\btype:\s*["'](\w+)["']""", SCRIPT.read_text(encoding="utf-8")))


def script_keys() -> dict[str, str]:
    block = re.search(r"KEY_DIRECTIONS\s*=\s*\{(.*?)\}", SCRIPT.read_text(encoding="utf-8"), re.S)
    assert block, "screen.js has no KEY_DIRECTIONS table"
    return dict(re.findall(r"""(\w+)\s*:\s*["']([NESW])["']""", block.group(1)))


def test_the_page_sends_only_the_contract_messages():
    assert script_messages() == {"load", "move", "restart"}
    assert script_keys() == {"ArrowUp": "N", "ArrowRight": "E", "ArrowDown": "S", "ArrowLeft": "W"}


def recorded_moves(level_id: str) -> str:
    path = SOLUTIONS / f"{level_id}.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    return "".join(line.strip() for line in lines if line.strip() and not line.startswith(";"))


def test_the_page_messages_play_a_level_to_solved(tmp_path):
    level_id = "training/tier1/t1-01"
    with client_for(tmp_path).websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "load", "level": level_id}))
        start = ws.receive_json()
        assert start["type"] == "state" and start["status"] == "playing"
        for direction in recorded_moves(level_id):
            ws.send_text(json.dumps({"type": "move", "dir": direction}))
            state = ws.receive_json()
        assert state["status"] == "solved"
        ws.send_text(json.dumps({"type": "restart"}))
        assert ws.receive_json() == start
