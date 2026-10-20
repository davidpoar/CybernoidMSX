#!/usr/bin/env python3
"""Debug the Cybernoid MSX ROM in the z80emu MSX emulator over the agent
protocol.  Read only: nothing in z80emu is modified.
"""
import json
import socket
import sys
from pathlib import Path

HOST = '127.0.0.1'
PORT = 5555
ROM = Path(__file__).parent.parent / 'build' / 'cybernoid.rom'
SYM = Path(__file__).parent.parent / 'build' / 'rom_engine.sym'


class Agent:
    def __init__(self, host=HOST, port=PORT, timeout=180):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.rfile = self.sock.makefile('r', encoding='utf-8', newline='\n')
        self.next_id = 1

    def call(self, cmd, **args):
        req = {'id': self.next_id, 'cmd': cmd}
        if args:
            req['args'] = args
        self.next_id += 1
        self.sock.sendall((json.dumps(req) + '\n').encode('utf-8'))
        line = self.rfile.readline()
        if not line:
            raise RuntimeError('agent closed the connection')
        resp = json.loads(line)
        if not resp.get('ok'):
            raise RuntimeError(f'{cmd} failed: {resp.get("error")}')
        return resp.get('data')

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def h(value, default=0):
    """El emulador devuelve los numeros como cadenas hexadecimales."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    return int(str(value), 16)


def symbols():
    out = {}
    if SYM.exists():
        for line in SYM.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 3 and not parts[0].startswith('.'):
                try:
                    out[parts[0]] = int(parts[2].rstrip('H'), 16)
                except ValueError:
                    pass
    return out


def show(agent, title):
    print(f'\n--- {title} ---')
    cpu = agent.call('cpu.read')
    print('  PC=${:04X} SP=${:04X} IX=${:04X} IY=${:04X} AF=${:04X} '
          'HL=${:04X} BC=${:04X} IM={} IFF1={} Halted={} Cycles={}'.format(
              h(cpu.get('PC')), h(cpu.get('SP')), h(cpu.get('IX')),
              h(cpu.get('IY')), h(cpu.get('AF')), h(cpu.get('HL')),
              h(cpu.get('BC')), cpu.get('IM'), cpu.get('IFF1'),
              cpu.get('Halted'), cpu.get('Cycles')))
    slots = agent.call('msx.slots')
    print(f"  slot_register={slots.get('slot_register')} "
          f"page_map={slots.get('page_map')}")
    vdp = agent.call('msx.vdp.state')
    regs = vdp.get('registers', [])
    print(f"  vdp: mode={vdp.get('mode')} frame={vdp.get('frame')} "
          f"regs={regs} irq={vdp.get('interrupts_enabled')}")


def main():
    agent = Agent()
    syms = symbols()
    try:
        print('=' * 70)
        print('CYBERNOID ROM - DEPURACION EN EL EMULADOR z80emu')
        print('=' * 70)
        print(f'ROM: {ROM} ({ROM.stat().st_size} bytes)')
        print(f'Simbolos: {len(syms)}')
        for name in ('INIT', 'MAINLOOP', 'SETBANK_B', 'BANK_SELFTEST'):
            if name in syms:
                print(f'  {name:14s} = ${syms[name]:04X}')

        show(agent, '1. Estado inicial (emulador pausado)')

        # ---------------------------------------------------------------
        print('\n[2] Arrancando la CPU (20 M ciclos)...')
        r = agent.call('exec.run', max_cycles=20_000_000)
        print(f"    reason={r.get('reason')} cycles={r.get('cycles')} "
              f"instructions={r.get('instructions')}")
        show(agent, '3. Tras arrancar')

        # ---------------------------------------------------------------
        print('\n[4] ¿Donde quedo el PC?')
        cpu = agent.call('cpu.read')
        pc = h(cpu.get('PC'))
        print(f'    PC = ${pc:04X}')
        if 0x4000 <= pc <= 0x7FFF:
            print('    -> DENTRO DEL CARTUCHO (banco A, pagina 1)')
        elif 0xC000 <= pc <= 0xFFFF:
            print('    -> En RAM (el codigo del cartucho NO esta corriendo)')
        else:
            print(f'    -> En la BIOS')

        # ---------------------------------------------------------------
        print('\n[5] Memoria visible')
        for name, addr in [('cabecera $4000', 0x4000), ('banco B $8000', 0x8000),
                           ('registro banco B $7000', 0x7000),
                           ('registro banco A $6000', 0x6000),
                           ('RAM $C000', 0xC000)]:
            try:
                mem = agent.call('mem.read', addr=f'0x{addr:04X}', len=16)
                print(f'    {name:22s}: {mem.get("hex")}')
            except Exception as e:
                print(f'    {name:22s}: error {e}')

        # ---------------------------------------------------------------
        print('\n[6] ¿Llego a MAINLOOP?')
        if 'MAINLOOP' in syms:
            ml = syms['MAINLOOP']
            agent.call('bp.set', addr=f'0x{ml:04X}')
            r = agent.call('exec.run', max_instructions=50_000_000)
            pc2 = h(r.get('pc', 0))
            print(f"    reason={r.get('reason')} pc=${pc2:04X}")
            if r.get('reason') == 'breakpoint':
                print('    -> LLEGO: el arranque del cartucho funciona')
            else:
                print(f'    -> NO llego. PC actual = ${pc2:04X}')
                show(agent, '       Estado en el momento de parar')
            agent.call('bp.clear', addr=f'0x{ml:04X}')

        # ---------------------------------------------------------------
        print('\n[7] VRAM (¿se escribio algo?)')
        for name, addr in [('patrones $0000', 0x0000), ('nombres $1800', 0x1800),
                           ('colores $2000', 0x2000), ('sprites $3800', 0x3800)]:
            mem = agent.call('msx.vram.read', addr=f'0x{addr:04X}', len=32)
            print(f'    {name:16s}: {mem.get("hex")}')

        # ---------------------------------------------------------------
        print('\n[8] Pantalla')
        scr = agent.call('msx.screen.text')
        lines = scr.get('lines', [])
        nonempty = [(i, l) for i, l in enumerate(lines) if l.strip('. ')]
        print(f'    {len(lines)} lineas, {len(nonempty)} con contenido')
        for i, l in nonempty[:10]:
            print(f'    {i:2}| {l}')

        # ---------------------------------------------------------------
        print('\n[9] Slots (¿el BIOS mapeo las paginas 1 y 2?)')
        slots = agent.call('msx.slots')
        print(f"    slot_register={slots.get('slot_register')}")
        for k, v in slots.get('page_map', {}).items():
            print(f'    {k} -> slot {v}')

    finally:
        agent.close()


if __name__ == '__main__':
    main()
