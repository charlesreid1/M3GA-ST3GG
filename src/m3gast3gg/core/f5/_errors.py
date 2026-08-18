"""Exception hierarchy shared by both F5 dialects."""

from __future__ import annotations


class F5Error(Exception):
    """Base class for anything the F5 codec raises."""


class InvalidJPEG(F5Error):
    """The input isn't a JPEG we can operate on (wrong magic, CMYK, etc.)."""


class CapacityExceeded(F5Error):
    """Payload too large for the carrier at the chosen matrix parameter."""


class ExtractionFailed(F5Error):
    """Extraction produced nonsense — usually a wrong key/password."""
