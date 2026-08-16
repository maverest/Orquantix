from games.orquantix.orca import beast_label, emoji, feedback, mood_for, rank_label


def test_mood_thresholds_at_the_boundaries():
    assert mood_for(0.0) == "sick"
    assert mood_for(19.99) == "sick"
    assert mood_for(20.0) == "vexed"
    assert mood_for(49.99) == "vexed"
    assert mood_for(50.0) == "intrigued"
    assert mood_for(69.99) == "intrigued"
    assert mood_for(70.0) == "overexcited"
    assert mood_for(87.99) == "overexcited"
    assert mood_for(88.0) == "solar"
    assert mood_for(99.99) == "solar"


def test_orca_becomes_intrigued_exactly_when_entering_top_1000():
    # 50° est le repère : c'est l'entrée dans le top 1000.
    assert mood_for(49.99) == "vexed"
    assert mood_for(50.0) == "intrigued"


def test_found_overrides_everything():
    assert mood_for(0.0, found=True) == "found"
    assert mood_for(100.0) == "found"


def test_measured_guesses_map_to_expected_moods():
    # Cible « confiture », températures mesurées.
    assert mood_for(96.0) == "solar"        # compote
    assert mood_for(76.0) == "overexcited"  # tartine
    assert mood_for(64.0) == "intrigued"    # cuisine
    assert mood_for(14.0) == "sick"         # bonjour
    assert mood_for(0.0) == "sick"          # moteur


def test_labels_exist_for_every_mood():
    for mood in ["sick", "vexed", "intrigued", "overexcited", "solar", "found"]:
        assert beast_label(mood)
        assert emoji(mood)


def test_rank_label_hides_rank_outside_top_1000():
    assert rank_label(None) == "Hors top 1000"
    assert rank_label(1500) == "Hors top 1000"
    assert rank_label(42) == "Voisin #42"
    assert rank_label(1, found=True) == "Mot mystère trouvé"


def test_feedback_bundles_everything_the_frontend_needs():
    result = feedback(76.0, 78)

    assert result["temperature"] == 76.0
    assert result["rank"] == 78
    assert result["mood"] == "overexcited"
    assert result["emoji"] == "🤯"
    assert result["rank_label"] == "Voisin #78"
    assert result["found"] is False


def test_feedback_for_a_word_outside_top_1000():
    result = feedback(14.0, None)

    assert result["rank"] is None
    assert result["rank_label"] == "Hors top 1000"
    assert result["mood"] == "sick"
