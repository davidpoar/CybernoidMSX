#!/usr/bin/env python3
"""Los datos de pantalla de la ROM MSX de Cybernoid.

La ROM en modo grafico 2 del MSX usa tres tablas en la VRAM:

  $0000-$17FF  tabla de patrones   (6 KB, 3 zonas de 2 KB)
  $1800-$1AFF  tabla de nombres     (768 indices)
  $2000-$37FF  tabla de colores     (6 KB, mapeo byte a byte de la
                                       tabla de patrones)

El codigo de la tabla de nombres elige el patron: la tabla de nombres
se inicializa con la secuencia 0 a 255 repetida tres veces, de modo que
cada celda de la pantalla tiene su propio bloque de 8 bytes de color.

Con eso el indice de un patron es:

  zona   = fila / 8
  patron = (fila % 8) * 32 + columna
  bytes  = zona * 2048 + patron * 8
"""
from pathlib import Path

# El mapa de la paleta del Spectrum al MSX.
# Spectrum: 0 negro, 1 azul, 2 rojo, 3 magenta, 4 verde, 5 cian, 6 amarillo, 7 blanco
# MSX:      1 negro, 8 azul medio, 9 rojo claro, 13 magenta,
#           2 verde medio, 5 azul claro, 14 amarillo, 15 blanco
from pathlib import Path

SPECTRUM_TO_MSX = [1, 8, 9, 13, 2, 5, 14, 15]

NAME_TABLE_SIZE = 768
PATTERN_TABLE_SIZE = 6144
COLOUR_TABLE_SIZE = 6144
SCREEN_DATA_SIZE = (NAME_TABLE_SIZE + PATTERN_TABLE_SIZE + COLOUR_TABLE_SIZE)


def name_table():
    """La tabla de nombres: la secuencia 0-255 repetida tres veces."""
    return bytes(i & 0xFF for i in range(NAME_TABLE_SIZE))


def cell_position(index):
    """La posicion en pantalla de un indice de patron.

    El indice es zona * 256 + patron, y el patron es (fila%8)*32 + col.
    """
    zone = index >> 8
    pattern = index & 0xFF
    col = pattern & 0x1F
    row = (pattern >> 5) & 0x07
    return col, row, zone * 8 + row


def build_test_screen():
    """Una pantalla de prueba: un degradado de color con una diagonal.

    Sirve para comprobar que la ROM arranca, que la tabla de nombres,
    la de patrones y la de colores estan en su sitio y que el VDP
    dibuja lo que le decimos.
    """
    patterns = bytearray(PATTERN_TABLE_SIZE)
    colours = bytearray(COLOUR_TABLE_SIZE)

    for index in range(768):
        col, row, screen_row = cell_position(index)

        # El patron: una diagonal que cruza la celda.
        for y in range(8):
            patterns[index * 8 + y] = 0x80 >> ((col + y) & 7)

        # El color: un degradado que depende de la columna y de la fila.
        ink = 1 + ((col + screen_row) & 7)
        paper = 1
        value = (ink << 4) | paper
        for y in range(8):
            colours[index * 8 + y] = value

    return name_table() + bytes(patterns) + bytes(colours)


def build_blank_sprites(size=2304):
    """Zeros para las tablas de sprites."""
    return bytes(size)


def build_bank1():
    """El contenido del banco 1: la pantalla y las tablas de sprites."""
    data = build_test_screen() + build_blank_sprites()
    return data


def load_converted(name='cybernoid_screen.bin'):
    """Los datos ya convertidos de la pantalla original del Spectrum.

    Se generan con convert_spectrum.py a partir de una captura de la
    pantalla del juego (msx/test con CYBERNOID_SPECTRUM=1).  Si el
    fichero no existe se cae en la pantalla de prueba.
    """
    path = Path(__file__).parent.parent / 'assets' / name
    if path.exists():
        data = path.read_bytes()
        if len(data) == SCREEN_DATA_SIZE:
            return data + build_blank_sprites()
        print(f'  AVISO: {path.name} tiene {len(data)} bytes, '
              f'se esperaban {SCREEN_DATA_SIZE}')
    return build_bank1()


if __name__ == '__main__':
    d = build_bank1()
    print(f'banco 1: {len(d)} bytes')
