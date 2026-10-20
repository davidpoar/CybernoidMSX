#!/usr/bin/env python3
"""Diagnostico: lee la cabecera de la ROM en el emulador y compara."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

EMU = r'C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe'
ROOT = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\cybernoid-test'
BIOS = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\vg8020_basic-bios1.rom'
ROM = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom'
PORT = 5670


def main():
    os.makedirs(ROOT, exist_ok=True)
    with open(ROM, 'rb') as f, open(os.path.join(ROOT, 'cybernoid.rom'), 'wb') as g:
        g.write(f.read())
    with open(BIOS, 'rb') as f, open(os.path.join(ROOT, 'msx.rom'), 'wb') as g:
        g.write(f.read())

    proc = subprocess.Popen(
        [EMU, '-r', os.path.join(ROOT, 'cybernoid.rom'), '--mapper', 'ascii16',
         '--agent-port', str(PORT)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    s = None
    for _ in range(60):
        time.sleep(0.5)
        try:
            s = socket.create_connection(('127.0.0.1', PORT), timeout=60)
            break
        except OSError:
            if proc.poll() is not None:
                print(proc.stdout.read()[-1500:])
                return
    f = s.makefile('r', encoding='utf-8', newline='\n')
    idc = [0]

    def call(cmd, args=None):
        idc[0] += 1
        msg = {'id': idc[0], 'cmd': cmd}
        if args is not None:
            msg['args'] = args
        s.sendall((json.dumps(msg) + '\n').encode())
        line = f.readline()
        r = json.loads(line)
        if not r.get('ok'):
            raise RuntimeError(f'{cmd} -> {r.get("error")}')
        return r.get('data', {})

    try:
        call('msx.run_frames', {'frames': 300})
        print('slots:', json.dumps(call('msx.slots')))
        print('cpu  :', json.dumps({k: v for k, v in call('cpu.read').items()
                                   if k in ('PC', 'SP', 'IM', 'IFF1', 'Halted',
                                            'InterruptsServiced')}))
        for addr in (0x4000, 0x4002, 0x4010, 0xC000, 0xC006):
            h = call('mem.read', {'addr': f'0x{addr:04X}', 'len': 16})['hex']
            print(f'  ${addr:04X}: {h}')

        # la ROM en el fichero
        with open(ROM, 'rb') as g:
            rom = g.read()
        print(f'\nla ROM en el fichero:')
        for off in (0x0000, 0x0010, 0xC000):
            print(f'  ${0x4000 + off:04X}: {rom[off:off + 16].hex(" ")}')
    finally:
        s.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == '__main__':
    main()
