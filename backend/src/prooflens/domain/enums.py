"""Domain enumerations for ProofLens AI."""

from enum import StrEnum


class DocumentStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"
    DELETED = "deleted"


class PageExtractionStatus(StrEnum):
    EXTRACTED = "extracted"
    EMPTY = "empty"
    UNSUPPORTED = "unsupported"


class QueryRunStatus(StrEnum):
    COMPLETED = "completed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    FAILED = "failed"


class CitationValidationStatus(StrEnum):
    VALID_REFERENCE = "valid_reference"
    INVALID_REFERENCE_REJECTED = "invalid_reference_rejected"
    NEEDS_REVIEW = "needs_review"


class ComparisonRelationship(StrEnum):
    SUPPORTS = "supports"
    DIFFERS = "differs"
    APPARENT_CONTRADICTION = "apparent_contradiction"
    NOT_COMPARABLE = "not_comparable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
