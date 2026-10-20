#!/usr/bin/env python3
"""Renderiza los datos del modo 2 de la ROM (la tabla de nombres, la de
patrones y la de colores) tal y como lo haria el VDP.

Sirve para comprobar la conversion sin depender del emulador.
"""
import struct
import sys
import zlib
from pathlib import Path

PALETA = [
    (0, 0, 0), (0, 0, 0), (0, 215, 0), (127, 255, 127),
    (0, 0, 215), (0, 255, 255), (215, 0, 0), (255, 127, 127),
    (0, 0, 127), (0, 127, 255), (127, 127, 127), (191, 191, 191),
    (0, 127, 0), (255, 0, 255), (215, 215, 0), (255, 255, 255),
]


def escribir_png(ruta, ancho, alto, rgb):
    raw = bytearray()
    for y in range(alto):
        raw.append(0)
        raw += rgb[y * ancho * 3:(y + 1) * ancho * 3]

    def chunk(tipo, datos):
        return (struct.pack('>I', len(datos)) + tipo + datos +
                struct.pack('>I', zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', ancho, alto, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    Path(ruta).write_bytes(png)


def main():
    datos = Path(sys.argv[1]).read_bytes()
    salida = sys.argv[2] if len(sys.argv) > 2 else 'modo2.png'
    nombres = datos[0:768]
    patrones = datos[768:768 + 6144]
    colores = datos[768 + 6144:768 + 6144 * 2]

    rgb = bytearray(256 * 192 * 3)
    for row in range(24):
        zona = row // 8
        for col in range(32):
            num = nombres[row * 32 + col]
            indice = zona * 256 + num
            for y in range(8):
                pb = patrones[(indice * 8 + y) & 0x1FFF]
                cb = colores[(indice * 8 + y) & 0x1FFF]
                fg = PALETA[cb >> 4]
                bg = PALETA[cb & 0x0F]
                for x in range(8):
                    on = (pb & (0x80 >> x)) != 0
                    c = fg if on else bg
                    o = ((row * 8 + y) * 256 + col * 8 + x) * 3
                    rgb[o], rgb[o + 1], rgb[o + 2] = c
    escribir_png(salida, 256, 192, rgb)
    print(f'  {salida} escrito')


if __name__ == '__main__':
    main()
