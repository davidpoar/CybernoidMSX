#!/usr/bin/env python3
"""Desensambla el INIT de una ROM de cartucho MSX real (referencia)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from z80dis import z80

ROOT = Path(r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms')


def dis(data, start, end, base=0x4000):
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
    for name, nbytes in [
        (r'ascii16\cross_blaim_dbsoft_1985_64k.rom', 90),
        (r'ascii16\elevator_action_taito_1985_32k.rom', 80),
    ]:
        p = ROOT / name
        if not p.exists():
            continue
        d = p.read_bytes()
        init = d[2] | (d[3] << 8)
        print(f'\n########## {name}   INIT = ${init:04X} ##########')
        dis(d, init, init + nbytes)


if __name__ == '__main__':
    main()
