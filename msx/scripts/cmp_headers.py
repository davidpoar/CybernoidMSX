#!/usr/bin/env python3
"""Compara la cabecera de una ROM de cartucho MSX con la nuestra."""
import sys
from pathlib import Path

ROMS = Path(r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms')
OURS = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom')


def header(path):
    d = path.read_bytes()
    h = d[:0x20]
    print(f'\n{path.name}  ({len(d)} bytes)')
    print('  $4000: ' + ' '.join(f'{b:02X}' for b in h[:16]))
    print('  $4010: ' + ' '.join(f'{b:02X}' for b in h[16:32]))
    print(f'  ID        = {h[0:2]}')
    print(f'  INIT      = ${h[2] | (h[3] << 8):04X}')
    print(f'  STATEMENT = ${h[4] | (h[5] << 8):04X}')
    print(f'  DEVICE    = ${h[6] | (h[7] << 8):04X}')
    print(f'  TEXT      = ${h[8] | (h[9] << 8):04X}')
    print(f'  $400A     = {h[10:12].hex()}')
    print(f'  $400C     = {h[12:14].hex()}')
    print(f'  device id = ${h[14]:02X}   (MSX2: ${h[15]:02X})')
    print(f'  nombre    = {h[16:32].decode("latin-1")!r}')
    return d


def main():
    for name in ['ascii16/cross_blaim_dbsoft_1985_64k.rom',
                 'ascii16/gallforce_sony_1986_128k.rom',
                 'ascii16/elevator_action_taito_1985_32k.rom',
                 'plain/antarctic_adventure_konami_1984_16k.rom']:
        p = ROMS / name
        if p.exists():
            header(p)
    header(OURS)


if __name__ == '__main__':
    main()
