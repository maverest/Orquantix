from __future__ import annotations

import os
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from downloader import download_all, MODEL_FILENAME, LEXIQUE_FILENAME
from game import (
    get_better_hint_word,
    get_daily_word,
    get_difficulty,
    get_proximity_feedback,
    get_score,
    get_strong_hint_word,
    get_top1000,
)
from vocabulary import (
    build_norm_map,
    compute_difficulty_thresholds,
    filter_eligible_words,
    normalize,
)
from rapidfuzz import process as fuzz_process


class AppState:
    def __init__(self) -> None:
        self.phase: str = "init"  # "downloading" | "loading" | "ready"
        self.progress: int = 0
        self.detail: str = ""
        self.model = None
        self.vocab: list[str] = []          # mots mystères (fréquents)
        self.freq_by_word: dict[str, float] = {}
        self.difficulty_thresholds: list[float] = []
        self.norm_to_vocab: dict[str, str] = {}   # pour sélection du mot mystère
        self.norm_to_model: dict[str, str] = {}   # tous les mots du modèle (propositions)
        self.top1000: dict[str, int] = {}
        self.daily_word: str = ""
        self.daily_difficulty: int = 0
        self.game_index: int = 0
        self._lock = threading.Lock()

    def update(self, **kwargs) -> None:
        with self._lock:
            for k, v in kwargs.items():
                setattr(self, k, v)


def create_app(state: AppState) -> Flask:
    templates_dir = os.environ.get("SEMANTIX_TEMPLATES", "templates")
    static_dir = os.environ.get("SEMANTIX_STATIC", "static")
    app = Flask(__name__, template_folder=templates_dir, static_folder=static_dir)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/status")
    def status():
        with state._lock:
            return jsonify({
                "phase": state.phase,
                "progress": state.progress,
                "detail": state.detail,
            })

    @app.route("/daily-info")
    def daily_info():
        if state.phase != "ready":
            return jsonify({"error": "not ready"}), 503
        with state._lock:
            return jsonify({
                "difficulty": state.daily_difficulty,
                "word_length": len(state.daily_word),
            })

    @app.route("/guess", methods=["POST"])
    def guess():
        if state.phase != "ready":
            return jsonify({"error": "not ready"}), 503
        data = request.get_json(silent=True)
        if not data or "word" not in data:
            return jsonify({"error": "missing word"}), 400

        word = str(data["word"]).strip()
        norm = normalize(word)

        with state._lock:
            norm_to_model = state.norm_to_model
            top1000 = state.top1000
            model = state.model
            daily_word = state.daily_word

        if norm not in norm_to_model:
            return jsonify({"error": "inconnu"})

        orig_word = norm_to_model[norm]

        if normalize(daily_word) == norm:
            return jsonify({
                "word": daily_word,
                "score": 100.0,
                "rank": 1,
                "win": True,
                "gave_up": False,
                "proximity": get_proximity_feedback(1, found=True),
            })

        score = get_score(model, orig_word, daily_word)
        rank = top1000.get(orig_word)
        return jsonify({
            "word": orig_word,
            "score": score,
            "rank": rank,
            "win": False,
            "gave_up": False,
            "proximity": get_proximity_feedback(rank, found=False),
        })

    @app.route("/give-up", methods=["POST"])
    def give_up():
        if state.phase != "ready":
            return jsonify({"error": "not ready"}), 503

        with state._lock:
            daily_word = state.daily_word

        return jsonify({
            "word": daily_word,
            "score": 100.0,
            "rank": 1,
            "win": True,
            "gave_up": True,
            "proximity": get_proximity_feedback(1, found=True),
        })

    @app.route("/suggest", methods=["POST"])
    def suggest():
        if state.phase != "ready":
            return jsonify({"error": "not ready"}), 503
        data = request.get_json(silent=True)
        if not data or "word" not in data:
            return jsonify({"error": "missing word"}), 400

        word = str(data["word"]).strip()
        norm = normalize(word)

        with state._lock:
            norm_to_model = state.norm_to_model

        result = fuzz_process.extractOne(
            norm,
            norm_to_model.keys(),
            score_cutoff=80,
        )
        if result is None:
            return jsonify({"suggestion": None})

        matched_norm = result[0]
        return jsonify({"suggestion": norm_to_model[matched_norm]})

    @app.route("/hint", methods=["POST"])
    def hint():
        if state.phase != "ready":
            return jsonify({"error": "not ready"}), 503

        data = request.get_json(silent=True) or {}
        hint_type = data.get("type")
        if hint_type not in {"first-letter", "word-length", "better-word", "golden-fish"}:
            return jsonify({"error": "invalid hint type"}), 400

        with state._lock:
            daily_word = state.daily_word
            top1000 = state.top1000

        if hint_type == "first-letter":
            return jsonify({
                "type": hint_type,
                "message": f"Premiere lettre : {daily_word[0].upper()}",
                "value": daily_word[0],
            })

        if hint_type == "word-length":
            return jsonify({
                "type": hint_type,
                "message": f"Nombre de lettres : {len(daily_word)}",
                "value": len(daily_word),
            })

        raw_best_rank = data.get("best_rank")
        try:
            best_rank = int(raw_best_rank) if raw_best_rank is not None else None
        except (TypeError, ValueError):
            best_rank = None

        raw_guessed_words = data.get("guessed_words") or []
        guessed_words = {
            str(word).strip()
            for word in raw_guessed_words
            if isinstance(word, str) and str(word).strip()
        }

        if hint_type == "golden-fish":
            hinted_word = get_strong_hint_word(
                top1000,
                guessed_words=guessed_words,
            )
            if hinted_word is None:
                return jsonify({
                    "type": hint_type,
                    "message": "Le poisson dore n'a rien remonte de mieux.",
                    "value": None,
                })

            return jsonify({
                "type": hint_type,
                "message": f'Poisson dore : essaie "{hinted_word}"',
                "value": hinted_word,
            })

        hinted_word = get_better_hint_word(top1000, best_rank, guessed_words=guessed_words)
        if hinted_word is None:
            return jsonify({
                "type": hint_type,
                "message": "Tu as deja le meilleur indice possible pour l'instant.",
                "value": None,
            })

        return jsonify({
            "type": hint_type,
            "message": f'Essaie "{hinted_word}"',
            "value": hinted_word,
        })

    @app.route("/new-game", methods=["POST"])
    def new_game():
        if state.phase != "ready":
            return jsonify({"error": "not ready"}), 503

        with state._lock:
            state.game_index += 1
            game_index = state.game_index
            vocab = state.vocab
            freq_by_word = state.freq_by_word
            thresholds = state.difficulty_thresholds
            model = state.model

        daily_word = get_daily_word(vocab, game_index)
        difficulty = get_difficulty(daily_word, freq_by_word, thresholds)
        top1000 = get_top1000(model, daily_word)

        state.update(
            daily_word=daily_word,
            daily_difficulty=difficulty,
            top1000=top1000,
        )
        return jsonify({"difficulty": difficulty, "word_length": len(daily_word)})

    return app


def _background_worker(state: AppState, data_dir: Path) -> None:
    try:
        _do_background_work(state, data_dir)
    except Exception as exc:
        state.update(phase="error", detail=f"Erreur : {exc}")
        raise


def _do_background_work(state: AppState, data_dir: Path) -> None:
    model_path = data_dir / MODEL_FILENAME
    lexique_path = data_dir / LEXIQUE_FILENAME

    if not model_path.exists() or not lexique_path.exists():
        state.update(phase="downloading")
        download_all(state, data_dir)

    state.update(phase="loading", progress=0, detail="Chargement du modèle Word2Vec…")
    from gensim.models import KeyedVectors

    try:
        model = KeyedVectors.load_word2vec_format(str(model_path), binary=True)
    except Exception:
        if model_path.exists():
            model_path.unlink()
        state.update(
            phase="downloading",
            progress=5,
            detail="Modèle incomplet détecté, nouveau téléchargement…",
        )
        download_all(state, data_dir)
        state.update(phase="loading", progress=0, detail="Chargement du modèle Word2Vec…")
        model = KeyedVectors.load_word2vec_format(str(model_path), binary=True)

    state.update(progress=60, detail="Filtrage du vocabulaire…")
    model_vocab = set(model.key_to_index.keys())
    vocab, freq_by_word = filter_eligible_words(str(lexique_path), model_vocab)

    if not vocab:
        raise RuntimeError("Aucun mot éligible trouvé — vérifiez Lexique383.tsv")

    norm_to_vocab = build_norm_map(vocab)
    # Tous les mots du modèle sont acceptés comme propositions
    norm_to_model = build_norm_map(list(model.key_to_index.keys()))
    thresholds = compute_difficulty_thresholds(vocab, freq_by_word)

    state.update(progress=80, detail="Calcul du mot du jour…")
    daily_word = get_daily_word(vocab, state.game_index)
    difficulty = get_difficulty(daily_word, freq_by_word, thresholds)

    state.update(progress=90, detail="Calcul des 1000 voisins les plus proches…")
    top1000 = get_top1000(model, daily_word)

    state.update(
        phase="ready",
        model=model,
        vocab=vocab,
        freq_by_word=freq_by_word,
        difficulty_thresholds=thresholds,
        norm_to_vocab=norm_to_vocab,
        norm_to_model=norm_to_model,
        top1000=top1000,
        daily_word=daily_word,
        daily_difficulty=difficulty,
        progress=100,
        detail="Prêt !",
    )


def start_background(state: AppState, data_dir: Path) -> None:
    t = threading.Thread(target=_background_worker, args=(state, data_dir), daemon=True)
    t.start()
