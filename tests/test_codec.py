"""Tests for Racjin compress/decompress round-trip."""

import os
import random

from racjin import compress, decompress


def test_roundtrip_simple():
    """Compress then decompress should return original data."""
    original = b"Hello, World! This is a test of the Racjin compression algorithm."
    compressed = compress(original)
    decompressed = decompress(compressed, len(original))
    assert decompressed == original


def test_roundtrip_zeros():
    """All-zero data should compress and decompress correctly."""
    original = b"\x00" * 1024
    compressed = compress(original)
    decompressed = decompress(compressed, len(original))
    assert decompressed == original


def test_roundtrip_repeated():
    """Highly repetitive data should compress well."""
    original = b"ABCDEFGH" * 500
    compressed = compress(original)
    decompressed = decompress(compressed, len(original))
    assert decompressed == original
    assert len(compressed) < len(original)


def test_roundtrip_random():
    """Random data should survive round-trip (even if it doesn't compress)."""
    random.seed(42)
    original = bytes(random.randint(0, 255) for _ in range(4096))
    compressed = compress(original)
    decompressed = decompress(compressed, len(original))
    assert decompressed == original


def test_roundtrip_binary():
    """Binary data with mixed patterns."""
    original = bytearray()
    for i in range(256):
        original.extend(bytes([i]) * (i % 8 + 1))
    original = bytes(original)
    compressed = compress(original)
    decompressed = decompress(compressed, len(original))
    assert decompressed == original


def test_decompress_empty_raises():
    """Decompressing with size 0 should raise ValueError."""
    try:
        decompress(b"\x00\x00", 0)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_compress_empty():
    """Compressing empty data should return empty or minimal output."""
    compressed = compress(b"")
    assert isinstance(compressed, bytes)


def test_roundtrip_large():
    """Test with larger data (64KB)."""
    random.seed(123)
    # Mix of compressible and random data
    parts = []
    for _ in range(64):
        if random.random() < 0.5:
            parts.append(bytes([random.randint(0, 255)]) * random.randint(8, 128))
        else:
            parts.append(bytes(random.randint(0, 255) for _ in range(random.randint(8, 128))))
    original = b"".join(parts)
    compressed = compress(original)
    decompressed = decompress(compressed, len(original))
    assert decompressed == original


if __name__ == "__main__":
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS: {name}")
            except Exception as e:
                print(f"  FAIL: {name}: {e}")
