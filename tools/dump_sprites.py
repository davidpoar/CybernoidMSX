#!/usr/bin/env python3
"""Dibuja los sprites de la zona de sprites del Spectrum."""
import sys
from pathlib import Path

path = Path(sys.argv[1])
base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x5F00
datos = path.read_bytes()


def dibujo(forma):
    lineas = []
    for y in range(8):
        linea = ''
        for x in range(8):
            linea += '#' if (forma[y] & (0x80 >> x)) else '.'
        lineas.append(linea)
    return lineas


def prueba(i, paso):
    """Prueba las posibles estructuras: 8 bytes de forma + 1 de mascara,
    o 16 bytes de forma (16x8), o bloques de 8."""
    for etiqueta, tam in (('8x8+1', 9), ('8x8', 8)):
        print(f'\n=== estructura {etiqueta} desde ${base + i:04X} ===')
        for n in range(4):
            off = i + n * tam
            if off + 8 > len(datos):
                break
            forma = datos[off:off + 8]
            extra = ''
            if tam == 9 and off + 8 < len(datos):
                extra = f'  mascara=${datos[off + 8]:02X}'
            print(f'  sprite {n} en ${base + off:04X}{extra}')
            for l in dibujo(forma):
                print('      ' + l)


if __name__ == '__main__':
    inicio = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x80
    prueba(inicio, 9)
