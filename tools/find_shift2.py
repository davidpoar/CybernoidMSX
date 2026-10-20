#!/usr/bin/env python3
"""Prueba todos los desplazamientos de pixel (linea y columna) para ver
si una captura del Spectrum esta desplazada respecto a otra.

El Spectrum guarda las lineas entrelazadas, asi que el desplazamiento
vertical se hace sobre la linea de la interlínea y el horizontal sobre
la columna del patron.
"""
import sys
from pathlib import Path


def direccion(linea, col):
    """La direccion del byte 'col' (0-31) de la linea 'linea' (0-191)."""
    return (linea // 8) * 0x100 + (linea % 8) * 0x20 + col


def main():
    a = Path(sys.argv[1]).read_bytes()[:6144]
    b = Path(sys.argv[2]).read_bytes()[:6144]

    mejor = (0, 0, -1)
    for dy in range(-8, 9):
        for dx in range(-4, 5):
            ok = tot = 0
            for linea in range(0, 192, 2):
                l2 = linea + dy
                if not (0 <= l2 < 192):
                    continue
                for col in range(0, 32):
                    c2 = col + dx
                    if not (0 <= c2 < 32):
                        continue
                    tot += 1
                    if a[direccion(linea, col)] == b[direccion(l2, c2)]:
                        ok += 1
            if tot and ok / tot > mejor[2]:
                mejor = (dx, dy, ok / tot)
    dx, dy, pct = mejor
    print(f'mejor: dx={dx} bytes dy={dy} lineas -> {pct * 100:.1f}%')

    ok = tot = 0
    for linea in range(0, 192, 2):
        for col in range(0, 32):
            tot += 1
            if a[direccion(linea, col)] == b[direccion(linea, col)]:
                ok += 1
    print(f'sin desplazamiento: {ok / tot * 100:.1f}%')


if __name__ == '__main__':
    main()
