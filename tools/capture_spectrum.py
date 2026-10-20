#!/usr/bin/env python3
"""Ejecuta Cybernoid en el emulador de Spectrum inyectando la imagen
de memoria ya descifrada, y captura la pantalla del juego.

Solo se usa el emulador para ver los graficos originales: no se
modifica nada de z80emu.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

EMU = r'C:\Dev\z80emu\spectrum\bin\Debug\net10.0\spectrum.exe'
WORK = Path(r'C:\Users\rubbe\AppData\Local\Temp\opencode\spec-roms')
OUT = Path(r'C:\Dev\cybernoidMSX\spectrum\captures')
IMAGE = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin')
PORT = 5650

# La paleta del Spectrum
PALETA = [
    (0, 0, 0), (0, 0, 215), (215, 0, 0), (215, 0, 215),
    (0, 215, 0), (0, 215, 215), (215, 215, 0), (215, 215, 215),
]


class Emu:
    def __init__(self, port, timeout=300):
        self.sock = socket.create_connection(('127.0.0.1', port), timeout=timeout)
        self.buf = b''
        self.id = 0

    def call(self, cmd, args=None):
        self.id += 1
        msg = {'id': self.id, 'cmd': cmd}
        if args is not None:
            msg['args'] = args
        self.sock.sendall((json.dumps(msg) + '\n').encode('utf-8'))
        while b'\n' not in self.buf:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError('cerrado')
            self.buf += chunk
        line, _, self.buf = self.buf.partition(b'\n')
        r = json.loads(line.decode('utf-8'))
        if not r.get('ok'):
            raise RuntimeError(f'{cmd} -> {r.get("error")}')
        return r.get('data', {})

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


def arrancar():
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [EMU, '--agent-port', str(PORT)],
        cwd=str(WORK), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(60):
        time.sleep(0.5)
        try:
            socket.create_connection(('127.0.0.1', PORT), timeout=1).close()
            return proc, Emu(PORT)
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError('murio: ' + proc.stdout.read()[-800:])
    raise RuntimeError('no abrio el puerto')


def ppm(bitmap, attrs):
    """Convierte la pantalla del Spectrum en un PPM."""
    w, h = 256, 192
    pix = bytearray(w * h * 3)
    for row in range(24):
        for col in range(32):
            attr = attrs[row * 32 + col]
            ink = attr & 7
            paper = (attr >> 3) & 7
            for y in range(8):
                addr = (row // 8) * 0x100 + (row % 8) * 0x20 + col * 8
                b = bitmap[addr + y]
                for x in range(8):
                    on = (b >> (7 - x)) & 1
                    c = ink if on else paper
                    o = ((row * 8 + y) * w + col * 8 + x) * 3
                    pix[o] = PALETA[c][0]
                    pix[o + 1] = PALETA[c][1]
                    pix[o + 2] = PALETA[c][2]
    return b'P6\n256 192\n255\n' + bytes(pix)


def guardar(emu, nombre):
    d = emu.call('spec.screen.read')
    bitmap = bytes.fromhex(d['bitmap_hex'])
    attrs = bytes.fromhex(d['attributes_hex'])
    (OUT / f'{nombre}.bin').write_bytes(bitmap)
    (OUT / f'{nombre}.attrs').write_bytes(attrs)
    (OUT / f'{nombre}.ppm').write_bytes(ppm(bitmap, attrs))
    print(f'  guardada {nombre}')
    return bitmap, attrs


def main():
    img = IMAGE.read_bytes()
    assert len(img) == 49152, len(img)
    proc, emu = arrancar()
    try:
        print('Inyectando la imagen de memoria del juego...')
        # la imagen va de $4000 a $FFFF
        for i in range(0, len(img), 4096):
            trozo = img[i:i + 4096]
            emu.call('mem.write', {'addr': f'0x{0x4000 + i:04X}',
                                    'hex': trozo.hex()})
        print(f'  {len(img)} bytes escritos en $4000-$FFFF')

        # arrancar el juego en $6504
        emu.call('cpu.write', {'PC': '0x6504', 'SP': '0x0000', 'I': '0x00'})
        print('  PC = $6504')

        print('\nArrancando...')
        for i in range(20):
            emu.call('exec.run', {'max_cycles': 1_000_000})
            st = emu.call('cpu.read')
            pc = int(str(st.get('PC')), 16)
            cyc = st.get('Cycles')
            print(f'  paso {i}: PC=${pc:04X} ciclos={cyc} '
                  f'interr={st.get("InterruptsServiced")}')
            if pc == 0x0001 or pc == 0x0000:
                print('  la CPU se ha parado')
                break

        guardar(emu, '01_inicio')

        print('\nEsperando al juego...')
        for i in range(30):
            emu.call('exec.run', {'max_cycles': 1_000_000})
            st = emu.call('cpu.read')
            pc = int(str(st.get('PC')), 16)
            if i % 5 == 0:
                print(f'  paso {i}: PC=${pc:04X} '
                      f'interr={st.get("InterruptsServiced")}')

        guardar(emu, '02_juego')

        print('\nPulsando ESPACIO...')
        emu.call('spec.keyboard.row', {'row': 7, 'pressed': True})
        for i in range(10):
            emu.call('exec.run', {'max_cycles': 1_000_000})
        emu.call('spec.keyboard.row', {'row': 7, 'pressed': False})
        for i in range(20):
            emu.call('exec.run', {'max_cycles': 1_000_000})
        guardar(emu, '03_tras_espacio')
        st = emu.call('cpu.read')
        print('  PC =', st.get('PC'), 'interr =', st.get('InterruptsServiced'))
    finally:
        emu.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == '__main__':
    main()
