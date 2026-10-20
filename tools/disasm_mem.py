#!/usr/bin/env python3
"""Desensambla una zona de la imagen de memoria del juego."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from z80dis import z80

img = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin').read_bytes()
BASE = 0x4000


def dis(start, length):
    print(f'\n=== ${start:04X}-${start + length:04X} ===')
    pos = start
    while pos < start + length:
        off = pos - BASE
        chunk = img[off:off + 4]
        try:
            d = z80.decode(chunk, pos)
            raw = img[off:off + d.len]
            print(f'${pos:04X}: {z80.decoded2str(d):<30s} ; {raw.hex(" ")}')
            pos += d.len
        except Exception as e:
            print(f'${pos:04X}: ??? {e}')
            pos += 1


for a in [int(x, 16) for x in sys.argv[1:]] or [0x84E0]:
    dis(a, 64)
