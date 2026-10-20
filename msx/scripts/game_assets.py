#!/usr/bin/env python3
"""Los assets del juego para la ROM MSX: el fondo, los digitos del
marcador y los sprites.

El fondo de Cybernoid no hace scroll: cada habitacion es una
pantalla completa, asi que aqui solo hace falta un campo de
estrellas.

El marcador (la puntuacion) va en las cinco primeras celdas de la
primera fila, con los digitos 0 a 9 en los diez primeros patrones
de la primera zona.  El resto de la primera fila usa los
patrones 10 a 31, de modo que no se mezclan.

Los sprites van en la zona de patrones de sprites ($3800): cuatro
bloques de 8x8 para la nave de 16x16, uno para la bala, tres para
los enemigos y cuatro para las explosiones.
"""

# Los digitos: 5 de ancho y 7 de alto, dentro de la celda de 8x8
DIGITOS = {
    '0': ['.###.', '#...#', '#..##', '#.#.#', '##..#', '#...#', '.###.'],
    '1': ['..#..', '.##..', '..#..', '..#..', '..#..', '..#..', '.###.'],
    '2': ['.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'],
    '3': ['#####', '...#.', '..#..', '...#.', '....#', '#...#', '.###.'],
    '4': ['...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'],
    '5': ['#####', '#....', '####.', '....#', '....#', '#...#', '.###.'],
    '6': ['..##.', '.#...', '#....', '####.', '#...#', '#...#', '.###.'],
    '7': ['#####', '....#', '...#.', '..#..', '.#...', '.#...', '.#...'],
    '8': ['.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'],
    '9': ['.###.', '#...#', '#...#', '.####', '....#', '...#.', '.##..'],
}

# La nave del jugador: 16x16
NAVE = [
    '................',
    '.....######.....',
    '....##....##....',
    '...##......##...',
    '..##..####..##..',
    '..##..####..##..',
    '..##........##..',
    '..###......###..',
    '...##......##...',
    '...###....###...',
    '....##....##....',
    '....########....',
    '.....######.....',
    '......####......',
    '.......##.......',
    '................',
]

# Los enemigos, de 8x8
ENEMIGO_DRON = [
    '..####..',
    '.#....#.',
    '#..##..#',
    '#......#',
    '#..##..#',
    '.#....#.',
    '..####..',
    '........',
]

ENEMIGO_ALA = [
    '...#....',
    '..##....',
    '.###....',
    '####....',
    '###.....',
    '##......',
    '#.......',
    '........',
]

ENEMIGO_BOMBA = [
    '..####..',
    '.#....#.',
    '#..##..#',
    '#.####.#',
    '#.####.#',
    '#..##..#',
    '.#....#.',
    '..####..',
]

# La bala del jugador
BALA = [
    '...##...',
    '...##...',
    '...##...',
    '...##...',
    '...##...',
    '...##...',
    '........',
    '........',
]

# Las explosiones (4 fotogramas)
EXPLOSION = [
    ['........', '........', '...##...', '...##...', '...##...', '...##...',
     '........', '........'],
    ['........', '..#..#..', '.#....#.', '..#..#..', '..#..#..', '.#....#.',
     '..#..#..', '........'],
    ['..#..#..', '.#....#.', '#..##..#', '#..##..#', '#..##..#', '#..##..#',
     '.#....#.', '..#..#..'],
    ['##.##.##', '#.####.#', '##.##.##', '.######.', '.######.', '##.##.##',
     '#.####.#', '##.##.##'],
]


def patron_de(lineas):
    """Convierte unas lineas de texto en los 8 bytes de un patron.
    Las lineas mas cortas se alinean a la izquierda."""
    salida = bytearray(8)
    for y in range(8):
        linea = lineas[y] if y < len(lineas) else ''
        linea = linea.ljust(8)[:8]
        v = 0
        for x, c in enumerate(linea):
            if c != ' ':
                v |= 0x80 >> x
        salida[y] = v
    return bytes(salida)


def digitos():
    """Los diez digitos, en los patrones 0 a 9."""
    salida = bytearray(10 * 8)
    for i, d in enumerate('0123456789'):
        salida[i * 8:(i + 1) * 8] = patron_de(DIGITOS[d])
    return bytes(salida)


def estrellas():
    """Un patron de estrella, con la estrella en un sitio distinto.

    Cada patron tiene un solo pixel (mas o menos) para que el fondo
    parezca un campo de estrellas y no un mosaico.
    """
    patrons = []
    for v in range(4):
        lineas = ['........'] * 8
        x = (1 + v * 3) % 8
        y = (2 + v * 5) % 8
        linea = list(lineas[y])
        linea[x] = '#'
        lineas[y] = ''.join(linea)
        patrons.append(patron_de(lineas))
    return patrons


def patrones_fondo():
    """Los 256 patrones de cada una de las tres zonas.

    En la primera zona los diez primeros son los digitos del
    marcador, el 10 es el patron vacio y del 11 al 14 las cuatro
    estrellas.  En las otras dos zonas solo hay estrellas (el 0 es
    el vacio y del 1 al 4 las estrellas).
    """
    salida = bytearray(6144)
    estrellas_ = estrellas()
    vacio = bytes(8)

    for zona in range(3):
        base = zona * 2048
        for i in range(256):
            salida[base + i * 8:base + (i + 1) * 8] = vacio
        if zona == 0:
            salida[base:base + 80] = digitos()
        for i in range(4):
            salida[base + (10 + i) * 8:base + (11 + i) * 8] = estrellas_[i]
    return bytes(salida)


def tabla_nombres():
    """La tabla de nombres: 768 bytes, el indice del patron de cada
    celda.

    La primera fila es el marcador (los digitos) y el resto es el
    fondo, con las estrellas repartidas con un generador
    congruencial para que no salga un mosaico.
    """
    salida = bytearray(768)
    semilla = 20240101
    for fila in range(24):
        for col in range(32):
            if fila == 0:
                # el marcador en las cinco primeras celdas
                salida[col] = col if col < 5 else 10
            else:
                semilla = (semilla * 1103515245 + 12345) & 0x7FFFFFFF
                n = (semilla >> 16) % 5
                salida[fila * 32 + col] = 10 + n
    return bytes(salida)


def tabla_colores():
    """La tabla de colores: 8 bytes por patron, con el mismo reparto
    que la tabla de patrones.

    El vacio es negro, los digitos blancos y cada estrella con su
    color.
    """
    salida = bytearray(6144)
    colores_estrella = [14, 5, 15, 13]     # amarillo, cian, blanco, magenta
    for zona in range(3):
        base = zona * 2048
        for p in range(256):
            if zona == 0 and p < 10:
                color = (15 << 4) | 1        # los digitos, blancos
            elif 11 <= p < 15:
                color = (colores_estrella[p - 11] << 4) | 1
            else:
                color = (1 << 4) | 1        # negro sobre negro
            for y in range(8):
                salida[base + p * 8 + y] = color
    return bytes(salida)


def patrones_sprites():
    """Los patrones de los sprites: la nave (4 bloques), la bala, los
    enemigos y las explosiones."""
    salida = bytearray(2048)

    # la nave de 16x16, en cuatro bloques de 8x8
    for y in range(0, 16, 8):
        for x in range(0, 16, 8):
            lineas = [NAVE[y + dy][x:x + 8] for dy in range(8)]
            idx = (y // 8) * 2 + (x // 8)
            salida[idx * 8:idx * 8 + 8] = patron_de(lineas)

    salida[4 * 8:5 * 8] = patron_de(BALA)
    salida[5 * 8:6 * 8] = patron_de(ENEMIGO_DRON)
    salida[6 * 8:7 * 8] = patron_de(ENEMIGO_ALA)
    salida[7 * 8:8 * 8] = patron_de(ENEMIGO_BOMBA)
    for i, frame in enumerate(EXPLOSION):
        salida[(8 + i) * 8:(9 + i) * 8] = patron_de(frame)
    return bytes(salida)


def colores_sprites():
    """La tabla de colores de los sprites (32 bytes)."""
    colores = bytearray(32)
    for i in range(4):
        colores[i] = 15       # la nave
    for i in range(4, 12):
        colores[i] = 14       # las balas
    for i in range(12, 20):
        colores[i] = 13       # los enemigos
    for i in range(20, 24):
        colores[i] = 9        # las explosiones
    return bytes(colores)


def build_game_bank():
    """El banco 2: el fondo del juego, el marcador y los sprites."""
    nombres = tabla_nombres()
    patrones = patrones_fondo()
    colores = tabla_colores()
    sprites = patrones_sprites()
    attrs = colores_sprites()
    return bytes(nombres) + bytes(patrones) + bytes(colores) + bytes(attrs) + bytes(sprites)


if __name__ == '__main__':
    d = build_game_bank()
    print(f'banco del juego: {len(d)} bytes')

