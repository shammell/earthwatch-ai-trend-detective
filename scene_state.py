"""Small state machine for the Task 4 guided evidence UI."""

from enum import Enum


class WizardStep(Enum):
    """Interactive wizard steps exposed by the Streamlit dashboard."""

    BRIEFING = 1
    SELECTION = 2
    EVIDENCE = 3
    VERDICT = 4


def advance_step(step: WizardStep, *, evidence_valid: bool = True) -> WizardStep:
    """Advance one wizard step, keeping invalid evidence out of the verdict."""
    if step is WizardStep.BRIEFING:
        return WizardStep.SELECTION
    if step is WizardStep.SELECTION:
        return WizardStep.EVIDENCE
    if step is WizardStep.EVIDENCE and evidence_valid:
        return WizardStep.VERDICT
    return step


def retreat_step(step: WizardStep) -> WizardStep:
    """Move back one step without discarding the user's selection."""
    if step is WizardStep.SELECTION:
        return WizardStep.BRIEFING
    if step is WizardStep.EVIDENCE:
        return WizardStep.SELECTION
    if step is WizardStep.VERDICT:
        return WizardStep.EVIDENCE
    return WizardStep.BRIEFING


def can_render_evidence(step: WizardStep, evidence_valid: bool) -> bool:
    """Whether derived evidence and charts are safe to display."""
    return evidence_valid and step in {WizardStep.EVIDENCE, WizardStep.VERDICT}


class Scene(Enum):
    """Scenes shown by the guided dashboard."""

    FRAMING = "framing"
    LOADING = "loading"
    EVIDENCE = "evidence"
    COVERAGE_WARNING = "coverage_warning"
    VERDICT = "verdict"


def transition(scene: Scene, *, loading: bool = False, evidence_valid: bool = False) -> Scene:
    """Return the next scene without allowing invalid data into verdicts."""
    if loading:
        return Scene.LOADING
    if not evidence_valid:
        return Scene.COVERAGE_WARNING
    return Scene.EVIDENCE if scene in {Scene.FRAMING, Scene.LOADING} else Scene.VERDICT


def can_show_analysis(scene: Scene, evidence_valid: bool) -> bool:
    """Whether charts, KPIs, and interpretation may be rendered."""
    return evidence_valid and scene in {Scene.EVIDENCE, Scene.VERDICT}
