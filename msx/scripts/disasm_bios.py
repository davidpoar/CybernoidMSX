#!/usr/bin/env python3
"""Desensambla las rutinas del BIOS de MSX1 que usa la ROM:
ENASLT ($0024 -> $025E), RSLREG ($0138 -> $144C) y la deteccion de
cartucho de la pagina de slots.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from z80dis import z80

BIOS = Path(__file__).parent.parent / 'build' / 'msx.rom'


def dis(data, base, start, end, label=''):
    print(f'\n=== {label}  ${start:04X}-${end:04X} ===')
    pos = start
    while pos < end:
        off = pos - base
        chunk = data[off:off + 4]
        try:
            d = z80.decode(chunk, pos)
            raw = data[off:off + d.len]
            print(f'${pos:04X}: {z80.decoded2str(d):<32s} ; {raw.hex()}')
            pos += d.len
        except Exception as e:
            print(f'${pos:04X}: ??? {e}')
            pos += 1


def main():
    data = BIOS.read_bytes()
    dis(data, 0x0000, 0x025E, 0x02A0, 'ENASLT ($025E)')
    dis(data, 0x0000, 0x144C, 0x1470, 'RSLREG ($144C)')
    dis(data, 0x0000, 0x7D60, 0x7DD0, 'Deteccion de cartucho (slots)')


if __name__ == '__main__':
    main()
