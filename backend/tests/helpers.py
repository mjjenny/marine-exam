"""Small test helpers (no fixtures)."""
import io


def png_upload(name="sketch.png"):
    """A tiny PNG-ish payload as a (fileobj, filename) tuple for multipart uploads."""
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    return (io.BytesIO(data), name)
