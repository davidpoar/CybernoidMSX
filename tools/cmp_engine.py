#!/usr/bin/env python3
"""Compara el motor binario de la ROM actual con el de la version
anterior (en git) y muestra donde cambian."""
import subprocess
import sys
from pathlib import Path

nuevo = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom').read_bytes()
out = subprocess.run(['git', 'show', 'HEAD:msx/build/cybernoid.rom'],
                     capture_output=True, cwd=r'C:\Dev\cybernoidMSX')
viejo = out.stdout
print(f'el motor anterior en git: {len(viejo)} bytes')
if not viejo:
    sys.exit('no hay motor anterior en git')

n = min(len(viejo), 0x900)
diferencias = [i for i in range(n) if viejo[i] != nuevo[i]]
print(f'los primeros {n} bytes difieren en {len(diferencias)} posiciones')
if diferencias:
    print(f'la primera diferencia esta en el offset ${diferencias[0]:04X} '
          f'(direccion ${0x4000 + diferencias[0]:04X})')
    ini = max(0, diferencias[0] - 16)
    for i in range(ini, min(n, ini + 64), 16):
        a = viejo[i:i + 16].hex(' ')
        b = nuevo[i:i + 16].hex(' ')
        marca = '  <-- DISTINTO' if viejo[i:i + 16] != nuevo[i:i + 16] else ''
        print(f'  ${0x4000 + i:04X} viejo: {a}')
        print(f'           nuevo: {b}{marca}')
