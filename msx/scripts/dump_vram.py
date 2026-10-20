#!/usr/bin/env python3
"""Lee la VRAM del emulador MSX y la dibuja como el VDP, para ver si lo
que se ve en la ventana es lo que hay en la memoria.

Uso: py dump_vram.py [puerto] [salida.png]
"""
import json
import socket
import struct
import sys
import time
import zlib
from pathlib import Path

PALETA = [
    (0, 0, 0), (0, 0, 0), (0, 215, 0), (127, 255, 127),
    (0, 0, 215), (0, 255, 255), (215, 0, 0), (255, 127, 127),
    (0, 0, 127), (0, 127, 255), (127, 127, 127), (191, 191, 191),
    (0, 127, 0), (255, 0, 255), (215, 215, 0), (255, 255, 255),
]


def conectar(puerto):
    for _ in range(40):
        try:
            return socket.create_connection(('127.0.0.1', puerto), timeout=60)
        except OSError:
            time.sleep(0.5)
    raise RuntimeError('no se pudo conectar')


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 5575
    salida = sys.argv[2] if len(sys.argv) > 2 else 'vram.png'
    s = conectar(puerto)
    f = s.makefile('r', encoding='utf-8', newline='\n')
    idc = [0]

    def call(cmd, args=None):
        idc[0] += 1
        msg = {'id': idc[0], 'cmd': cmd}
        if args is not None:
            msg['args'] = args
        s.sendall((json.dumps(msg) + '\n').encode())
        r = json.loads(f.readline())
        if not r.get('ok'):
            raise RuntimeError(f'{cmd} -> {r.get("error")}')
        return r.get('data', {})

    try:
        call('msx.run_frames', {'frames': 300})
        vdp = call('msx.vdp.state')
        print('VDP:', json.dumps(vdp))
        vram = bytes.fromhex(call('msx.vram.read', {'addr': 0, 'len': 16384})['hex'])
    finally:
        s.close()

    # el dibujado del emulador (RenderGraphic2)
    nombre = 0x1800
    patron = 0x0000
    color = 0x2000
    rgb = bytearray(256 * 192 * 3)
    for row in range(24):
        zona = row // 8
        for col in range(32):
            num = vram[nombre + row * 32 + col]
            indice = zona * 256 + num
            for y in range(8):
                pb = vram[patron + (indice * 8 + y) & 0x1FFF]
                cb = vram[color + (indice * 8 + y) & 0x1FFF]
                fg = PALETA[cb >> 4]
                bg = PALETA[cb & 0x0F]
                for x in range(8):
                    on = (pb & (0x80 >> x)) != 0
                    c = fg if on else bg
                    o = ((row * 8 + y) * 256 + col * 8 + x) * 3
                    rgb[o], rgb[o + 1], rgb[o + 2] = c

    # PNG minimo
    raw = bytearray()
    for y in range(192):
        raw.append(0)
        raw += rgb[y * 256 * 3:(y + 1) * 256 * 3]

    def chunk(tipo, datos):
        return (struct.pack('>I', len(datos)) + tipo + datos +
                struct.pack('>I', zlib.crc32(tipo + datos) & 0xFFFFFFFF))

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 192, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += chunk(b'IEND', b'')
    Path(salida).write_bytes(png)
    print(f'  {salida} escrito')

    # un resumen
    distintos = len(set(rgb[0::3]))
    print(f'  {distintos} colores distintos en la imagen')


if __name__ == '__main__':
    main()
