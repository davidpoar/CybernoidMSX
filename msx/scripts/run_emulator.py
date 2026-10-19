#!/usr/bin/env python3
"""Drive the z80emu MSX emulator through its agent protocol to run the
Cybernoid MSX port and capture the screen.

Usage:
  py msx/scripts/run_emulator.py [--rom PATH] [--com PATH] [--frames N]

The emulator must be started separately with --agent-port.
"""
import argparse
import json
import socket
import sys
import time
from pathlib import Path

MSX_DIR = Path(__file__).parent.parent
BUILD_DIR = MSX_DIR / 'build'


class Agent:
    def __init__(self, host='127.0.0.1', port=8111, timeout=60):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.rfile = self.sock.makefile('r', encoding='utf-8', newline='\n')
        self.next_id = 1

    def cmd(self, name, **args):
        req = {'id': self.next_id, 'cmd': name, 'args': args}
        self.next_id += 1
        self.sock.sendall((json.dumps(req) + '\n').encode('utf-8'))
        line = self.rfile.readline()
        if not line:
            raise RuntimeError('agent closed the connection')
        resp = json.loads(line)
        if not resp.get('ok'):
            raise RuntimeError(f'{name} failed: {resp.get("error")}')
        return resp.get('data')

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def wait_for_agent(port, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection(('127.0.0.1', port), timeout=2)
            s.close()
            return True
        except OSError:
            time.sleep(0.5)
    return False


def render_text(screen_text):
    """Print the emulator's textual screen dump."""
    if not screen_text:
        print('  (no screen text)')
        return
    for line in screen_text.split('\n'):
        print('  |' + line.replace(' ', '.'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8111)
    ap.add_argument('--com', default=str(BUILD_DIR / 'cybernoid.com'))
    ap.add_argument('--frames', type=int, default=10)
    ap.add_argument('--hold', type=int, default=0,
                    help='extra frames to run after the first capture')
    args = ap.parse_args()

    if not wait_for_agent(args.port):
        print(f'ERROR: no agent listening on port {args.port}')
        print('Start the emulator with:')
        print(f'  msx.exe --agent-port {args.port}')
        return 1

    agent = Agent(port=args.port)
    try:
        print('== CPU state before ==')
        print(' ', agent.cmd('cpu.read'))

        # --- load the .COM into MSX RAM at $0100 ---
        com = Path(args.com).read_bytes()
        payload = com[256:]            # skip the CP/MS header
        print(f'\n== Loading {args.com} ({len(payload)} bytes) at $0100 ==')
        # mem.write has a message size limit, so write in chunks
        CHUNK = 0x8000
        addr = 0x0100
        for off in range(0, len(payload), CHUNK):
            part = payload[off:off + CHUNK]
            agent.cmd('mem.write', addr=addr, hex=part.hex())
            addr += len(part)
        print(f'   loaded up to ${addr - 1:04X}')

        # --- switch every page to the RAM slot (all-RAM mode) ---
        agent.cmd('cpu.write', slotregister=0xFF, slotmapping=1)
        print('\n== Switched to all-RAM mode (slot register = $FF) ==')

        # --- start the game ---
        agent.cmd('cpu.write', pc=0x0100, sp=0xF380, i=0xF0)
        print('== Starting the game at $0100 ==')

        for n in (1, 2, 5, 10, 30, 60):
            if n > args.frames:
                break
            r = agent.cmd('msx.run_frames', frames=n)
            print(f'  ran to frame {n}: {r}')

        print('\n== CPU state ==')
        print(' ', agent.cmd('cpu.read'))

        print('\n== Screen ==')
        try:
            render_text(agent.cmd('msx.screen.text'))
        except Exception as e:
            print(f'  (screen text failed: {e})')

        print('\n== VRAM: pattern table (first 64 bytes) ==')
        v = agent.cmd('msx.vram.read', addr=0x0000, len=64)
        print('  ', v['hex'])

        print('\n== VRAM: colour table (first 32 bytes) ==')
        v = agent.cmd('msx.vram.read', addr=0x2000, len=32)
        print('  ', v['hex'])

        print('\n== VRAM: name table (first 64 bytes) ==')
        v = agent.cmd('msx.vram.read', addr=0x3800, len=64)
        print('  ', v['hex'])

        print('\n== VDP state ==')
        print(' ', agent.cmd('msx.vdp.state'))

        print('\n== PSG state ==')
        print(' ', agent.cmd('msx.psg.state'))

        if args.hold:
            print(f'\n== Running {args.hold} more frames ==')
            agent.cmd('msx.run_frames', frames=args.hold)
            render_text(agent.cmd('msx.screen.text'))
    finally:
        agent.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())