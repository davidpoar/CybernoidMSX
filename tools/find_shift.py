#!/usr/bin/env python3
"""Busca el desplazamiento (x,y) que mejor hace coincidir dos capturas
de la pantalla del Spectrum.  Sirve para saber si una imagen esta
desplazada o si son contenidos distintos.
"""
import sys
from pathlib import Path


def celda(px, row, col):
    base = (row // 8) * 0x100 + (row % 8) * 0x20 + col * 8
    return bytes(px[base + y] for y in range(8))


def main():
    a = Path(sys.argv[1]).read_bytes()[:6144]
    b = Path(sys.argv[2]).read_bytes()[:6144]

    mejor = (0, 0, -1)
    for dy in range(-12, 13):
        for dx in range(-12, 13):
            ok = 0
            total = 0
            for row in range(0, 24, 2):
                for col in range(0, 32, 2):
                    r2 = row + dy
                    c2 = col + dx
                    if not (0 <= r2 < 24 and 0 <= c2 < 32):
                        continue
                    total += 1
                    if celda(a, row, col) == celda(b, r2, c2):
                        ok += 1
            if total and ok / total > mejor[2]:
                mejor = (dx, dy, ok / total)
    dx, dy, pct = mejor
    print(f'el mejor desplazamiento es dx={dx} dy={dy} con un '
          f'{pct * 100:.1f}% de celdas iguales')
    print(f'sin desplazamiento: ', end='')
    ok = total = 0
    for row in range(0, 24, 2):
        for col in range(0, 32, 2):
            total += 1
            if celda(a, row, col) == celda(b, row, col):
                ok += 1
    print(f'{ok / total * 100:.1f}%')


if __name__ == '__main__':
    main()
