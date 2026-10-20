#!/usr/bin/env python3
"""Convierte la pantalla del Spectrum en los datos de la ROM MSX.

La pantalla del Spectrum son 6144 bytes de pixeles (1 bit por pixel) y
768 bytes de atributos.  El modo grafico 2 del MSX usa:

  VRAM $0000-$17FF  tabla de patrones  (6 KB)
  VRAM $1800-$1AFF  tabla de nombres    (768 indices)
  VRAM $2000-$37FF  tabla de colores    (6 KB)

Los pixeles no hay que convertirlos: un patron del TMS9918 son 8 bytes
con 1 bit por pixel, igual que una celda del Spectrum.  Lo que hay que
convertir son los atributos, porque el Spectrum guarda la tinta y el
papel en un byte y el MSX los quiere en dos nibbles de otra tabla, y
ademas los numeros de color son distintos.

El layout de la tabla de nombres del MSX es la secuencia 0 a 255
repetida tres veces, de modo que el patron de la celda (columna, fila)
esta en:

  patron = (fila/8)*$800 + (fila%8)*$100 + columna*8
  color  = $2000 + (fila/8)*$800 + (fila%8)*$100 + columna*8

Uso:
    py convert_spectrum.py pantalla.raw [salida.bin]
"""
import sys
from pathlib import Path

# La paleta del Spectrum y su equivalente en el MSX.
# Spectrum: 0 negro, 1 azul, 2 rojo, 3 magenta, 4 verde, 5 cian,
#           6 amarillo, 7 blanco
# MSX:      1 negro, 8 azul medio, 9 rojo claro, 13 magenta,
#           2 verde medio, 5 azul claro, 14 amarillo, 15 blanco
#
# Con el bit de "brillo" del Spectrum se usa la variante mas clara
# del MSX cuando existe.
MSX_NORMAL = [1, 8, 9, 13, 2, 5, 14, 15]
MSX_BRIGHT = [1, 5, 9, 13, 3, 5, 14, 15]


def convierte(bitmap, attrs, escala=1):
    """Devuelve (nombre, patrones, colores) para el modo 2 del MSX."""
    nombre = bytearray(768)
    patrones = bytearray(6144)
    colores = bytearray(6144)

    for fila in range(24):
        for col in range(32):
            attr = attrs[fila * 32 + col]
            tinta = attr & 7
            papel = (attr >> 3) & 7
            brillo = (attr & 0x80) != 0

            # la tinta y el papel del MSX
            t_msx = (MSX_BRIGHT if brillo else MSX_NORMAL)[tinta]
            p_msx = MSX_NORMAL[papel]
            color = (t_msx << 4) | p_msx

            # la posicion en las tablas del MSX
            zona = fila // 8
            patron_idx = ((fila % 8) * 32 + col) * 8
            destino = zona * 2048 + patron_idx

            # los 8 bytes del patron: la misma disposicion que el
            # Spectrum, solo hay que separarlos por lineas
            base = (fila // 8) * 0x100 + (fila % 8) * 0x20 + col * 8
            for y in range(8):
                patrones[destino + y] = bitmap[base + y]
                colores[destino + y] = color

            # el indice del nombre
            nombre[fila * 32 + col] = ((fila % 8) * 32 + col) & 0xFF

    return bytes(nombre), bytes(patrones), bytes(colores)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = Path(sys.argv[1])
    data = src.read_bytes()
    bitmap, attrs = data[:6144], data[6144:]
    nombre, patrones, colores = convierte(bitmap, attrs)

    salida = bytes(nombre) + bytes(patrones) + bytes(colores)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_bytes(salida)
        print(f'{src.name} -> {sys.argv[2]} ({len(salida)} bytes)')
    else:
        print(f'{src.name}: {len(salida)} bytes '
              f'(nombres {len(nombre)}, patrones {len(patrones)}, '
              f'colores {len(colores)})')

    # un resumen de los tiles distintos
    tiles = set()
    for i in range(0, 6144, 8):
        tiles.add(patrones[i:i + 8])
    colores_distintos = len(set(colores))
    print(f'  {len(tiles)} patrones distintos, '
          f'{colores_distintos} colores distintos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
