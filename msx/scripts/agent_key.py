#!/usr/bin/env python3
"""Manda una tecla al emulador MSX de z80emu y ejecuta unos frames.

Uso: py agent_key.py <fila> <bit> [frames] [puerto]
"""
import json
import socket
import sys
import time


def main():
    fila = int(sys.argv[1])
    bit = int(sys.argv[2])
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    puerto = int(sys.argv[4]) if len(sys.argv) > 4 else 5575

    for _ in range(40):
        try:
            s = socket.create_connection(('127.0.0.1', puerto), timeout=60)
            break
        except OSError:
            time.sleep(0.5)
    else:
        print('no se pudo conectar con el emulador')
        return 1

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
        call('msx.keyboard.press', {'row': fila, 'bit': bit})
        call('msx.run_frames', {'frames': frames})
        call('msx.keyboard.release', {'row': fila, 'bit': bit})
        call('msx.run_frames', {'frames': frames})
        print(f'  tecla ({fila},{bit}) pulsada y {frames * 2} frames')
    finally:
        s.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
