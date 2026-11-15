"""Small state machine for the Task 4 guided evidence UI."""

from enum import Enum


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
