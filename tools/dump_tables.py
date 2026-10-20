#!/usr/bin/env python3
"""Muestra las tablas de direcciones de pantalla del Spectrum."""
import sys
from pathlib import Path

path = Path(sys.argv[1])
base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x6300
d = path.read_bytes()

print(f'{path.name}: {len(d)} bytes desde ${base:04X}')
print('\nlas 192 entradas (direccion de la linea de barrido):')
for i in range(0, min(len(d), 384), 2):
    v = d[i] | (d[i + 1] << 8)
    print(f'  {i // 2:3d}: ${v:04X}', end='')
    if i % 8 == 6:
        print()
print()
print('\nprimeros 64 bytes:', d[:64].hex(' '))
