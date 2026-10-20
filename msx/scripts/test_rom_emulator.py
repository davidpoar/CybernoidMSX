#!/usr/bin/env python3
"""Prueba la ROM en el emulador: arranca, carga la pantalla y comprueba
que la VRAM recibe los datos.
"""
import json
import os
import socket
import subprocess
import sys
import time

EMU = r'C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe'
ROOT = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms'
ROM_SRC = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom'
ROM_DST = os.path.join(ROOT, 'cybernoid', 'cybernoid.rom')
PORT = [5610]


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


def arrancar(rom, mapper='ascii16'):
    PORT[0] += 1
    path = rom if os.path.isabs(rom) else os.path.join(ROOT, rom)
    proc = subprocess.Popen(
        [EMU, '-r', path, '--mapper', mapper, '--agent-port', str(PORT[0])],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(60):
        time.sleep(0.5)
        try:
            socket.create_connection(('127.0.0.1', PORT[0]), timeout=1).close()
            return proc, Emu(PORT[0])
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError('el emulador murio: ' + proc.stdout.read()[-600:])
    raise RuntimeError('el emulador no abrio el puerto')


def hexb(s):
    return bytes.fromhex(s)


def main():
    os.makedirs(os.path.dirname(ROM_DST), exist_ok=True)
    with open(ROM_SRC, 'rb') as f:
        data = f.read()
    with open(ROM_DST, 'wb') as f:
        f.write(data)

    proc, emu = arrancar(ROM_DST)
    try:
        print('Arrancando la ROM en el emulador...')
        emu.call('msx.run_frames', {'frames': 900})

        slots = emu.call('msx.slots')
        print(f"  slot_register = {slots.get('slot_register')}")
        print(f"  page_map      = {slots.get('page_map')}")

        cpu = emu.call('cpu.read')
        pc = int(str(cpu.get('PC')), 16)
        print(f"  PC={cpu.get('PC')} SP={cpu.get('SP')} IFF1={cpu.get('IFF1')} "
              f"IM={cpu.get('IM')} Halted={cpu.get('Halted')} "
              f"Interrupts={cpu.get('InterruptsServiced')}")

        vdp = emu.call('msx.vdp.state')
        print(f"  VDP: mode={vdp.get('mode')} regs={vdp.get('registers')}")

        psg = emu.call('msx.psg.state')
        print(f"  PSG: {psg.get('registers')}")

        mem = emu.call('mem.read', {'addr': '0xC000', 'len': 32})['hex']
        b = hexb(mem)
        print(f"  RAM $C000: {mem}")
        print(f"     cur_bank=${b[0]:02X} our_slot=${b[1]:02X} slot_id=${b[2]:02X} "
              f"saved_reg=${b[3]:02X} bank_result=${b[4]:02X}")
        print(f"     job_phase=${b[0x10]:02X} job_dst=${b[0x11]:02X}${b[0x12]:02X} "
              f"job_src=${b[0x13]:02X}${b[0x14]:02X} job_pages=${b[0x15]:02X}${b[0x16]:02X}")

        print('\n  VRAM tras 900 frames:')
        for name, a, n in [('patrones $0000', 0, 32), ('patrones $0800', 0x800, 16),
                           ('nombres $1800', 0x1800, 32), ('nombres $1900', 0x1900, 16),
                           ('colores $2000', 0x2000, 32), ('colores $2800', 0x2800, 16),
                           ('sprites $3800', 0x3800, 16)]:
            h = emu.call('msx.vram.read', {'addr': a, 'len': n})['hex']
            print(f'    {name:16s}: {h}')

        # Comprobar que la tabla de nombres es la secuencia 0-255
        nt = emu.call('msx.vram.read', {'addr': 0x1800, 'len': 768})['hex'].lower()
        esperado = ''.join(f'{i & 0xFF:02x}' for i in range(768))
        print(f"\n  tabla de nombres correcta: {'SI' if nt == esperado else 'NO'}")

        # Comparar los patrones con los del fichero de la ROM
        rom = data
        # el banco 1 empieza en el offset $4000 del fichero; el byte 0 es
        # el ID y los datos empiezan en el byte 1
        def bank1(offset, length):
            return rom[0x4000 + 1 + offset: 0x4000 + 1 + offset + length].hex()

        vram_pat = emu.call('msx.vram.read', {'addr': 0, 'len': 6144})['hex'].lower()
        esperado_pat = bank1(768, 6144)
        print(f"  tabla de patrones correcta: "
              f"{'SI' if vram_pat == esperado_pat else 'NO'}")
        if vram_pat != esperado_pat:
            for i in range(0, 6144, 256):
                if vram_pat[i * 2:i * 2 + 32] != esperado_pat[i * 2:i * 2 + 32]:
                    print(f"     difiere en el offset ${i:04X} (zona {i // 2048})")
                    print(f"       vram    : {vram_pat[i * 2:i * 2 + 32]}")
                    print(f"       esperado: {esperado_pat[i * 2:i * 2 + 32]}")
                    break

        vram_col = emu.call('msx.vram.read', {'addr': 0x2000, 'len': 6144})['hex'].lower()
        esperado_col = bank1(768 + 6144, 6144)
        print(f"  tabla de colores correcta: "
              f"{'SI' if vram_col == esperado_col else 'NO'}")
        if vram_col != esperado_col:
            for i in range(0, 6144, 256):
                if vram_col[i * 2:i * 2 + 32] != esperado_col[i * 2:i * 2 + 32]:
                    print(f"     difiere en el offset ${i:04X} (zona {i // 2048})")
                    break

    finally:
        emu.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == '__main__':
    main()

