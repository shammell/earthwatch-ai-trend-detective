from scene_state import (
    Scene,
    WizardStep,
    advance_step,
    can_render_evidence,
    can_show_analysis,
    retreat_step,
    transition,
)


def test_invalid_coverage_is_blocked_from_verdict_scene():
    assert transition(Scene.LOADING, evidence_valid=False) is Scene.COVERAGE_WARNING
    assert not can_show_analysis(Scene.COVERAGE_WARNING, False)


def test_valid_coverage_reaches_evidence_scene():
    scene = transition(Scene.LOADING, evidence_valid=True)
    assert scene is Scene.EVIDENCE
    assert can_show_analysis(scene, True)


def test_wizard_requires_explicit_step_actions():
    assert advance_step(WizardStep.BRIEFING) is WizardStep.SELECTION
    assert advance_step(WizardStep.SELECTION) is WizardStep.EVIDENCE
    assert advance_step(WizardStep.EVIDENCE) is WizardStep.VERDICT


def test_invalid_evidence_cannot_advance_to_verdict():
    assert advance_step(WizardStep.EVIDENCE, evidence_valid=False) is WizardStep.EVIDENCE
    assert not can_render_evidence(WizardStep.EVIDENCE, False)


def test_wizard_back_navigation():
    assert retreat_step(WizardStep.VERDICT) is WizardStep.EVIDENCE
    assert retreat_step(WizardStep.BRIEFING) is WizardStep.BRIEFING
