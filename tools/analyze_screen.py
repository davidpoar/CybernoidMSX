#!/usr/bin/env python3
"""Analiza la pantalla cruda del Spectrum: busca la rotacion que
hace coherente la imagen y extrae los tiles de 8x8.

El juego desplaza la pantalla girando las tablas de direcciones de
linea, asi que la imagen en memoria puede estar girada respecto a lo
que se ve.
"""
import sys
from collections import Counter
from pathlib import Path

PALETA = [
    (0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215),
    (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215),
]


def celda(pixels, row, col):
    """Los 8 bytes del patron de una celda (fila, columna)."""
    base = (row // 8) * 0x100 + (row % 8) * 0x20 + col * 8
    return bytes(pixels[base + y] for y in range(8))


def puntuacion(pixels, rows, cols):
    """Cuantos patrones distintos hay: una pantalla coherente tiene
    pocos, una pantalla de ruido tiene muchos."""
    patrones = Counter()
    for r in rows:
        for c in cols:
            patrones[celda(pixels, r, c)] += 1
    return len(patrones)


def main():
    path = Path(sys.argv[1])
    data = path.read_bytes()
    pixels, attrs = data[:6144], data[6144:]

    print(f'pantalla: {path.name}')

    # 1) la imagen tal cual
    print(f'\npatrones distintos sin rotar: {puntuacion(pixels, range(24), range(32))}')

    # 2) rotaciones verticales de 8 lineas
    print('\nrotaciones verticales (multiplos de 8 lineas):')
    mejor = None
    for k in range(24):
        rows = [(r + k) % 24 for r in range(24)]
        p = puntuacion(pixels, rows, range(32))
        print(f'   +{k:2d} lineas: {p} patrones distintos')
        if mejor is None or p < mejor[1]:
            mejor = (k, p)

    # 3) rotaciones verticales de 1 linea
    print('\nlas mejores rotaciones de 1 linea:')
    res = []
    for k in range(192):
        rows = [(r + k) % 24 for r in range(24)]
        p = puntuacion(pixels, rows, range(32))
        res.append((p, k))
    res.sort()
    for p, k in res[:8]:
        print(f'   +{k:3d} lineas: {p} patrones distintos')

    # 4) desplazamientos horizontales
    print('\ndesplazamientos horizontales:')
    res = []
    for dx in range(8):
        cols = [(c + dx) % 32 for c in range(32)]
        p = puntuacion(pixels, range(24), cols)
        res.append((p, dx))
    res.sort()
    for p, dx in res[:4]:
        print(f'   +{dx} columnas: {p} patrones distintos')

    # 5) vuelca la mejor rotacion vertical como texto
    p, k = res[0]
    print(f'\nla mejor rotacion es +{k} lineas ({p} patrones)')
    print('\nla pantalla en esa rotacion (1 = pixel, 0 = fondo):')
    for r in range(24):
        rr = (r + k) % 24
        linea = ''
        for c in range(32):
            patron = celda(pixels, rr, c)
            bits = ''.join(f'{b:08b}' for b in patron)
            linea += bits.replace('0', ' ').replace('1', '#')
        print('  ' + linea)


if __name__ == '__main__':
    main()
