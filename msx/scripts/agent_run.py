#!/usr/bin/env python3
"""Manda al emulador MSX de z80emu que ejecute unos cuantos frames.

El emulador arranca en pausa cuando se le pasa --agent-port, asi que
sin esto la pantalla no se dibuja.

Uso: py agent_run.py [frames] [puerto]
"""
import json
import socket
import sys
import time


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    puerto = int(sys.argv[2]) if len(sys.argv) > 2 else 5575

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
        call('msx.run_frames', {'frames': frames})
        print(f'  {frames} frames ejecutados')
    finally:
        s.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
