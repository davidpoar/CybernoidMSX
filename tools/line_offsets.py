#!/usr/bin/env python3
"""Para cada linea de la pantalla, busca el desplazamiento de byte que
mejor la hace coincidir con una pantalla de referencia.  Con eso se
deduce como rota la pantalla el juego del Spectrum 48K.
"""
import sys
from collections import Counter
from pathlib import Path


def dir_linea(linea, col):
    return (linea // 8) * 0x100 + (linea % 8) * 0x20 + col


def main():
    captura = Path(sys.argv[1]).read_bytes()[:6144]
    ref = Path(sys.argv[2]).read_bytes()[:6144]

    print('linea  mejor_offset  aciertos   (de 32 bytes por linea)')
    offsets = []
    for i in range(192):
        mejor = (0, -1)
        for off in range(0, 32):
            ok = 0
            for col in range(32):
                # la linea i de la referencia, leida desde la captura
                # desplazada 'off' bytes dentro de la misma interlínea
                li = i
                # el desplazamiento se aplica sobre la direccion
                d = dir_linea(li, 0) + off
                if d + 32 > 6144:
                    continue
                if captura[d + col] == ref[dir_linea(li, col)]:
                    ok += 1
            if ok > mejor[1]:
                mejor = (off, ok)
        offsets.append(mejor[0])
        if i < 40 or i % 16 == 0:
            print(f'  {i:3d}  {mejor[0]:3d}          {mejor[1]:2d}')

    print('\nla secuencia de desplazamientos:')
    for i in range(0, 192, 16):
        print(f'  {i:3d}: ' + ' '.join(f'{o:3d}' for o in offsets[i:i + 16]))
    print('\nlos mas frecuentes:', Counter(offsets).most_common(8))


if __name__ == '__main__':
    main()
