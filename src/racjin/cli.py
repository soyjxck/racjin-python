"""
Command-line interface for Racjin compression/decompression.

Usage:
    racjin decompress <input> <output> --size <decompressed_size>
    racjin compress <input> <output>
    racjin extract <archive> <output_dir> [--format cfc|cddata|cddata-old] [--big-endian]
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

from racjin.codec import compress, decompress

SECTOR_SIZE = 0x800  # 2048 bytes


def cmd_decompress(args: argparse.Namespace) -> None:
    with open(args.input, "rb") as f:
        data = f.read()

    result = decompress(data, args.size)

    with open(args.output, "wb") as f:
        f.write(result)

    print(f"Decompressed {len(data):,} -> {len(result):,} bytes")


def cmd_compress(args: argparse.Namespace) -> None:
    with open(args.input, "rb") as f:
        data = f.read()

    result = compress(data)

    with open(args.output, "wb") as f:
        f.write(result)

    ratio = len(data) / len(result) if result else 0
    print(f"Compressed {len(data):,} -> {len(result):,} bytes ({ratio:.2f}x)")


def cmd_extract(args: argparse.Namespace) -> None:
    """Extract all entries from a CFC.DIG or CDDATA.DIG archive."""
    archive_path = args.input
    output_dir = args.output
    fmt = args.format
    big_endian = args.big_endian
    endian = ">" if big_endian else "<"

    os.makedirs(output_dir, exist_ok=True)

    with open(archive_path, "rb") as f:
        archive = f.read()

    archive_size = len(archive)

    # Auto-detect format if not specified
    if fmt is None:
        first_16 = archive[:16]
        if first_16 == b"\x00" * 16:
            fmt = "cfc"
        else:
            first_offset = struct.unpack(f"{endian}I", first_16[:4])[0]
            if big_endian:
                first_offset = int.from_bytes(first_16[:4], "big")
            if first_offset * SECTOR_SIZE < archive_size:
                fmt = "cfc"  # FMA-style: CFC format but non-zero first entry
            else:
                fmt = "cddata"
        print(f"Auto-detected format: {fmt}")

    # Determine record section bounds
    if fmt == "cfc":
        record_start = 0
        first_offset = struct.unpack(f"{endian}I", archive[record_start:record_start + 4])[0]
        if first_offset == 0:
            # Standard CFC: first 16 bytes are empty, real data starts at 0x10
            record_start = 0x10
            first_offset = struct.unpack(f"{endian}I", archive[record_start:record_start + 4])[0]
        record_end = first_offset * SECTOR_SIZE
        record_size = 16
    elif fmt == "cddata":
        record_start = 0
        first_offset = struct.unpack(f"{endian}I", archive[:4])[0]
        record_end = first_offset * SECTOR_SIZE
        record_size = 16
    elif fmt == "cddata-old":
        record_start = 0
        first_offset = struct.unpack(f"{endian}I", archive[:4])[0]
        record_end = first_offset * SECTOR_SIZE
        record_size = 12
    else:
        print(f"Unknown format: {fmt}")
        sys.exit(1)

    print(f"Record section: 0x{record_start:X} - 0x{record_end:X}")

    extracted = 0
    failed = 0
    pos = record_start

    while pos + record_size <= record_end:
        entry_idx = (pos - record_start) // record_size

        if fmt == "cfc":
            offset, comp_size, section_and_flag, decomp_size = struct.unpack(
                f"{endian}IIII", archive[pos:pos + 16]
            )
            if endian == "<":
                section_count = section_and_flag & 0xFFFF
                is_compressed = (section_and_flag >> 16) & 0xFFFF
            else:
                section_count = (section_and_flag >> 16) & 0xFFFF
                is_compressed = section_and_flag & 0xFFFF

            offset *= SECTOR_SIZE
            is_compressed = comp_size != decomp_size

        elif fmt == "cddata":
            offset, decomp_size_sectors, section_count, comp_size_sectors = struct.unpack(
                f"{endian}IIII", archive[pos:pos + 16]
            )
            offset *= SECTOR_SIZE
            decomp_size = decomp_size_sectors * SECTOR_SIZE
            comp_size = comp_size_sectors * SECTOR_SIZE if comp_size_sectors > 0 else decomp_size
            is_compressed = comp_size_sectors > 0

        elif fmt == "cddata-old":
            offset, size_sectors, section_count = struct.unpack(
                f"{endian}III", archive[pos:pos + 12]
            )
            offset *= SECTOR_SIZE
            comp_size = size_sectors * SECTOR_SIZE
            decomp_size = comp_size
            is_compressed = False

        pos += record_size

        if offset == 0 and comp_size == 0:
            continue

        if offset >= archive_size:
            break

        if comp_size > decomp_size:
            print(f"  Entry {entry_idx}: comp > decomp, stopping (wrong format?)")
            break

        # Read compressed data
        raw = archive[offset:offset + comp_size]

        # Decompress if needed
        if is_compressed and comp_size != decomp_size:
            try:
                data = decompress(raw, decomp_size)
            except Exception as e:
                print(f"  Entry {entry_idx}: decompression failed: {e}")
                failed += 1
                continue
        else:
            data = raw[:decomp_size] if decomp_size < len(raw) else raw

        out_path = os.path.join(output_dir, f"{entry_idx:04d}.bin")
        with open(out_path, "wb") as f:
            f.write(data)

        extracted += 1

    print(f"\nExtracted: {extracted}, Failed: {failed}")
    print(f"Output: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="racjin",
        description="Racjin compression tool for PS2/PSP/Wii game archives (CFC.DIG / CDDATA.DIG)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # decompress
    p_dec = subparsers.add_parser("decompress", aliases=["d"], help="Decompress a single file")
    p_dec.add_argument("input", help="Compressed input file")
    p_dec.add_argument("output", help="Decompressed output file")
    p_dec.add_argument("--size", type=int, required=True, help="Expected decompressed size in bytes")
    p_dec.set_defaults(func=cmd_decompress)

    # compress
    p_enc = subparsers.add_parser("compress", aliases=["c"], help="Compress a single file")
    p_enc.add_argument("input", help="Input file to compress")
    p_enc.add_argument("output", help="Compressed output file")
    p_enc.set_defaults(func=cmd_compress)

    # extract
    p_ext = subparsers.add_parser("extract", aliases=["x"], help="Extract all entries from a DIG archive")
    p_ext.add_argument("input", help="Path to CFC.DIG or CDDATA.DIG file")
    p_ext.add_argument("output", help="Output directory")
    p_ext.add_argument(
        "--format", "-f",
        choices=["cfc", "cddata", "cddata-old"],
        default=None,
        help="Archive format (auto-detected if not specified)",
    )
    p_ext.add_argument(
        "--big-endian", "-b",
        action="store_true",
        help="Use big-endian byte order (for Wii/GameCube)",
    )
    p_ext.set_defaults(func=cmd_extract)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
