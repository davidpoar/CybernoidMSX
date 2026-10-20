#!/usr/bin/env python3
"""Muestra la diferencia entre dos capturas de la pantalla del Spectrum.

Sirve para ver que se mueve: la nave, los enemigos, el fondo.
"""
import sys
from pathlib import Path


def carga(path):
    d = Path(path).read_bytes()
    return d[:6144], d[6144:]


def main():
    a = sys.argv[1]
    b = sys.argv[2]
    px1, at1 = carga(a)
    px2, at2 = carga(b)

    print(f'diferencia entre {Path(a).name} y {Path(b).name}\n')
    for fila in range(24):
        linea = ''
        for col in range(32):
            i = (fila // 8) * 0x100 + (fila % 8) * 0x20 + col * 8
            p1 = px1[i:i + 8]
            p2 = px2[i:i + 8]
            if p1 == p2 and at1[fila * 32 + col] == at2[fila * 32 + col]:
                linea += '.'
            else:
                # quantas lineas cambian dentro de la celda
                d = sum(1 for x, y in zip(p1, p2) if x != y)
                linea += ' ' if d == 0 else ('+' if d < 8 else '#')
        print(f'  {fila:2d} |{linea}|')

    print('\n  ( . = igual, + = cambia un poco, # = cambia mucho )')


if __name__ == '__main__':
    main()
