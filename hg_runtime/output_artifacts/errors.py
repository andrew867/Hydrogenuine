"""Output artifacts errors."""

from __future__ import annotations


class OutputArtifactError(Exception):
    """Base output artifact error."""


class ArtifactValidationError(OutputArtifactError):
    """Artifact schema or content validation failed."""


class ArtifactQualityError(OutputArtifactError):
    """Output quality check failed."""


class ArtifactStoreError(OutputArtifactError):
    """Artifact store operation failed."""


class ReviewCandidateError(OutputArtifactError):
    """Review candidate operation failed."""


__all__ = [
    "ArtifactQualityError",
    "ArtifactStoreError",
    "ArtifactValidationError",
    "OutputArtifactError",
    "ReviewCandidateError",
]
