#!/usr/bin/env python3
"""Busca llamadas y saltos a direcciones concretas en la imagen."""
import sys
from pathlib import Path

img = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin').read_bytes()
BASE = 0x4000


def buscar(needle, label):
    print(f'\n=== {label} ({needle.hex(" ")}) ===')
    i = 0
    n = 0
    while True:
        i = img.find(needle, i)
        if i < 0:
            break
        print(f'  ${BASE + i:04X}')
        i += 1
        n += 1
        if n > 40:
            print('  ...')
            break
    if n == 0:
        print('  no encontrado')


for addr in sys.argv[1:]:
    a = int(addr, 16)
    buscar(bytes([0xCD, a & 0xFF, a >> 8]), f'CALL ${a:04X}')
    buscar(bytes([0xC3, a & 0xFF, a >> 8]), f'JP   ${a:04X}')
