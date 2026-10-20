#!/usr/bin/env python3
"""Un decodificador de PNG minimo (sin dependencias) y utilidades para
comparar capturas del Spectrum con las del original.

Soporta los PNG de 8 bits con paleta y de 24 bits RGB, sin entrelazado,
que es lo que usan las capturas de archive.org.
"""
import struct
import zlib
from pathlib import Path

# La paleta del Spectrum
PALETA = [
    (0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215),
    (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215),
]


def leer_png(ruta):
    """Devuelve (ancho, alto, pixeles RGB como lista de tuplas)."""
    datos = Path(ruta).read_bytes()
    if datos[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('no es un PNG')

    pos = 8
    idat = b''
    paleta = None
    while pos < len(datos):
        (largo,) = struct.unpack('>I', datos[pos:pos + 4])
        tipo = datos[pos + 4:pos + 8]
        cuerpo = datos[pos + 8:pos + 8 + largo]
        if tipo == b'IHDR':
            ancho, alto, bits, color, comp, filt, entre = \
                struct.unpack('>IIBBBBB', cuerpo)
            if bits != 8:
                raise ValueError(f'solo 8 bits por canal, no {bits}')
            if entre:
                raise ValueError('PNG entrelazado no soportado')
            canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
        elif tipo == b'PLTE':
            paleta = [tuple(cuerpo[i:i + 3]) for i in range(0, len(cuerpo), 3)]
        elif tipo == b'IDAT':
            idat += cuerpo
        elif tipo == b'IEND':
            break
        pos += 12 + largo

    crudo = zlib.decompress(idat)
    bpp = canales
    paso = ancho * bpp
    lineas = []
    prev = bytearray(paso)
    p = 0
    for y in range(alto):
        f = crudo[p]
        p += 1
        linea = bytearray(crudo[p:p + paso])
        p += paso
        if f == 1:
            for i in range(bpp, paso):
                linea[i] = (linea[i] + linea[i - bpp]) & 0xFF
        elif f == 2:
            for i in range(paso):
                linea[i] = (linea[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(paso):
                a = linea[i - bpp] if i >= bpp else 0
                linea[i] = (linea[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(paso):
                a = linea[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                linea[i] = (linea[i] + pr) & 0xFF
        lineas.append(linea)
        prev = linea

    pixeles = []
    for y in range(alto):
        fila = lineas[y]
        for x in range(ancho):
            v = fila[x * bpp]
            if color == 3:
                pixeles.append(paleta[v])
            elif color == 0:
                pixeles.append((v, v, v))
            else:
                pixeles.append((fila[x * bpp], fila[x * bpp + 1], fila[x * bpp + 2]))
    return ancho, alto, pixeles


def a_espectro(ancho, alto, pixeles, escala=2):
    """Recorta la parte de la pantalla del Spectrum de una captura
    ampliada y la devuelve en el formato del Spectrum (1 bit por pixel)."""
    # la parte jugable esta centrada: se busca el rectangulo no negro
    minx, miny, maxx, maxy = ancho, alto, -1, -1
    for y in range(alto):
        for x in range(ancho):
            r, g, b = pixeles[y * ancho + x]
            if r + g + b > 60:
                if x < minx: minx = x
                if x > maxx: maxx = x
                if y < miny: miny = y
                if y > maxy: maxy = y
    if maxx < 0:
        raise ValueError('la imagen esta toda negra')

    # la region Spectrum es de 256x192, con una relacion 4:3
    w = maxx - minx + 1
    h = maxy - miny + 1
    print(f'  la zona con color va de ({minx},{miny}) a ({maxx},{maxy}) '
          f'= {w}x{h}')

    # la region Spectrum es de 256x192, escalada
    ancho_espectro = 256 * escala
    alto_espectro = 192 * escala
    x0 = minx
    y0 = miny
    if x0 + ancho_espectro > ancho or y0 + alto_espectro > alto:
        x0 = max(0, min(x0, ancho - ancho_espectro))
        y0 = max(0, min(y0, alto - alto_espectro))

    pixeles_spectrum = []
    for y in range(192):
        for x in range(256):
            r, g, b = pixeles[(y0 + y * escala) * ancho + (x0 + x * escala)]
            pixeles_spectrum.append((r, g, b))
    return pixeles_spectrum


def a_bitmap(pixeles, colores=PALETA):
    """Convierte a los 6144 bytes del Spectrum (1 bit por pixel).

    El bit se pone a 1 cuando el pixel esta mas cerca del color de
    tinta de su celda que del de papel: asi el resultado se ve igual
    que la captura original aunque una celda tenga mas de dos
    colores.
    """
    def distancia(c, ref):
        return (c[0] - ref[0]) ** 2 + (c[1] - ref[1]) ** 2 + (c[2] - ref[2]) ** 2

    salida = bytearray(6144)
    for fila in range(24):
        for col in range(32):
            # los dos colores de la celda
            cuenta = {}
            for y in range(8):
                for x in range(8):
                    c = pixeles[(fila * 8 + y) * 256 + col * 8 + x]
                    cuenta[c] = cuenta.get(c, 0) + 1
            papel = max(cuenta, key=lambda k: cuenta[k])
            tinta = papel
            for c in cuenta:
                if c != papel:
                    tinta = c
                    break
            base = (fila // 8) * 0x100 + (fila % 8) * 0x20 + col * 8
            for y in range(8):
                b = 0
                for x in range(8):
                    c = pixeles[(fila * 8 + y) * 256 + col * 8 + x]
                    if distancia(c, tinta) < distancia(c, papel):
                        b |= 0x80 >> x
                salida[base + y] = b
    return bytes(salida)


if __name__ == '__main__':
    import sys
    ancho, alto, pix = leer_png(sys.argv[1])
    print(f'{sys.argv[1]}: {ancho}x{alto}')
    ps = a_espectro(ancho, alto, pix)
    bm = a_bitmap(ps)
    Path(sys.argv[2] if len(sys.argv) > 2 else 'captura.bin').write_bytes(bm)
    print(f'  bitmap de {len(bm)} bytes escrito')
