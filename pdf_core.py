"""PDF authoring for payload smuggling.

Builds multi-page PDFs with hidden payloads using ``pypdf``.  Supports
three smuggling strategies:

* **invisible_text** — white-on-white text, invisible unless selected.
* **marked_content** — payload in PDF marked-content operators, which
  most renderers ignore.
* **between_objects** — payload as a comment-like stream between PDF
  indirect objects.
"""

from __future__ import annotations

import io


def _get_pypdf():
    """Lazy-import pypdf so the base install does not require it."""
    try:
        import pypdf
    except ImportError as exc:
        raise ImportError(
            "PDF authoring requires pypdf. Install with `pip install stegg[pdf]` "
            "or `pip install pypdf`."
        ) from exc
    return pypdf


def _make_content_stream(content: bytes) -> "pypdf.generic.StreamObject":
    """Build a StreamObject from raw content bytes."""
    import pypdf
    from pypdf.generic import StreamObject, NameObject, NumberObject

    stream = StreamObject()
    stream._data = content
    stream[NameObject("/Length")] = NumberObject(len(content))
    return stream


def pdf_smuggle_invisible_text(
    payload: str | bytes,
    *,
    cover_text: str = "This page intentionally left blank.",
    page_count: int = 1,
) -> bytes:
    """Create a PDF with *payload* hidden as white-on-white invisible text.

    *payload* may be a ``str`` (UTF-8 encoded) or raw ``bytes``.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    pypdf = _get_pypdf()
    from pypdf.generic import NameObject

    writer = pypdf.PdfWriter()

    for _ in range(page_count):
        payload_escaped = payload.decode("utf-8", errors="replace")
        payload_escaped = (
            payload_escaped.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
        )

        content = (
            b"BT\n"
            b"/F1 12 Tf\n"
            b"72 700 Td\n"
            b"(" + cover_text.encode("latin-1", errors="replace") + b") Tj\n"
            b"ET\n"
            b"BT\n"
            b"1 1 1 rg\n"
            b"/F1 1 Tf\n"
            b"72 10 Td\n"
            b"(" + payload_escaped.encode("latin-1", errors="replace") + b") Tj\n"
            b"ET\n"
        )

        writer.add_blank_page(width=612, height=792)
        writer.pages[-1][NameObject("/Contents")] = _make_content_stream(content)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def pdf_smuggle_marked_content(
    payload: str | bytes,
    *,
    cover_text: str = "This page intentionally left blank.",
) -> bytes:
    """Create a PDF with *payload* hidden in marked-content operators.

    *payload* may be a ``str`` (UTF-8 encoded) or raw ``bytes``.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    pypdf = _get_pypdf()
    from pypdf.generic import NameObject

    writer = pypdf.PdfWriter()
    payload_hex = payload.hex()

    content = (
        b"BT\n/F1 12 Tf\n72 700 Td\n"
        b"(" + cover_text.encode("latin-1", errors="replace") + b") Tj\nET\n"
        b"/Payload BMC\n"
        b"(" + payload_hex.encode("ascii") + b")\n"
        b"EMC\n"
    )

    writer.add_blank_page(width=612, height=792)
    writer.pages[-1][NameObject("/Contents")] = _make_content_stream(content)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def pdf_smuggle_between_objects(
    payload: str | bytes,
    *,
    page_count: int = 2,
) -> bytes:
    """Create a multi-page PDF with *payload* in a non-referenced stream.

    *payload* may be a ``str`` (UTF-8 encoded) or raw ``bytes``.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    pypdf = _get_pypdf()
    from pypdf.generic import StreamObject, NameObject

    writer = pypdf.PdfWriter()

    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)

    # Add an orphan indirect object containing the payload.
    payload_stream = StreamObject()
    payload_stream._data = payload
    payload_stream[NameObject("/Type")] = NameObject("/EmbeddedFile")
    payload_stream[NameObject("/Subtype")] = NameObject("/text#2Fplain")
    writer._add_object(payload_stream)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# Convenience dispatch.
_SMUGGLE_METHODS = {
    "invisible_text": pdf_smuggle_invisible_text,
    "marked_content": pdf_smuggle_marked_content,
    "between_objects": pdf_smuggle_between_objects,
}


def pdf_smuggle(
    payload: str | bytes,
    method: str = "between_objects",
    *,
    cover_text: str = "This page intentionally left blank.",
    page_count: int = 2,
) -> bytes:
    """Create a PDF smuggling *payload* via the given *method*.

    *payload* may be a ``str`` (UTF-8 encoded) or raw ``bytes``.
    """
    if method not in _SMUGGLE_METHODS:
        raise ValueError(
            f"unknown method {method!r}. "
            f"Use one of: {', '.join(sorted(_SMUGGLE_METHODS))}"
        )
    kwargs = {}
    if method in ("invisible_text", "marked_content"):
        kwargs["cover_text"] = cover_text
    if method in ("invisible_text", "between_objects"):
        kwargs["page_count"] = page_count
    return _SMUGGLE_METHODS[method](payload, **kwargs)
