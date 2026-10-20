#!/usr/bin/env python3
"""Diagnostico de la ROM en el emulador: comprueba el hook de
interrupcion, el estado del trabajo de VRAM y traza la ISR."""
import json
import os
import socket
import subprocess
import sys
import time

EMU = r'C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe'
ROOT = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms'
ROM = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom'
PORT = 5620


class Emu:
    def __init__(self, port, timeout=180):
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


def arrancar():
    dst = os.path.join(ROOT, 'cybernoid', 'cybernoid.rom')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(ROM, 'rb') as f, open(dst, 'wb') as g:
        g.write(f.read())
    proc = subprocess.Popen(
        [EMU, '-r', dst, '--mapper', 'ascii16', '--agent-port', str(PORT)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(60):
        time.sleep(0.5)
        try:
            socket.create_connection(('127.0.0.1', PORT), timeout=1).close()
            return proc, Emu(PORT)
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError('murio: ' + proc.stdout.read()[-600:])
    raise RuntimeError('no abrio el puerto')


def main():
    proc, emu = arrancar()
    try:
        emu.call('msx.run_frames', {'frames': 900})

        print('1) El hook de interrupcion en $FD9F')
        h = emu.call('mem.read', {'addr': '0xFD9A', 'len': 8})['hex']
        print(f'   $FD9A: {h}')
        b = bytes.fromhex(h)
        if b[5] == 0xC3:
            addr = b[6] | (b[7] << 8)
            print(f'   -> JP ${addr:04X}')
        else:
            print('   -> NO hay un JP: el hook no se instalo')

        print('\n2) Estado del trabajo de VRAM')
        ram = bytes.fromhex(emu.call('mem.read', {'addr': '0xC000', 'len': 32})['hex'])
        print(f'   job_phase  = ${ram[0x10]:02X}')
        print(f'   job_dst    = ${ram[0x11] | (ram[0x12] << 8):04X}')
        print(f'   job_src    = ${ram[0x13] | (ram[0x14] << 8):04X}')
        print(f'   job_pages  = {ram[0x15] | (ram[0x16] << 8)}')

        print('\n3) Cuantas interrupciones se han servicingado')
        cpu = emu.call('cpu.read')
        print(f"   InterruptsServiced = {cpu.get('InterruptsServiced')}")

        print('\n4) La ISR se ejecuta? breakpoint en el gancho')
        emu.call('bp.set', {'addr': '0x407C'})
        r = emu.call('exec.run', {'max_instructions': 200000})
        print(f"   reason={r.get('reason')}")
        cpu = emu.call('cpu.read')
        print(f"   PC={cpu.get('PC')}")
        emu.call('bp.clear', {'addr': '0x407C'})

        print('\n5) Y JOB_NEXT?')
        emu.call('bp.set', {'addr': '0x40E1'})
        r = emu.call('exec.run', {'max_instructions': 200000})
        print(f"   reason={r.get('reason')}")
        cpu = emu.call('cpu.read')
        print(f"   PC={cpu.get('PC')}")
        emu.call('bp.clear', {'addr': '0x40E1'})

        print('\n6) La copia (job_copy)?')
        emu.call('bp.set', {'addr': '0x4100'})
        r = emu.call('exec.run', {'max_instructions': 200000})
        print(f"   reason={r.get('reason')}")
        cpu = emu.call('cpu.read')
        print(f"   PC={cpu.get('PC')}  HL={cpu.get('HL')}  BC={cpu.get('BC')}")
        emu.call('bp.clear', {'addr': '0x4100'})

        print('\n7) VRAM despues')
        for name, a in [('patrones', 0), ('nombres', 0x1800), ('colores', 0x2000)]:
            h = emu.call('msx.vram.read', {'addr': a, 'len': 16})['hex']
            print(f'   {name:9s}: {h}')

    finally:
        emu.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == '__main__':
    main()
