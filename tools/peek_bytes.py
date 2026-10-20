#!/usr/bin/env python3
"""Mira bytes concretos de la imagen de memoria del juego y del ROM."""
from pathlib import Path

img = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin').read_bytes()
print(f'imagen: {len(img)} bytes ($0000-$FFFF)')

def hexdump(addr, length, label=''):
    print(f'\n{label} ${addr:04X}:')
    for i in range(0, length, 16):
        row = img[addr + i:addr + i + 16]
        txt = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        print(f'  ${addr + i:04X}: ' + ' '.join(f'{b:02X}' for b in row) + '  ' + txt)

hexdump(0x6504, 48, 'entrada del juego')
hexdump(0x70D3, 32, 'manejador de interrupcion')
hexdump(0xFE00, 32, 'vector de interrupcion IM2')

rom48 = Path(r'C:\Dev\z80emu\spectrum\bin\Debug\net10.0\48.rom').read_bytes()
print(f'\n48.rom: {len(rom48)} bytes, primeros: ' +
      ' '.join(f'{b:02X}' for b in rom48[:16]))
