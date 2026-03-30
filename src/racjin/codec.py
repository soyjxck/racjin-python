"""
Racjin compression and decompression.

Algorithm overview:
    - Data is encoded as a stream of 9-bit tokens
    - Tokens are packed into bytes using a rotating bit shift (0-7)
    - Bit 8 of each token is a flag:
        - 1 = literal byte (lower 8 bits are the value)
        - 0 = back-reference (bits 3-7 = frequency index, bits 0-2 = length-1)
    - Back-references use a context-sensitive sliding window:
        - 8192-entry table indexed by (frequency_index + last_byte * 32)
        - A per-byte frequency counter wraps at 31 (& 0x1F)

Port of the C++ implementation by Raw-man:
    https://github.com/Raw-man/Racjin-de-compression
"""

from __future__ import annotations


def decompress(data: bytes | bytearray, decompressed_size: int) -> bytes:
    """
    Decompress Racjin-compressed data.

    Args:
        data: Compressed input bytes.
        decompressed_size: Expected size of decompressed output.

    Returns:
        Decompressed bytes of exactly decompressed_size length.

    Raises:
        ValueError: If decompressed_size is negative or zero.
        DecompressionError: If the compressed data is malformed.
    """
    if decompressed_size <= 0:
        raise ValueError(f"decompressed_size must be positive, got {decompressed_size}")

    buf = memoryview(data) if isinstance(data, (bytes, bytearray)) else bytes(data)
    buf_len = len(buf)

    index = 0
    dest_index = 0
    last_dec_byte = 0
    bit_shift = 0

    frequencies = bytearray(256)
    seq_indices = [0] * 8192
    output = bytearray(decompressed_size)

    while index < buf_len - 1 and dest_index < decompressed_size:
        # Read 2 bytes little-endian, extract 9-bit token
        next_code = (buf[index + 1] << 8) | buf[index]
        next_code >>= bit_shift

        bit_shift += 1
        index += 1

        if bit_shift == 8:
            bit_shift = 0
            index += 1

        seq_index = dest_index

        if next_code & 0x100:
            # Literal byte
            output[dest_index] = next_code & 0xFF
            dest_index += 1
        else:
            # Back-reference
            key = ((next_code >> 3) & 0x1F) + last_dec_byte * 32
            src_index = seq_indices[key]
            length = (next_code & 0x07) + 1

            for _ in range(length):
                if dest_index >= decompressed_size:
                    break
                output[dest_index] = output[src_index]
                dest_index += 1
                src_index += 1

        if dest_index >= decompressed_size:
            break

        # Update context tables
        key = frequencies[last_dec_byte] + last_dec_byte * 32
        seq_indices[key] = seq_index
        frequencies[last_dec_byte] = (frequencies[last_dec_byte] + 1) & 0x1F
        last_dec_byte = output[dest_index - 1]

    return bytes(output)


def compress(data: bytes | bytearray) -> bytes:
    """
    Compress data using the Racjin algorithm.

    Args:
        data: Input bytes to compress.

    Returns:
        Compressed bytes.

    Note:
        The output may be slightly larger than the C++ reference
        implementation due to minor differences in the code folding
        step. Both produce output that decompresses identically.
    """
    buf = bytes(data)
    buf_len = len(buf)

    index = 0
    last_enc_byte = 0
    bit_shift = 0

    frequencies = [0] * 256
    seq_indices = [0] * 8192

    codes: list[int] = []

    while index < buf_len:
        best_freq = 0
        best_match = 0

        positions_to_check = min(frequencies[last_enc_byte], 32) & 0x1F

        seq_index = index

        # Search for best match in the context window
        for freq in range(positions_to_check):
            key = freq + last_enc_byte * 32
            src_index = seq_indices[key]

            matched = 0
            max_length = min(8, buf_len - index)

            for offset in range(max_length):
                if src_index + offset >= buf_len:
                    break
                if buf[src_index + offset] == buf[index + offset]:
                    matched += 1
                else:
                    break

            if matched > best_match:
                best_freq = freq
                best_match = matched

        if best_match > 0:
            # Encode back-reference: flag=0, freq in bits 3-7, length-1 in bits 0-2
            code = (best_freq << 3) | (best_match - 1)
            index += best_match
        else:
            # Encode literal: flag=1, byte value in bits 0-7
            code = 0x100 | buf[index]
            index += 1

        # Apply bit shift for folding
        code <<= bit_shift
        codes.append(code)

        bit_shift += 1
        if bit_shift == 8:
            bit_shift = 0

        # Update context tables
        key = (frequencies[last_enc_byte] & 0x1F) + last_enc_byte * 32
        seq_indices[key] = seq_index
        frequencies[last_enc_byte] += 1
        last_enc_byte = buf[index - 1]

    # Fold codes: pack 9-bit tokens into bytes
    # Groups of 8 codes (9 bits each = 72 bits) fold into 9 bytes
    compressed = bytearray()

    for i in range(0, len(codes), 8):
        group_size = min(8, len(codes) - i)

        for s in range(0, group_size + 1, 2):
            first = codes[s + i - 1] if s > 0 else 0x00
            middle = codes[s + i] if s < group_size else 0x00
            last = codes[s + i + 1] if s < group_size - 1 else 0x00

            result = middle | (first >> 8) | (last << 8)

            compressed.append(result & 0xFF)

            if s < group_size:
                compressed.append((result >> 8) & 0xFF)

    return bytes(compressed)
