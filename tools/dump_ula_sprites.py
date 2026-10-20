#!/usr/bin/env python3
"""Busca los sprites de la ULA del Spectrum en un volcado de RAM.

En el Spectrum los atributos de los ocho sprites estan en $5F00
(cuatro bytes cada uno: Y, X, forma, atributo).  Un sprite esta
activo si su Y no es 0 (0 significa "fuera de pantalla").
"""
import sys
from pathlib import Path

path = Path(sys.argv[1])
d = path.read_bytes()
base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x5F00

print(f'{path.name}: {len(d)} bytes desde ${base:04X}')
print('\natributos de sprite:')
for i in range(0, min(len(d), 0x40), 4):
    y, x, forma, attr = d[i], d[i + 1], d[i + 2], d[i + 3]
    activo = 'ACTIVO' if y != 0 else ''
    print(f'  sprite {i // 4}: Y={y:3d} X={x:3d} forma=${forma:02X} '
          f'attr=${attr:02X}  {activo}')

print('\nla zona como bits (los sprites 8x8 empiezan en $4000):')
for i in range(0, min(len(d), 0x100), 8):
    fila = d[i:i + 8]
    bits = ''.join(f'{b:08b}' for b in fila)
    print(f'  ${base + i:04X}: {bits}')
