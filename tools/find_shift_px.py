#!/usr/bin/env python3
"""Busca el desplazamiento en pixels entre dos capturas del Spectrum.

El Spectrum guarda las lineas entrelazadas, asi que el desplazamiento
se hace sobre las coordenadas de pixel y no sobre los bytes.
"""
import sys
from pathlib import Path


def pixeles(px):
    """Devuelve una matriz 192x256 con el valor 0 o 1 de cada pixel."""
    m = [[0] * 256 for _ in range(192)]
    for row in range(24):
        for col in range(32):
            base = (row // 8) * 0x100 + (row % 8) * 0x20 + col * 8
            for y in range(8):
                b = px[base + y]
                for x in range(8):
                    m[row * 8 + y][col * 8 + x] = (b >> (7 - x)) & 1
    return m


def main():
    a = pixeles(Path(sys.argv[1]).read_bytes()[:6144])
    b = pixeles(Path(sys.argv[2]).read_bytes()[:6144])

    mejor = (0, 0, -1)
    for dy in range(-12, 13):
        for dx in range(-12, 13):
            ok = tot = 0
            for y in range(16, 176):
                for x in range(16, 240):
                    y2, x2 = y + dy, x + dx
                    if not (0 <= y2 < 192 and 0 <= x2 < 256):
                        continue
                    tot += 1
                    if a[y][x] == b[y2][x2]:
                        ok += 1
            if tot and ok / tot > mejor[2]:
                mejor = (dx, dy, ok / tot)
    dx, dy, pct = mejor
    print(f'mejor desplazamiento: dx={dx} dy={dy}  ({pct * 100:.1f}% de pixeles)')

    # y tambien el color medio de la coincidencia
    ok = tot = 0
    for y in range(16, 176):
        for x in range(16, 240):
            y2, x2 = y + dy, x + dx
            if not (0 <= y2 < 192 and 0 <= x2 < 256):
                continue
            tot += 1
            if a[y][x] == b[y2][x2]:
                ok += 1
    print(f'sin desplazamiento: {ok / tot * 100:.1f}%')


if __name__ == '__main__':
    main()
