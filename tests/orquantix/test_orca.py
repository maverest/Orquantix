from games.orquantix.orca import beast_label, emoji, feedback, mood_for, rank_label


def test_mood_thresholds_at_the_rank_boundaries():
    assert mood_for(None) == "sick"
    assert mood_for(1500) == "sick"
    assert mood_for(1000) == "vexed"
    assert mood_for(551) == "vexed"
    assert mood_for(550) == "intrigued"
    assert mood_for(176) == "intrigued"
    assert mood_for(175) == "overexcited"
    assert mood_for(31) == "overexcited"
    assert mood_for(30) == "solar"
    assert mood_for(1) == "solar"


def test_found_overrides_everything():
    assert mood_for(None, found=True) == "found"
    assert mood_for(900, found=True) == "found"


def test_labels_exist_for_every_mood():
    for mood in ["sick", "vexed", "intrigued", "overexcited", "solar", "found"]:
        assert beast_label(mood)
        assert emoji(mood)


def test_rank_label_hides_rank_outside_top_1000():
    assert rank_label(None) == "Hors top 1000"
    assert rank_label(1500) == "Hors top 1000"
    assert rank_label(42) == "Voisin #42"
    assert rank_label(1, found=True) == "Mot mystère trouvé"


def test_feedback_bundles_progress_rank_and_mood():
    result = feedback(78)

    assert result["progress"] == 70.16 or result["progress"] > 60
    assert result["rank"] == 78
    assert result["mood"] == "overexcited"
    assert result["emoji"] == "🤯"
    assert result["rank_label"] == "Voisin #78"
    assert result["found"] is False


def test_feedback_for_a_word_outside_top_1000():
    result = feedback(5968)

    assert result["progress"] == 0.0
    assert result["rank"] is None
    assert result["rank_label"] == "Hors top 1000"
    assert result["mood"] == "sick"


def test_feedback_when_found():
    result = feedback(1, found=True)

    assert result["progress"] == 100.0
    assert result["mood"] == "found"
    assert result["found"] is True
