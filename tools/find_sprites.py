#!/usr/bin/env python3
"""Busca sprites en la imagen de memoria del juego.

Un sprite del Spectrum son 8 bytes (uno por linea) y casi todos los
objetos del juego (la nave, los enemigos) son simetricos respecto al
eje vertical, asi que se pueden localizar de forma objetiva.
"""
import sys
from pathlib import Path

IMG = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin')
BASE = 0x4000


def dibuja(bloque):
    return [''.join('#' if (b & (0x80 >> x)) else '.' for x in range(8))
            for b in bloque]


def main():
    img = IMG.read_bytes()
    ancho = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    minimo = int(sys.argv[2]) if len(sys.argv) > 2 else 2

    print(f'buscando bloques de {ancho} bytes simetricos '
          f'(al menos {minimo} pixeles)\n')

    encontrados = []
    for i in range(0, len(img) - ancho + 1):
        bloque = img[i:i + ancho]
        if not any(bloque):
            continue
        if bloque != bloque[::-1]:
            continue
        pixeles = sum(bin(b).count('1') for b in bloque)
        if pixeles < minimo:
            continue
        # que no sea un bloque repetido
        if any(img[j:j + ancho] == bloque for j in range(max(0, i - 64), i)):
            continue
        encontrados.append((i, bloque, pixeles))

    print(f'{len(encontrados)} bloques simetricos\n')
    for i, bloque, pixeles in encontrados[:60]:
        print(f'  ${BASE + i:04X}  ({pixeles} pixeles)')
        for l in dibuja(bloque):
            print('      ' + l)
        print()


if __name__ == '__main__':
    main()
