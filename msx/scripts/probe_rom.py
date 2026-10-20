#!/usr/bin/env python3
"""Lee el estado interno de la ROM en el emulador."""
import json
import socket
import sys

s = socket.create_connection(('127.0.0.1', 5555), timeout=60)
f = s.makefile('r', encoding='utf-8', newline='\n')


def call(cmd, **args):
    req = {'id': 1, 'cmd': cmd}
    if args:
        req['args'] = args
    s.sendall((json.dumps(req) + '\n').encode())
    return json.loads(f.readline())


m = call('mem.read', addr='0xC000', len=16)['data']
b = bytes.fromhex(m['hex'])
print('RAM $C000:', m['hex'])
names = ['cur_bank', 'our_slot', 'slot_id', 'saved_reg', 'bank_result']
for i, n in enumerate(names):
    print('   %-12s = $%02X' % (n, b[i]))

print()
slots = call('msx.slots')['data']
print('slot_register =', slots['slot_register'])
print('page_map      =', slots['page_map'])

regs = call('msx.psg.state')['data']['registers']
print()
print('PSG (%d registros):' % len(regs))
for i, v in enumerate(regs):
    print('   R%-2d = %s' % (i, v))

print()
vdp = call('msx.vdp.state')['data']
print('VDP:', json.dumps(vdp))

print()
scr = call('msx.screen.text')['data']['lines']
print('pantalla (%d lineas):' % len(scr))
for i, l in enumerate(scr):
    if l.strip('. '):
        print('   %2d| %s' % (i, l))

s.close()
