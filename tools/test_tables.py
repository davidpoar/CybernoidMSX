#!/usr/bin/env python3
"""Prueba las dos tablas de direcciones de pantalla del juego."""
import sys
from pathlib import Path


def main():
    tabla = Path(sys.argv[1]).read_bytes()
    captura = Path(sys.argv[2]).read_bytes()[:6144]
    ref = Path(sys.argv[3]).read_bytes()[:6144]

    def prueba(datos, etiqueta):
        lineas = [datos[i] | (datos[i + 1] << 8) for i in range(0, 384, 2)]
        salida = bytearray(6144)
        for i in range(192):
            b = lineas[i] - 0x4000
            if not (0 <= b <= 6144 - 32):
                continue
            d = (i // 8) * 0x100 + (i % 8) * 0x20
            for k in range(32):
                salida[d + k] = captura[b + k]
        ok = sum(1 for a, b in zip(salida, ref) if a == b)
        primeros = ' '.join('$' + format(v, '04X') for v in lineas[:8])
        print(f'{etiqueta}: {ok} de 6144 ({ok / 6144 * 100:.1f}%)  {primeros}')
        return ok

    prueba(tabla, 'tabla A')
    prueba(tabla[0x100:], 'tabla B')
    ok = sum(1 for a, b in zip(captura, ref) if a == b)
    print(f'sin rotar: {ok} de 6144 ({ok / 6144 * 100:.1f}%)')


if __name__ == '__main__':
    main()
