"""Legacy import surface: pre-refactor names still work.

The old ``m3gast3gg.core.transforms`` was a flat module; it is now a package
with a shim that re-exports the legacy free functions and the ``_TRANSFORMS``
dict. Each import here anchors a caller-visible name that must not disappear
during the port.
"""

from __future__ import annotations


def test_legacy_free_function_imports():
    from m3gast3gg.core.transforms import (
        base32_encode,
        base64_encode,
        base_n_encode,
        binary_encode,
        fullwidth_text,
        hex_encode,
        leetspeak,
        reverse_text,
        ternary_encode,
        zalgo_text,
    )
    assert callable(zalgo_text)
    assert callable(fullwidth_text)
    assert callable(leetspeak)
    assert callable(base64_encode)
    assert callable(base32_encode)
    assert callable(binary_encode)
    assert callable(ternary_encode)
    assert callable(hex_encode)
    assert callable(reverse_text)
    assert callable(base_n_encode)


def test_legacy_registry_surface():
    from m3gast3gg.core.transforms import (
        _TRANSFORMS,
        get_transform,
        list_transforms,
    )
    names = list_transforms()
    assert "zalgo" in names
    assert "fullwidth" in names
    assert "leetspeak" in names
    assert "base64" in names
    assert "base32" in names
    assert "binary" in names
    assert "ternary" in names
    assert "hex" in names
    assert "reverse" in names
    assert callable(get_transform("fullwidth"))
    assert "fullwidth" in _TRANSFORMS
    assert callable(_TRANSFORMS["fullwidth"])


def test_legacy_fullwidth_output_stable():
    from m3gast3gg.core.transforms import fullwidth_text
    assert fullwidth_text("Hello") == "Ｈｅｌｌｏ"
    assert fullwidth_text(" ") == "　"
    assert fullwidth_text("!") == "！"


def test_legacy_base64_output_stable():
    from m3gast3gg.core.transforms import base64_encode
    assert base64_encode("Hello, World!") == "SGVsbG8sIFdvcmxkIQ=="


def test_legacy_hex_output_stable():
    from m3gast3gg.core.transforms import hex_encode
    assert hex_encode("hi") == "6869"


def test_legacy_binary_output_stable():
    from m3gast3gg.core.transforms import binary_encode
    assert binary_encode("A") == "01000001"


def test_legacy_reverse_involution():
    from m3gast3gg.core.transforms import reverse_text
    assert reverse_text(reverse_text("hello")) == "hello"


def test_legacy_base_n_encode_dispatches():
    from m3gast3gg.core.transforms import base_n_encode
    assert base_n_encode("A", 2) == "01000001"
    assert base_n_encode("A", 16) == "41"
