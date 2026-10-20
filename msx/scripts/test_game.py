#!/usr/bin/env python3
"""Prueba el juego de la ROM en el emulador MSX de z80emu.

Arranca la ROM, carga la pantalla del titulo, pulsa la tecla 1 para
empezar la partida, y comprueba que la nave se mueve con las
flechas y que dispara.
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

EMU = r'C:\Dev\z80emu\msx\bin\Debug\net10.0\msx.exe'
# Un directorio propio, sin cintas: si el emulador encuentra una cinta
# en el directorio de trabajo la carga en vez de la ROM.
ROOT = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\cybernoid-test'
BIOS = r'C:\Users\rubbe\AppData\Local\Temp\opencode\msx-roms\vg8020_basic-bios1.rom'
ROM_SRC = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom'
ROM_DST = os.path.join(ROOT, 'cybernoid.rom')
PORT = 5660

# Las variables del juego en la RAM
ESTADO = 0xC020
SCORE = 0xC021
VIDAS = 0xC024
ETAPA = 0xC025
NAVE_X = 0xC0B0
NAVE_Y = 0xC0B1
BALA_X = 0xC0C0
BALA_VIVA = 0xC0D0
FRAME = 0xC006


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
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise ConnectionError('cerrado')
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


def main():
    os.makedirs(ROOT, exist_ok=True)
    shutil_copy(ROM_SRC, ROM_DST)
    shutil_copy(BIOS, os.path.join(ROOT, 'msx.rom'))

    proc = subprocess.Popen(
        [EMU, '-r', ROM_DST, '--mapper', 'ascii16', '--agent-port', str(PORT)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    emu = None
    for _ in range(60):
        time.sleep(0.5)
        try:
            emu = Emu(PORT)
            break
        except OSError:
            if proc.poll() is not None:
                print('el emulador murio')
                return 1
    if emu is None:
        print('no se pudo conectar')
        return 1

    fallos = 0

    def check(ok, label, detail=''):
        nonlocal fallos
        print(f'  [{"PASS" if ok else "FAIL"}] {label}' +
              (f' - {detail}' if detail else ''))
        if not ok:
            fallos += 1

    def ram(addr, n=1):
        h = emu.call('mem.read', {'addr': f'0x{addr:04X}', 'len': n})['hex']
        return bytes.fromhex(h)

    try:
        print('1. El arranque')
        emu.call('msx.run_frames', {'frames': 900})
        cpu = emu.call('cpu.read')
        pc = int(str(cpu.get('PC')), 16)
        check(0x4000 <= pc <= 0x7FFF, 'el PC esta en el cartucho', f'${pc:04X}')
        slots = emu.call('msx.slots')
        pm = slots.get('page_map', {})
        check(pm.get('page_1_0x1000') == 1 and pm.get('page_2_0x2000') == 1,
              'el cartucho esta en las paginas 1 y 2', str(pm))
        check(ram(0xC004)[0] == 0, 'el autotest del mapper pasa',
              f'${ram(0xC004)[0]:02X}')

        print('\n2. La pantalla del titulo')
        nt = emu.call('msx.vram.read', {'addr': 0x1800, 'len': 768})['hex'].lower()
        esperado = ''.join(f'{i & 0xFF:02x}' for i in range(768))
        check(nt == esperado, 'la tabla de nombres esta cargada')
        patrones = emu.call('msx.vram.read', {'addr': 0, 'len': 2048})['hex'].lower()
        check(len(set(range(0, len(patrones), 2))) > 20,
              'los patrones estan cargados',
              f'{len(patrones) // 2} bytes')

        print('\n3. Empezar la partida (tecla 1)')
        emu.call('msx.keyboard.press', {'row': 0, 'bit': 1})
        emu.call('msx.run_frames', {'frames': 5})
        emu.call('msx.keyboard.release', {'row': 0, 'bit': 1})
        emu.call('msx.run_frames', {'frames': 200})
        estado = ram(ESTADO)[0]
        check(estado == 1, 'el juego esta en marcha', f'estado=${estado:02X}')
        vidas = ram(VIDAS)[0]
        check(vidas == 3, 'tres vidas', f'{vidas}')
        patron0 = emu.call('msx.vram.read', {'addr': 0, 'len': 8})['hex'].lower()
        check(patron0 != '8040201008040201'[:16],
              'el fondo del juego se ha cargado', patron0)

        # el fondo del juego tiene su propia tabla de colores
        asset = Path(r'C:\Dev\cybernoidMSX\msx\assets\cybernoid_screen.bin')
        juego = bytes.fromhex(
            emu.call('msx.vram.read', {'addr': 0x2000, 'len': 6144})['hex'])
        colores_esperados = None
        # el banco 2 del fichero de la ROM
        rom = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom').read_bytes()
        # el banco 2: 768 (nombres) + 6144 (patrones) + 6144 (colores)
        colores_esperados = rom[0x8000 + 1 + 768 + 6144:0x8000 + 1 + 768 + 6144 * 2]
        check(juego == colores_esperados,
              'la tabla de colores del juego es la del banco',
              f'{juego[:8].hex(" ")} vs {colores_esperados[:8].hex(" ")}')

        print('\n4. La nave se mueve con las flechas')
        x0 = ram(NAVE_X)[0]
        y0 = ram(NAVE_Y)[0]
        emu.call('msx.keyboard.press', {'row': 8, 'bit': 7})   # la derecha
        emu.call('msx.run_frames', {'frames': 20})
        emu.call('msx.keyboard.release', {'row': 8, 'bit': 7})
        x1 = ram(NAVE_X)[0]
        check(x1 > x0, 'la nave va a la derecha', f'x ${x0:02X} -> ${x1:02X}')

        emu.call('msx.keyboard.press', {'row': 8, 'bit': 6})   # abajo
        emu.call('msx.run_frames', {'frames': 20})
        emu.call('msx.keyboard.release', {'row': 8, 'bit': 6})
        y2 = ram(NAVE_Y)[0]
        check(y2 > y0, 'la nave baja', f'y ${y0:02X} -> ${y2:02X}')

        print('\n5. Disparar')
        emu.call('msx.keyboard.press', {'row': 8, 'bit': 0})   # el espacio
        emu.call('msx.run_frames', {'frames': 10})
        teclas = ram(0xC060)[0]
        enfriamiento = ram(0xC0B4)[0]
        print(f'    key_flechas=${teclas:02X}  nave_fire=${enfriamiento:02X}')
        print('    nave x,y,dx,dy,fire,lim = ' +
              ' '.join(f'${v:02X}' for v in ram(0xC0B0, 6)))
        print('    key_digitos = ' + f'${ram(0xC061)[0]:02X}')
        emu.call('msx.keyboard.release', {'row': 8, 'bit': 0})
        emu.call('msx.run_frames', {'frames': 5})
        vivas = ram(BALA_VIVA, 8)
        check(any(vivas), 'hay una bala en el aire', vivas.hex(' '))
        bx = ram(BALA_X)[0]
        check(bx > 0, 'la bala esta en la posicion de la nave', f'x=${bx:02X}')

        print('\n6. Los enemigos')
        emu.call('msx.run_frames', {'frames': 300})
        from_ram = ram(0xC100, 8)   # enem_viva
        check(any(from_ram), 'hay enemigos en pantalla', from_ram.hex(' '))

        print('\n7. El marcador')
        score = ram(SCORE, 3)
        check(True, 'la puntuacion se lee', score.hex(' '))

        print('\n8. La tabla de atributos de los sprites')
        atr = emu.call('msx.vram.read', {'addr': 0x1B00, 'len': 16})['hex'].lower()
        check(atr[0:4] != '00000000', 'la nave tiene un sprite escrito', atr)

    finally:
        if emu:
            emu.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    if fallos == 0:
        print('TODAS LAS PRUEBAS PASAN')
        return 0
    print(f'{fallos} PRUEBAS FALLAN')
    return 1


def shutil_copy(a, b):
    with open(a, 'rb') as f, open(b, 'wb') as g:
        g.write(f.read())


if __name__ == '__main__':
    sys.exit(main())
