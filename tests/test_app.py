"""Tests de la coquille (Shell) elle-même.

Distinct de tests/orquantix/test_routes.py : ici on vérifie que app.py sait
démarrer un jeu paresseusement, une seule fois, et remonter une erreur —
sans rien connaître des règles d'Orquantix. Aucun de ces cas n'existait dans
l'ancien tests/test_app.py (qui testait AppState, supprimé avec ce refactor).
"""

import pytest

import app as app_module
from app import Shell, create_app


@pytest.fixture
def shell(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "missing_files", lambda data_dir: [])
    monkeypatch.setattr(app_module, "load_resources", lambda state, data_dir: None)
    return Shell(tmp_path)


@pytest.fixture
def client(shell):
    flask_app = create_app(shell)
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_home_redirects_into_the_game(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/games/orquantix/")


def test_status_reports_idle_before_the_game_is_entered(client):
    data = client.get("/status").get_json()
    assert data["phase"] == "idle"


def test_ensure_loaded_starts_the_game_only_once(shell):
    shell.ensure_loaded("orquantix")
    shell.ensure_loaded("orquantix")

    # L'idempotence se vérifie sans attendre le thread : l'ensemble
    # `_started` est mis à jour de façon synchrone avant le lancement.
    assert shell._started == {"orquantix"}


def test_load_downloads_only_when_files_are_missing(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(app_module, "missing_files", lambda data_dir: ["Lexique383.tsv"])
    monkeypatch.setattr(app_module, "download_all", lambda state, data_dir: calls.append("download"))
    monkeypatch.setattr(app_module, "load_resources", lambda state, data_dir: calls.append("load"))

    shell = Shell(tmp_path)
    shell._load("orquantix")

    assert calls == ["download", "load"]


def test_load_skips_download_when_files_are_present(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(app_module, "missing_files", lambda data_dir: [])
    monkeypatch.setattr(app_module, "download_all", lambda state, data_dir: calls.append("download"))
    monkeypatch.setattr(app_module, "load_resources", lambda state, data_dir: calls.append("load"))

    shell = Shell(tmp_path)
    shell._load("orquantix")

    assert calls == ["load"]


def test_load_failure_is_reported_on_the_state_instead_of_crashing(monkeypatch, tmp_path):
    monkeypatch.setattr(app_module, "missing_files", lambda data_dir: [])

    def boom(state, data_dir):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(app_module, "load_resources", boom)

    shell = Shell(tmp_path)
    shell._load("orquantix")  # ne doit pas lever

    assert shell.orquantix.phase == "error"
    assert "kaboom" in shell.orquantix.detail
