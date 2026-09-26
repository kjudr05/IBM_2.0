"""
Public re-exports for the models package.

Import from here rather than from individual sub-modules:

    from app.models import (
        PipelineFailureEvent,
        BaseEvidence, FailureEvidence, ChangeEvidence,
        DependencyEvidence, TestEvidence, InfraEvidence, HistoricalEvidence,
        AnyEvidence,
        InvestigationResult, InvestigationStatus, InvestigatorOutcome,
        FixProposal, FixType, ValidationResult, ValidationStatus,
    )
"""

from app.models.events import HistoricalRun, PipelineFailureEvent
from app.models.evidence import (
    AnyEvidence,
    BaseEvidence,
    ChangedFile,
    ChangeEvidence,
    Confidence,
    DepChange,
    DependencyEvidence,
    EvidenceSource,
    EvidenceType,
    FailedTest,
    FailureEvidence,
    HistoricalEvidence,
    InfraEvidence,
    Severity,
    SimilarFailure,
    TestCaseStatus,
    TestEvidence,
    TestRunEvidence,
)
from app.models.fix import FixProposal, FixType, ValidationResult, ValidationStatus
from app.models.investigation import (
    InvestigationResult,
    InvestigationStatus,
    InvestigatorOutcome,
)

__all__ = [
    # events
    "HistoricalRun",
    "PipelineFailureEvent",
    # evidence base + union
    "AnyEvidence",
    "BaseEvidence",
    "Confidence",
    "EvidenceSource",
    "EvidenceType",
    "Severity",
    "TestStatus",
    # value objects
    "ChangedFile",
    "DepChange",
    "FailedTest",
    "SimilarFailure",
    # evidence subclasses
    "ChangeEvidence",
    "DependencyEvidence",
    "FailureEvidence",
    "HistoricalEvidence",
    "InfraEvidence",
    "TestRunEvidence",
    "TestEvidence",  # alias for TestRunEvidence
    "TestCaseStatus",
    # investigation result
    "InvestigationResult",
    "InvestigationStatus",
    "InvestigatorOutcome",
    # fix proposal
    "FixProposal",
    "FixType",
    "ValidationResult",
    "ValidationStatus",
]
