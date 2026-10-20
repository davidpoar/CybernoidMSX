#!/usr/bin/env python3
"""Pruebas de bajo nivel contra el emulador: hooks de interrupcion, estado
del VDP y tiempos de acceso a VRAM."""
import json
import os
import socket
import subprocess
import sys
import time

EMU = r'C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe'
ROOT = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms'
PORT = 5590


class Emu:
    def __init__(self, port, timeout=120):
        self.sock = socket.create_connection(('127.0.0.1', port), timeout=timeout)
        self.buf = b''
        self.id = 0

    def call(self, cmd, args=None):
        self.id += 1
        msg = {'id': 1, 'cmd': cmd} if False else {'id': self.id, 'cmd': cmd}
        if args is not None:
            msg['args'] = args
        self.sock.sendall((json.dumps(msg) + '\n').encode('utf-8'))
        while b'\n' not in self.buf:
            chunk = self.sock.recv(65536)
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


def arrancar(rom, mapper='ascii16'):
    global PORT
    PORT += 1
    path = rom if os.path.isabs(rom) else os.path.join(ROOT, rom)
    proc = subprocess.Popen(
        [EMU, '-r', path, '--mapper', mapper, '--agent-port', str(PORT)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(60):
        time.sleep(0.5)
        try:
            socket.create_connection(('127.0.0.1', PORT), timeout=1).close()
            return proc, Emu(PORT)
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError('murio: ' + proc.stdout.read()[-500:])
    raise RuntimeError('no abrio el puerto')


def main():
    proc, emu = arrancar(r'cybernoid\cybernoid.rom')
    try:
        emu.call('msx.run_frames', {'frames': 200})

        print('1) Los hooks $FD9A / $FD9F son RAM escribible?')
        for addr in (0xFD9A, 0xFD9F, 0xFCC1):
            antes = emu.call('mem.read', {'addr': f'0x{addr:04X}', 'len': 4})['hex']
            emu.call('mem.write', {'addr': f'0x{addr:04X}', 'hex': 'AABBCCDD'})
            despues = emu.call('mem.read', {'addr': f'0x{addr:04X}', 'len': 4})['hex']
            print(f'   ${addr:04X}: antes={antes}  escrito=AABBCCDD  leido={despues}'
                  f'   -> {"RAM" if despues == "aabbccdd" else "ROM (no escribible)"}')

        print('\n2) Estado del VDP: bits del registro de estado')
        vdp = emu.call('msx.vdp.state')
        print('   ', json.dumps(vdp))

        print('\n3) El registro de estado cambia con el vblank?')
        for i in range(8):
            st = emu.call('msx.vdp.state')
            print(f"   frame={st.get('frame')} is_vblank={st.get('is_vblank')} "
                  f"status={st.get('status')}")
            emu.call('msx.run_frames', {'frames': 5})

        print('\n4) La pantalla se dibuja? (name table y patrones)')
        for name, a in [('patrones', 0), ('nombres', 0x1800), ('colores', 0x2000)]:
            h = emu.call('msx.vram.read', {'addr': a, 'len': 32})['hex']
            print(f'   {name:9s} ${a:04X}: {h}')

        print('\n5) La pagina 2 ($8000) es la del cartucho? (banco B visible)')
        print('   $8000 =', emu.call('mem.read', {'addr': '0x8000', 'len': 8})['hex'])
        print('   $6000 =', emu.call('mem.read', {'addr': '0x6000', 'len': 8})['hex'])
        print('   $6800 =', emu.call('mem.read', {'addr': '0x6800', 'len': 8})['hex'])
        print('   $7000 =', emu.call('mem.read', {'addr': '0x7000', 'len': 8})['hex'])
        print('   $7800 =', emu.call('mem.read', {'addr': '0x7800', 'len': 8})['hex'])
    finally:
        emu.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == '__main__':
    main()
