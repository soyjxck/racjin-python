"""
racjin - Python implementation of the Racjin compression algorithm.

Used in PS2/PSP/Wii games by Racjin and other Japanese studios, including:
- Fullmetal Alchemist and the Broken Angel (PS2)
- Fullmetal Alchemist 2/3 (PS2)
- Naruto: Uzumaki Chronicles series (PS2)
- Bleach: Soul Carnival 2 (PSP)
- Naruto Shippuden: Legends / Ultimate Ninja Impact (PSP)

Archives using this compression are typically named CFC.DIG or CDDATA.DIG.

Reference C++ implementation:
    https://github.com/Raw-man/Racjin-de-compression
"""

from racjin.codec import compress, decompress

__version__ = "1.0.0"
__all__ = ["compress", "decompress"]
