#!/usr/bin/env python3
"""Desensambla el motor de la ROM (banco 0)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from z80dis import z80

ROM = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom')
SYM = Path(r'C:\Dev\cybernoidMSX\msx\build\rom_engine.sym')

simbolos = {}
for linea in SYM.read_text().splitlines():
    p = linea.split()
    if len(p) >= 3:
        try:
            simbolos[int(p[2].rstrip('H'), 16)] = p[0]
        except ValueError:
            pass

rom = ROM.read_bytes()


def desensambla(inicio, fin):
    pos = inicio
    while pos < fin:
        off = pos - 0x4000
        chunk = rom[off:off + 4]
        try:
            d = z80.decode(chunk, pos)
            raw = rom[off:off + d.len]
            etiqueta = simbolos.get(pos, '')
            print(f'${pos:04X}: {z80.decoded2str(d):<28s} ; {raw.hex(" ")}'
                  f'  {etiqueta}')
            pos += d.len
        except Exception as e:
            print(f'${pos:04X}: ??? {e}')
            pos += 1


if __name__ == '__main__':
    a = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x4085
    b = int(sys.argv[2], 16) if len(sys.argv) > 2 else a + 64
    desensambla(a, b)
