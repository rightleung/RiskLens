"""Service layer package."""

__all__ = ["AssessmentService", "AssessmentServiceError", "RichAssessmentService"]


def __getattr__(name: str):
    if name in {"AssessmentService", "AssessmentServiceError"}:
        from .assessment_service import AssessmentService, AssessmentServiceError

        return {
            "AssessmentService": AssessmentService,
            "AssessmentServiceError": AssessmentServiceError,
        }[name]
    if name == "RichAssessmentService":
        from .rich_assessment_service import RichAssessmentService

        return RichAssessmentService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
