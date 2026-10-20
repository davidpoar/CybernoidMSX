#!/usr/bin/env python3
"""Prueba varias variantes de la ROM para aislar por que no arranca."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

EMU = r'C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe'
ROOT = Path(r'C:\Users\rubbe\AppData\Local\Temp\opencode\cybernoid-test')
BIOS = Path(r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\vg8020_basic-bios1.rom')
PORT = 5680


def probar(rom_bytes, etiqueta):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'cybernoid.rom').write_bytes(rom_bytes)
    (ROOT / 'msx.rom').write_bytes(BIOS.read_bytes())
    proc = subprocess.Popen(
        [EMU, '-r', str(ROOT / 'cybernoid.rom'), '--mapper', 'ascii16',
         '--agent-port', str(PORT)],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    s = None
    for _ in range(60):
        time.sleep(0.4)
        try:
            s = socket.create_connection(('127.0.0.1', PORT), timeout=30)
            break
        except OSError:
            if proc.poll() is not None:
                print(f'{etiqueta}: el emulador murio')
                return False
    if s is None:
        print(f'{etiqueta}: no se pudo conectar')
        proc.terminate()
        return False
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
        call('msx.run_frames', {'frames': 900})
        slots = call('msx.slots')
        pm = slots.get('page_map', {})
        pc = int(str(call('cpu.read').get('PC')), 16)
        ok = pm.get('page_1_0x1000') == 1
        print(f'{etiqueta:38s} pagina1->slot{pm.get("page_1_0x1000")} '
              f'PC=${pc:04X}  {"ARRANCA" if ok else "no"}')
        return ok
    finally:
        s.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    base = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom').read_bytes()

    probar(base, 'la ROM nueva tal cual')

    v = bytearray(base)
    for i in range(0x8000, 0xC000):
        v[i] = 0xFF
    probar(bytes(v), 'la nueva con el banco 2 vacio')

    v = bytearray(base)
    v[0x8000:0xC000] = base[0x4000:0x8000]
    probar(bytes(v), 'la nueva con el banco 2 = el banco 1')

    v = bytearray(base)
    v[0x0000:0x0203] = base[0x0000:0x0203]     # la cabecera igual
    v[0x0000:0x0203] = b'AB\x10\x40' + v[4:0x203]
    probar(bytes(v), 'la nueva con la cabecera puesta a mano')

    # el motor anterior (esta en git) con el banco 2 nuevo
    import subprocess
    out = subprocess.run(['git', 'show', 'HEAD:msx/build/cybernoid.rom'],
                         capture_output=True, cwd=r'C:\Dev\cybernoidMSX')
    if out.stdout:
        viejo = bytearray(out.stdout)
        viejo[0x8000:0xC000] = base[0x8000:0xC000]     # el banco 2 nuevo
        probar(bytes(viejo), 'el motor viejo con el banco 2 nuevo')

        # el motor nuevo con el banco 0 viejo
        v = bytearray(base)
        v[0:0x4000] = viejo[0:0x4000]
        probar(bytes(v), 'el motor nuevo con el banco 0 viejo')


if __name__ == '__main__':
    main()


