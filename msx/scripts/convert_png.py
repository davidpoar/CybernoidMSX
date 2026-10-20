#!/usr/bin/env python3
"""Convierte una captura PNG del Spectrum en los datos del modo 2 del
MSX.

La idea es mapear cada color de la imagen al color del MSX que mas se
le parece (comparando en RGB), y luego:

  * de cada celda de 8x8 se toma el color mas frecuente como papel y
    el segundo mas frecuente como tinta;
  * cada pixel se enciende si su color esta mas cerca de la tinta
    que del papel.

Con eso se conserva el aspecto de la imagen original aunque una
celda tenga mas de dos colores (el modo 2 del MSX solo tiene tinta y
papel).

Uso:
    py convert_png.py captura.png [salida.bin]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))
from pngreader import leer_png, a_espectro

# La paleta del MSX (los mismos valores que usa el emulador)
PALETA_MSX = [
    (0, 0, 0),        # 0 transparente
    (0, 0, 0),        # 1 negro
    (0, 215, 0),      # 2 verde medio
    (127, 255, 127),  # 3 verde claro
    (0, 0, 215),      # 4 azul oscuro
    (0, 255, 255),    # 5 azul claro
    (215, 0, 0),      # 6 rojo oscuro
    (255, 127, 127),  # 7 gris medio
    (0, 0, 127),      # 8 azul medio
    (0, 127, 255),    # 9 rojo claro
    (127, 127, 127),  # 10 gris oscuro
    (191, 191, 191),  # 11 gris claro
    (0, 127, 0),      # 12 verde oscuro
    (255, 0, 255),    # 13 magenta
    (215, 215, 0),    # 14 amarillo
    (255, 255, 255),  # 15 blanco
]


def mas_cercano(r, g, b):
    """El color del MSX mas parecido."""
    mejor, dist = 1, 1 << 30
    for i, (pr, pg, pb) in enumerate(PALETA_MSX):
        if i == 0:
            continue
        d = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if d < dist:
            dist, mejor = d, i
    return mejor


def convierte(pixeles):
    """Devuelve (nombre, patrones, colores) para el modo 2."""
    nombre = bytearray(768)
    patrones = bytearray(6144)
    colores = bytearray(6144)

    for fila in range(24):
        for col in range(32):
            pix = [pixeles[(fila * 8 + y) * 256 + col * 8 + x]
                   for y in range(8) for x in range(8)]
            cuenta = {}
            for c in pix:
                cuenta[c] = cuenta.get(c, 0) + 1
            # el papel es el color mas frecuente
            papel_rgb = max(cuenta, key=lambda k: cuenta[k])
            tinta_rgb = papel_rgb
            for c in cuenta:
                if c != papel_rgb:
                    tinta_rgb = c
                    break
            papel = mas_cercano(*papel_rgb)
            tinta = mas_cercano(*tinta_rgb)
            if tinta == papel:
                # si los dos son iguales, el texto se ve con el
                # "contraste" de un color claro sobre el fondo
                tinta = 15 if papel != 15 else 14
            color = (tinta << 4) | papel

            destino = (fila // 8) * 2048 + ((fila % 8) * 32 + col) * 8
            base = (fila // 8) * 0x100 + (fila % 8) * 0x20 + col * 8
            for y in range(8):
                b = 0
                for x in range(8):
                    c = pix[y * 8 + x]
                    if mas_cercano(*c) == tinta:
                        b |= 0x80 >> x
                patrones[destino + y] = b
                colores[destino + y] = color
            nombre[fila * 32 + col] = ((fila % 8) * 32 + col) & 0xFF

    return bytes(nombre), bytes(patrones), bytes(colores)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = Path(sys.argv[1])
    ancho, alto, pix = leer_png(src)
    print(f'{src.name}: {ancho}x{alto}')
    ps = a_espectro(ancho, alto, pix)
    nombre, patrones, colores = convierte(ps)
    datos = bytes(nombre) + bytes(patrones) + bytes(colores)
    salida = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix('.bin')
    salida.write_bytes(datos)
    print(f'  {salida}: {len(datos)} bytes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
