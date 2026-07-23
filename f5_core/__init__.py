"""F5 JPEG steganography — pure-Python port.

Two dialects live behind separate classes so callers cannot accidentally
mix them up:

* :class:`F5Stegg` — the ``f5stegojs`` dialect (byte key, RC4-KSA keystream,
  2/3-byte length prefix). Byte-compatible with the JS library shipped as
  ``f5stego-lib.js``.
* :class:`F5Classic` — Westfeld's original F5 dialect (password string,
  MD5 → Java ``Random`` LCG, 32-bit length prefix). Compatible with
  ``Embed.jar`` / ``Extract.jar`` and downstream Java forks.

Both classes land in Phases 2 and 3 of the port. Phase 1 lands only the
codec substrate (:mod:`f5_core._dct`) and the exception hierarchy.
"""

from __future__ import annotations

from ._errors import CapacityExceeded, ExtractionFailed, F5Error, InvalidJPEG
from .f5_stegg import F5Stegg

__all__ = [
    "F5Stegg",
    "F5Classic",
    "F5Error",
    "CapacityExceeded",
    "InvalidJPEG",
    "ExtractionFailed",
]


class F5Classic:
    """Placeholder — lands in Phase 3."""

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "F5Classic (Westfeld dialect) is Phase 3 of the F5 port; "
            "not yet implemented.  Use F5Stegg for the f5stegojs dialect."
        )
