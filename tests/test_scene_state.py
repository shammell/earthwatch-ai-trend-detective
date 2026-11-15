from scene_state import Scene, can_show_analysis, transition


def test_invalid_coverage_is_blocked_from_verdict_scene():
    assert transition(Scene.LOADING, evidence_valid=False) is Scene.COVERAGE_WARNING
    assert not can_show_analysis(Scene.COVERAGE_WARNING, False)


def test_valid_coverage_reaches_evidence_scene():
    scene = transition(Scene.LOADING, evidence_valid=True)
    assert scene is Scene.EVIDENCE
    assert can_show_analysis(scene, True)
