from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import Flask, jsonify, redirect, url_for

from downloader import download_all, missing_files
from games.orquantix import GAME_ID, OrquantixState, build_blueprint, load_resources

APP_NAME = "PROCRASTINATOR"


class Shell:
    """L'application. Ne connaît aucune règle de mini-jeu."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.orquantix = OrquantixState()
        self._started: set[str] = set()
        self._lock = threading.Lock()

    def ensure_loaded(self, game_id: str) -> None:
        """Déclenche le chargement d'un jeu, une seule fois."""
        with self._lock:
            if game_id in self._started:
                return
            self._started.add(game_id)

        thread = threading.Thread(
            target=self._load, args=(game_id,), daemon=True
        )
        thread.start()

    def _load(self, game_id: str) -> None:
        state = self.orquantix
        try:
            if missing_files(self.data_dir):
                state.update(phase="downloading", progress=0, detail="Téléchargement…")
                download_all(state, self.data_dir)
            load_resources(state, self.data_dir)
        except Exception as exc:  # noqa: BLE001 — remonté à l'écran de chargement
            state.update(phase="error", detail=f"Erreur : {exc}")


def create_app(shell: Shell) -> Flask:
    templates_dir = os.environ.get("PROCRASTINATOR_TEMPLATES", "templates")
    static_dir = os.environ.get("PROCRASTINATOR_STATIC", "static")
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    app.register_blueprint(build_blueprint(shell.orquantix))

    @app.route("/")
    def home():
        # Phase 2 : le menu de PROCRASTINATOR. En attendant, on entre dans le jeu.
        shell.ensure_loaded(GAME_ID)
        return redirect(url_for("orquantix.index"))

    @app.route("/status")
    def status():
        return jsonify(shell.orquantix.snapshot())

    return app
