from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request
from rapidfuzz import process as fuzz_process

from games.orquantix import engine, hints, orca
from games.orquantix.vocabulary import normalize

BLUEPRINT_NAME = "orquantix"
URL_PREFIX = "/games/orquantix"


def build_blueprint(state) -> Blueprint:
    bp = Blueprint(BLUEPRINT_NAME, __name__, url_prefix=URL_PREFIX)

    def _not_ready():
        return jsonify({"error": "not ready"}), 503

    def _record(word: str, temperature: float, rank: int | None, *, win: bool, gave_up: bool) -> dict:
        entry = orca.feedback(temperature, rank, found=win)
        entry.update({"word": word, "win": win, "gave_up": gave_up})
        state.guesses.append(entry)
        return entry

    @bp.route("/")
    def index():
        return render_template("orquantix/index.html")

    @bp.route("/status")
    def status():
        return jsonify(state.snapshot())

    @bp.route("/session")
    def session():
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

        payload = request.get_json(silent=True)
        if not payload or "word" not in payload:
            return jsonify({"error": "missing word"}), 400

        raw = str(payload["word"]).strip()
        norm = normalize(raw)

        if norm not in state.norm_to_model:
            return jsonify({"error": "inconnu"})

        word = state.norm_to_model[norm]

        if normalize(state.mystery_word) == norm:
            return jsonify(_record(state.mystery_word, 100.0, 1, win=True, gave_up=False))

        similarity = float(state.model.similarity(word, state.mystery_word))
        degrees = engine.temperature(state.scale, similarity)
        rank = state.top1000.get(word)
        return jsonify(_record(word, degrees, rank, win=False, gave_up=False))

    @bp.route("/give-up", methods=["POST"])
    def give_up():
        if state.phase != "ready":
            return _not_ready()
        return jsonify(_record(state.mystery_word, 100.0, 1, win=True, gave_up=True))

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

        state.game_index += 1
        word = engine.get_daily_word(state.pools.mystery_words, state.game_index)
        neighbours = engine.get_neighbours(state.model, word)

        state.update(
            mystery_word=word,
            neighbours=neighbours,
            top1000={w: i + 1 for i, (w, _) in enumerate(neighbours)},
            scale=engine.build_temperature_scale(state.model, word, neighbours),
            difficulty=engine.get_difficulty(word, state.pools.mystery_freq, state.difficulty_thresholds),
            guesses=[],
        )
        return jsonify({"difficulty": state.difficulty, "word_length": len(word)})

    return bp
