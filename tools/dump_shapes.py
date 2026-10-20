#!/usr/bin/env python3
"""Busca formas de 8x8 y 16x16 en un volcado de RAM del Spectrum.

Los sprites del juego se guardan como tablas de bitmap: 8 bytes por
patron de 8x8.  Este script busca bloques que parezcan formas y los
dibuja con caracteres para poder reconocerlos.
"""
import sys
from pathlib import Path


def dibujo(bits, ancho=8, alto=8):
    lineas = []
    for y in range(alto):
        linea = ''
        for x in range(ancho):
            b = bits[y * ancho + x]
            linea += '#' if (b & (0x80 >> x)) else '.'
        lineas.append(linea)
    return lineas


def main():
    path = Path(sys.argv[1])
    data = path.read_bytes()
    base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x5F00
    tam = int(sys.argv[3], 16) if len(sys.argv) > 3 else 8

    print(f'{path.name}: {len(data)} bytes desde ${base:04X}')
    print('\nla zona como mapa de bits (8 bytes por linea = 8 pixels):')
    for i in range(0, len(data) - 7, 8):
        fila = data[i:i + 8]
        bits = ''.join(f'{b:08b}' for b in fila)
        print(f'  ${base + i:04X}: {bits}')

    # busca los bloques de 8x8 con algun pixel puesto
    print('\npatrones de 8x8 con pixels:')
    for i in range(0, len(data) - 7, 8):
        patron = data[i:i + 8]
        if any(patron):
            print(f'  ${base + i:04X}:')
            for l in dibujo(patron):
                print('      ' + l)


if __name__ == '__main__':
    main()
