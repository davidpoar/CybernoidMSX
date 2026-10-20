#!/usr/bin/env python3
"""Compara dos capturas de la pantalla del Spectrum celda a celda."""
import sys
from pathlib import Path


def celda(px, row, col):
    base = (row // 8) * 0x100 + (row % 8) * 0x20 + col * 8
    return [px[base + y] for y in range(8)]


def dibuja(px, row, col):
    c = celda(px, row, col)
    return '|'.join(''.join('#' if (c[y] >> (7 - x)) & 1 else '.'
                            for x in range(8)) for y in range(8))


def main():
    a = Path(sys.argv[1]).read_bytes()[:6144]
    b = Path(sys.argv[2]).read_bytes()[:6144]
    iguales = sum(1 for x, y in zip(a, b) if x == y)
    print(f'bytes iguales: {iguales} de 6144')

    mostradas = 0
    for row in range(24):
        for col in range(32):
            if celda(a, row, col) != celda(b, row, col):
                if mostradas < 4:
                    print(f'\nfila {row} columna {col}:')
                    print('  A:', dibuja(a, row, col))
                    print('  B:', dibuja(b, row, col))
                mostradas += 1
    print(f'\nceldas distintas: {mostradas} de 768')


if __name__ == '__main__':
    main()
