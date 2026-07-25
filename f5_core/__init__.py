"""F5 JPEG steganography — pure-Python port.

The F5 algorithm (Westfeld 2001) — matrix encoding with shrinkage over
permuted, zigzag-ordered AC DCT coefficients — is implemented once in
:class:`F5Base`. The paper leaves three choices open (PRNG, key format,
length prefix); each concrete subclass pins one combination.

* :class:`F5Base` — abstract F5 core; subclass to bind a PRNG and
  framing scheme.
* :class:`F5Stegg` — the ``f5stegojs`` dialect (byte key, RC4-KSA
  keystream, 2/3-byte length prefix). Byte-compatible with the JS
  library shipped as ``f5stego-lib.js``.
"""

from __future__ import annotations

from ._errors import CapacityExceeded, ExtractionFailed, F5Error, InvalidJPEG
from .f5_base import F5Base
from .f5_stegg import F5Stegg

__all__ = [
    "F5Base",
    "F5Stegg",
    "F5Error",
    "CapacityExceeded",
    "InvalidJPEG",
    "ExtractionFailed",
]
