#!/usr/bin/env python3
"""Prueba basica del emulador de Spectrum: arranca la CPU y la cinta."""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

EMU = r'C:\Dev\z80emu\spectrum\bin\Debug\net10.0\spectrum.exe'
WORK = Path(r'C:\Users\rubbe\AppData\Local\Temp\opencode\spec-roms')
PORT = 5642


def main():
    proc = subprocess.Popen(
        [EMU, '-t', str(WORK / 'Cybernoid.tzx'), '--agent-port', str(PORT)],
        cwd=str(WORK), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    s = None
    for _ in range(60):
        time.sleep(0.5)
        try:
            s = socket.create_connection(('127.0.0.1', PORT), timeout=60)
            break
        except OSError:
            if proc.poll() is not None:
                print(proc.stdout.read()[-800:])
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
        if not line:
            raise RuntimeError('cerrado')
        r = json.loads(line)
        if not r.get('ok'):
            raise RuntimeError(f'{cmd} -> {r.get("error")}')
        return r.get('data', {})

    try:
        print('cpu:', json.dumps(call('cpu.read')))
        print('tape:', json.dumps(call('spec.tape.state')))
        print('ula:', json.dumps(call('spec.ula.state')))

        print('\n1) probar exec.step')
        r = call('exec.step', {'count': 100})
        print('  ', json.dumps(r))
        print('  cpu:', json.dumps(call('cpu.read')))

        print('\n2) arrancar la cinta y ejecutar')
        print('  ', json.dumps(call('spec.tape.set_playing', {'playing': True})))
        r = call('exec.run', {'max_cycles': 500000})
        print('  ', json.dumps(r))
        print('  cpu:', json.dumps(call('cpu.read')))
        print('  tape:', json.dumps(call('spec.tape.state')))

        print('\n3) reset + run')
        call('reset')
        r = call('exec.run', {'max_cycles': 2000000})
        print('  ', json.dumps(r))
        print('  cpu:', json.dumps(call('cpu.read')))
    finally:
        s.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == '__main__':
    main()
