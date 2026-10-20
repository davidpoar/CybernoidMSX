#!/usr/bin/env python3
"""Recorta la zona de la pantalla del Spectrum de una captura y la
guarda como un PNG de 256x192."""
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pngreader import leer_png, a_espectro


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
    src = Path(sys.argv[1])
    salida = sys.argv[2] if len(sys.argv) > 2 else 'recorte.png'
    ancho, alto, pix = leer_png(src)
    ps = a_espectro(ancho, alto, pix)
    rgb = bytearray(256 * 192 * 3)
    for i, (r, g, b) in enumerate(ps):
        rgb[i * 3] = r
        rgb[i * 3 + 1] = g
        rgb[i * 3 + 2] = b
    escribir_png(salida, 256, 192, rgb)
    print(f'  {salida} escrito (256x192)')


if __name__ == '__main__':
    main()
