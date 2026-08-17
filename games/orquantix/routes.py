from __future__ import annotations

from collections.abc import Callable

from flask import Blueprint, jsonify, render_template, request
from rapidfuzz import process as fuzz_process

from games.orquantix import engine, hints, orca
from games.orquantix.vocabulary import normalize

BLUEPRINT_NAME = "orquantix"
URL_PREFIX = "/games/orquantix"


def build_blueprint(state, on_load: Callable[[], None] | None = None) -> Blueprint:
    """Construit le blueprint du jeu.

    on_load : déclenché à chaque entrée dans le jeu via index() — c'est ici,
    pas dans la coquille (app.py), que le chargement paresseux doit démarrer,
    pour qu'atteindre /games/orquantix/ directement fonctionne, et pour
    qu'un futur menu phase 2 ne charge pas Orquantix à chaque visite.
    """
    bp = Blueprint(BLUEPRINT_NAME, __name__, url_prefix=URL_PREFIX)

    def _not_ready():
        return jsonify({"error": "not ready"}), 503

    def _record(
        round_index: int, word: str, rank: int | None, *, win: bool, gave_up: bool
    ) -> dict:
        entry = orca.feedback(rank, found=win)
        entry.update({"word": word, "win": win, "gave_up": gave_up})
        # round_index a été capturé avant tout calcul, côté route : si une
        # manche a démarré entre-temps, l'ajout est silencieusement
        # abandonné (voir OrquantixState.record_guess) plutôt que de muter
        # la liste de la nouvelle manche ou un objet déjà remplacé.
        state.record_guess(round_index, entry)
        return entry

    @bp.route("/")
    def index():
        if on_load is not None:
            on_load()
        return render_template("orquantix/index.html")

    @bp.route("/status")
    def status():
        return jsonify(state.snapshot())

    @bp.route("/session")
    def session():
        if state.phase != "ready":
            return _not_ready()
        return jsonify(
            {
                "difficulty": state.difficulty,
                "word_length": len(state.mystery_word),
                "guesses": state.guesses,
                "resolved": any(g["win"] for g in state.guesses),
            }
        )

    @bp.route("/guess", methods=["POST"])
    def guess():
        if state.phase != "ready":
            return _not_ready()

        # Capturé avant toute lecture de mystery_word/top1000 : si une
        # nouvelle manche démarre pendant le traitement de cette requête,
        # round_index reste celui de la manche pour laquelle la réponse a
        # réellement été calculée (voir _record / OrquantixState.record_guess).
        round_index = state.game_index

        payload = request.get_json(silent=True)
        if not payload or "word" not in payload:
            return jsonify({"error": "missing word"}), 400

        raw = str(payload["word"]).strip()
        norm = normalize(raw)

        if norm not in state.norm_to_model:
            return jsonify({"error": "inconnu"})

        word = state.norm_to_model[norm]

        if normalize(state.mystery_word) == norm:
            return jsonify(_record(round_index, state.mystery_word, 1, win=True, gave_up=False))

        rank = state.top1000.get(word)
        return jsonify(_record(round_index, word, rank, win=False, gave_up=False))

    @bp.route("/give-up", methods=["POST"])
    def give_up():
        if state.phase != "ready":
            return _not_ready()
        round_index = state.game_index
        return jsonify(_record(round_index, state.mystery_word, 1, win=True, gave_up=True))

    @bp.route("/suggest", methods=["POST"])
    def suggest():
        if state.phase != "ready":
            return _not_ready()

        payload = request.get_json(silent=True)
        if not payload or "word" not in payload:
            return jsonify({"error": "missing word"}), 400

        match = fuzz_process.extractOne(
            normalize(str(payload["word"]).strip()),
            state.norm_to_model.keys(),
            score_cutoff=80,
        )
        if match is None:
            return jsonify({"suggestion": None})
        return jsonify({"suggestion": state.norm_to_model[match[0]]})

    @bp.route("/hint", methods=["POST"])
    def hint():
        if state.phase != "ready":
            return _not_ready()

        payload = request.get_json(silent=True) or {}
        kind = payload.get("type")
        if kind not in {"first-letter", "word-length", "better-word", "golden-fish"}:
            return jsonify({"error": "invalid hint type"}), 400

        if kind == "first-letter":
            letter = state.mystery_word[0]
            return jsonify({"type": kind, "message": f"Première lettre : {letter.upper()}", "value": letter})

        if kind == "word-length":
            length = len(state.mystery_word)
            return jsonify({"type": kind, "message": f"Nombre de lettres : {length}", "value": length})

        guessed = {g["word"] for g in state.guesses}
        pool = state.pools.hint_words

        if kind == "golden-fish":
            result = hints.golden_fish(state.mystery_word, state.littre, state.top1000, pool, guessed)
            return jsonify({"type": kind, **result})

        ranked = [g["rank"] for g in state.guesses if g["rank"] is not None]
        best_rank = min(ranked) if ranked else None
        word = hints.better_hint_word(state.top1000, pool, best_rank, guessed)
        if word is None:
            return jsonify(
                {"type": kind, "message": "Tu as déjà le meilleur indice possible.", "value": None}
            )
        return jsonify({"type": kind, "message": f'Essaie "{word}"', "value": word})

    @bp.route("/new-game", methods=["POST"])
    def new_game():
        if state.phase != "ready":
            return _not_ready()

        # Le mot du prochain tour se calcule à partir de l'index à venir ;
        # pools/model sont immuables une fois phase == "ready" (posés une
        # fois par le loader), donc les lire ici sans verrou est sûr. Seule
        # la transition elle-même (incrément + remplacement des champs de
        # la manche) doit être atomique — c'est start_new_round qui s'en
        # charge (finding 2 : plus de game_index += 1 séparé du reste).
        next_index = state.game_index + 1
        word = engine.get_daily_word(state.pools.mystery_words, next_index)
        neighbours = engine.get_neighbours(state.model, word)

        state.start_new_round(
            mystery_word=word,
            neighbours=neighbours,
            top1000=engine.rank_map(neighbours),
            difficulty=engine.get_difficulty(word, state.pools.mystery_freq, state.difficulty_thresholds),
        )
        return jsonify({"difficulty": state.difficulty, "word_length": len(word)})

    return bp
