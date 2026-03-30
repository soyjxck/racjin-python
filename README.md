# racjin

Python implementation of the Racjin compression algorithm used in PS2/PSP/Wii game archives.

Handles **CFC.DIG** and **CDDATA.DIG** archive files found in games by Racjin and other Japanese studios.

If this helped you, consider [buying me a coffee](https://ko-fi.com/soyjack) ☕

## Supported Games

- Fullmetal Alchemist and the Broken Angel (PS2)
- Fullmetal Alchemist 2: Curse of the Crimson Elixir (PS2)
- Fullmetal Alchemist 3: Kami o Tsugu Shoujo (PS2)
- Naruto: Uzumaki Chronicles 1 & 2 (PS2)
- Bleach: Soul Carnival 2 (PSP)
- Naruto Shippuden: Legends: Akatsuki Rising (PSP)
- Naruto Shippuden: Ultimate Ninja Impact (PSP)
- Other titles using the same archive format

## Installation

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## CLI Usage

### Extract an entire archive

```bash
# Auto-detects format and endianness
racjin extract CDDATA.DIG output/

# Specify format explicitly
racjin extract CFC.DIG output/ --format cfc

# For Wii/GameCube (big-endian)
racjin extract CDDATA.DIG output/ --big-endian
```

### Compress / decompress individual files

```bash
# Decompress (requires known decompressed size)
racjin decompress compressed.bin decompressed.bin --size 577152

# Compress
racjin compress input.bin compressed.bin
```

## Python API

```python
from racjin import compress, decompress

# Decompress
with open("compressed.bin", "rb") as f:
    compressed_data = f.read()

decompressed = decompress(compressed_data, expected_size)

# Compress
with open("input.bin", "rb") as f:
    original_data = f.read()

compressed = compress(original_data)

# Round-trip
assert decompress(compress(data), len(data)) == data
```

## Algorithm

The Racjin compression uses 9-bit tokens packed into a bitstream:

- **Bit 8 = 1**: Literal byte (lower 8 bits stored directly)
- **Bit 8 = 0**: Back-reference using a context-sensitive sliding window
  - Bits 3-7: 5-bit frequency index
  - Bits 0-2: 3-bit length (actual length = value + 1, max 8 bytes)
  - Window is a 8192-entry table indexed by `(freq_index + last_byte * 32)`

Tokens are folded using a rotating bit shift (0-7), packing 8 tokens (72 bits) into 9 bytes.

## Archive Formats

Three structure variants are supported:

| Format | Field Layout | Notes |
|--------|-------------|-------|
| `cfc` | offset, comp_size, section_count\|flags, decomp_size | Most common (post-2005) |
| `cddata` | offset, decomp_size, section_count, comp_size | All sizes in sectors (2004-era) |
| `cddata-old` | offset, size, section_count | No compression (pre-2004) |

All offsets are in 2048-byte disc sectors.

## Credits

Algorithm reverse-engineered by [Raw-man](https://github.com/Raw-man/Racjin-de-compression) (C++ implementation). This is a Python port.

## License

GPL-3.0 (same as the reference implementation)
