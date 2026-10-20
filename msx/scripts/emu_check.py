#!/usr/bin/env python3
"""Arranca una ROM en el emulador MSX de z80emu y comprueba que funciona.

No modifica nada de z80emu: solo lanza el ejecutable y habla con el
servidor de control por TCP.

Uso:
    py emu_check.py <rom> [mapper] [frames]
    py emu_check.py --compare
"""
import json
import os
import socket
import subprocess
import sys
import time

EMU = r'C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe'
ROOT = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms'
PORT = [5570]


class Emu:
    def __init__(self, port, timeout=120):
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
                raise ConnectionError('el emulador cerro la conexion')
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


def arrancar(rom, mapper='ascii16', port=None):
    port = port or PORT[0]
    PORT[0] += 1
    path = rom if os.path.isabs(rom) else os.path.join(ROOT, rom)
    proc = subprocess.Popen(
        [EMU, '-r', path, '--mapper', mapper, '--agent-port', str(port)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(60):
        time.sleep(0.5)
        try:
            socket.create_connection(('127.0.0.1', port), timeout=1).close()
            return proc, Emu(port)
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError('el emulador murio: ' + proc.stdout.read()[-600:])
    raise RuntimeError('el emulador no abrio el puerto')


def comprobar(rom, mapper='ascii16', frames=900, port=None):
    print('=' * 72)
    print(f'ROM    : {rom}')
    print(f'mapper : {mapper}   frames: {frames}')
    print('=' * 72)
    proc = None
    try:
        proc, emu = arrancar(rom, mapper, port)
        emu.call('msx.run_frames', {'frames': frames})

        slots = emu.call('msx.slots')
        print(f"  slot_register = {slots.get('slot_register')}")
        print(f"  page_map      = {slots.get('page_map')}")
        pm = slots.get('page_map', {})
        mapeado = (pm.get('page_1_0x1000') == 1 and pm.get('page_2_0x2000') == 1)
        print(f"  -> cartucho mapeado en paginas 1 y 2: {'SI' if mapeado else 'NO'}")

        cpu = emu.call('cpu.read')
        pc = int(str(cpu.get('PC')), 16)
        print(f"  PC = {cpu.get('PC')}  SP={cpu.get('SP')}  IM={cpu.get('IM')}  "
              f"IFF1={cpu.get('IFF1')}  Halted={cpu.get('Halted')}")
        print(f"  -> PC en el cartucho: "
              f"{'SI' if 0x4000 <= pc <= 0xBFFF else 'NO'}")

        vdp = emu.call('msx.vdp.state')
        print(f"  VDP: mode={vdp.get('mode')} regs={vdp.get('registers')} "
              f"irq={vdp.get('interrupts_enabled')}")

        psg = emu.call('msx.psg.state')
        print(f"  PSG: {psg.get('registers')}")

        # La pantalla debe cambiar entre dos muestras si el juego esta vivo
        s1 = emu.call('msx.screen.text')['lines']
        emu.call('msx.run_frames', {'frames': 30})
        s2 = emu.call('msx.screen.text')['lines']
        cambia = s1 != s2
        print(f"  pantalla cambia entre muestras: {'SI' if cambia else 'NO'}")
        no_vacias = [(i, l) for i, l in enumerate(s2) if l.strip('. ')]
        print(f'  lineas con contenido: {len(no_vacias)}')
        for i, l in no_vacias[:6]:
            print(f'     {i:2}| {l}')

        # VRAM con contenido?
        vram = emu.call('msx.vram.read', {'addr': 0, 'len': 64})['hex']
        print(f'  VRAM[0..63] = {vram}')
        return mapeado and 0x4000 <= pc <= 0xBFFF
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    if sys.argv[1] == '--compare':
        casos = [
            (r'ascii16\cross_blaim_dbsoft_1985_64k.rom', 'ascii16', 900),
            (r'ascii16\gallforce_sony_1986_128k.rom', 'ascii16', 900),
            (r'cybernoid\cybernoid.rom', 'ascii16', 900),
        ]
        for rom, mp, fr in casos:
            try:
                comprobar(rom, mp, fr)
            except Exception as e:
                print(f'  ERROR: {e}')
            print()
    else:
        rom = sys.argv[1]
        mp = sys.argv[2] if len(sys.argv) > 2 else 'ascii16'
        fr = int(sys.argv[3]) if len(sys.argv) > 3 else 900
        comprobar(rom, mp, fr)


if __name__ == '__main__':
    main()
