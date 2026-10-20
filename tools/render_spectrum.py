#!/usr/bin/env python3
"""Renderiza un bitmap del Spectrum a PNG usando el mismo renderizador
que el harness, para comprobar si el renderizador es correcto.

Tambien saca los atributos de una captura ya coloreada (el color mas
frecuente de cada celda es el papel y el otro la tinta).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pngreader import PALETA, leer_png, a_espectro, a_bitmap


def atributos_de_colores(pixeles):
    """Deduce los 768 atributos de una captura en color."""
    salida = bytearray(768)
    for fila in range(24):
        for col in range(32):
            cuenta = {}
            for y in range(8):
                for x in range(8):
                    c = pixeles[(fila * 8 + y) * 256 + col * 8 + x]
                    cuenta[c] = cuenta.get(c, 0) + 1
            # el color mas frecuente es el papel
            papel = max(cuenta, key=lambda k: cuenta[k])
            tinta = papel
            for c in cuenta:
                if c != papel:
                    tinta = c
                    break
            ip = PALETA.index(papel) if papel in PALETA else 0
            it = PALETA.index(tinta) if tinta in PALETA else 0
            salida[fila * 32 + col] = it | (ip << 3)
    return bytes(salida)


def render(bitmap, attrs, destino):
    """Escribe un PNG con el mismo criterio que el harness."""
    import zlib
    import struct
    w = h = 256
    rgb = bytearray(w * h * 3)
    for row in range(24):
        for col in range(32):
            a = attrs[row * 32 + col]
            ink = a & 7
            paper = (a >> 3) & 7
            for y in range(8):
                addr = (row // 8) * 0x100 + (row % 8) * 0x20 + col * 8
                b = bitmap[addr + y]
                for x in range(8):
                    on = (b & (0x80 >> x)) != 0
                    c = PALETA[ink if on else paper]
                    o = ((row * 8 + y) * w + col * 8 + x) * 3
                    rgb[o], rgb[o + 1], rgb[o + 2] = c
    # PNG
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgb[y * w * 3:(y + 1) * w * 3]
    def chunk(tipo, datos):
        c = struct.pack('>I', len(datos)) + tipo + datos
        return c + struct.pack('>I', zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    Path(destino).write_bytes(png)
    print(f'  escrito {destino}')


def main():
    if sys.argv[1] == '--de-png':
        ancho, alto, pix = leer_png(sys.argv[2])
        ps = a_espectro(ancho, alto, pix)
        bm = a_bitmap(ps)
        at = atributos_de_colores(ps)
        render(bm, at, sys.argv[3] if len(sys.argv) > 3 else 'render.png')
    else:
        d = Path(sys.argv[1]).read_bytes()
        render(d[:6144], d[6144:],
               sys.argv[2] if len(sys.argv) > 2 else 'render.png')


if __name__ == '__main__':
    main()


