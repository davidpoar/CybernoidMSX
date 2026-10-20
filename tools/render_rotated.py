#!/usr/bin/env python3
"""Renderiza la pantalla del Spectrum usando la tabla de direcciones de
linea que mantiene el juego (el truco de rotacion de pantalla del
Spectrum 48K) y la compara con la captura original.
"""
import sys
from pathlib import Path


def main():
    tabla_path = Path(sys.argv[1])
    captura = Path(sys.argv[2])
    real = Path(sys.argv[3]) if len(sys.argv) > 3 else None

    tabla = tabla_path.read_bytes()
    # 192 entradas de 2 bytes: la direccion de cada linea de barrido
    lineas = [tabla[i] | (tabla[i + 1] << 8) for i in range(0, 384, 2)]
    print('las 32 primeras entradas:')
    print('  ' + ' '.join(f'${v:04X}' for v in lineas[:32]))
    print('  ' + ' '.join(f'${v:04X}' for v in lineas[32:64]))

    # renderiza: la linea i de la pantalla son los 32 bytes desde lineas[i]
    img = captura.read_bytes()
    pix = img[:6144]
    salida = bytearray(6144)
    for i in range(192):
        base = lineas[i] - 0x4000
        if not (0 <= base <= 6144 - 32):
            continue
        # la linea i de la pantalla va a la posicion estandar
        destino = (i // 8) * 0x100 + (i % 8) * 0x20
        for k in range(32):
            salida[destino + k] = pix[base + k]

    # compara con la referencia
    if real:
        ref = real.read_bytes()[:6144]
        ok = sum(1 for a, b in zip(salida, ref) if a == b)
        print(f'\nbytes iguales con la referencia: {ok} de 6144 '
              f'({ok / 6144 * 100:.1f}%)')
        # sin rotar
        ok2 = sum(1 for a, b in zip(pix, ref) if a == b)
        print(f'sin rotar:                      {ok2} de 6144 '
              f'({ok2 / 6144 * 100:.1f}%)')

    Path(sys.argv[4] if len(sys.argv) > 4 else 'rotada.bin').write_bytes(salida)
    print(f'\nwritten rotada.bin ({len(salida)} bytes)')


if __name__ == '__main__':
    main()
