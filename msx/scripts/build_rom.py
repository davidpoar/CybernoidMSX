#!/usr/bin/env python3
"""Build the 64K Cybernoid MSX ROM (ASCII16 mapper).

ROM layout (64 KB = 4 banks of 16 KB):

  file $0000-$3FFF  bank 0 -> MSX $4000-$7FFF
        "AB" header, engine: INIT, VDP routines, bank switching,
        music, input
  file $4000-$7FFF  bank 1 -> MSX $8000-$BFFF (window)
        assets: screen maps, tiles, sprites
  file $8000-$BFFF  bank 2 -> MSX $8000-$BFFF (window)
        assets: compressed tile maps
  file $C000-$FFFF  bank 3 -> MSX $8000-$BFFF (window)
        assets: more data

The engine is assembled with `org $4000`; the assets are placed in
the other banks by the build script.
"""
import os
import struct
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MSX_DIR = SCRIPT_DIR.parent
TOOLS_DIR = MSX_DIR.parent / 'tools'
BUILD_DIR = MSX_DIR / 'build'
SRC_DIR = MSX_DIR / 'src'
TMP_DIR = BUILD_DIR / 'tmp'

INIT_ASM = SRC_DIR / 'rom.asm'
INIT_BIN = BUILD_DIR / 'rom_engine.bin'
INIT_SYM = BUILD_DIR / 'rom_engine.sym'
ROM_OUT = BUILD_DIR / 'cybernoid.rom'
BANK_SIZE = 0x4000
ROM_BANKS = 4
ROM_SIZE = BANK_SIZE * ROM_BANKS

# Assets to place in the switchable banks.  Each entry is
#   (bank number, source file or None)
BANK_CONTENTS = {
    1: None,      # filled in later: screen maps and tiles
    2: None,      # filled in later: compressed tile maps
    3: None,      # filled in later: sprite and misc data
}


def run_pasmo(source, bin_out, sym_out=None):
    cmd = ['pasmo']
    if sym_out:
        cmd += [str(source), str(bin_out), str(sym_out)]
    else:
        cmd += ['--bin', str(source), str(bin_out)]
    print(f'  pasmo {source.name}')
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print('STDERR:', result.stderr)
        print('STDOUT:', result.stdout)
        sys.exit(1)
    return result


def build_rom():
    print('=' * 62)
    print('Building Cybernoid MSX ROM (64K, ASCII16)')
    print('=' * 62)

    print('\n[1/3] Assembling the engine...')
    BUILD_DIR.mkdir(exist_ok=True)
    run_pasmo(INIT_ASM, INIT_BIN, INIT_SYM)

    with open(INIT_BIN, 'rb') as f:
        engine = f.read()
    print(f'  engine: {len(engine)} bytes')

    if len(engine) > BANK_SIZE:
        print(f'ERROR: the engine does not fit in a 16K bank '
              f'({len(engine)} > {BANK_SIZE})')
        sys.exit(1)

    print('\n[2/3] Laying out the banks...')
    rom = bytearray(ROM_SIZE)

    # Bank 0: the engine
    rom[0:len(engine)] = engine

    # Banks 1-3: the assets
    for bank, source in BANK_CONTENTS.items():
        # Every asset bank starts with an ID byte so it can be identified
        # at run time (and by the tests).
        off = bank * BANK_SIZE
        rom[off] = 0xB0 + bank

        if source is None:
            continue
        path = Path(source)
        if not path.is_absolute():
            path = MSX_DIR / path
        with open(path, 'rb') as f:
            data = f.read()
        if len(data) > BANK_SIZE - 1:
            print(f'ERROR: {path.name} does not fit in bank {bank} '
                  f'({len(data)} > {BANK_SIZE - 1})')
            sys.exit(1)
        rom[off + 1:off + 1 + len(data)] = data
        print(f'  bank {bank}: {path.name} ({len(data)} bytes)')

    print('\n[3/3] Writing the ROM...')
    with open(ROM_OUT, 'wb') as f:
        f.write(rom)
    print(f'  {ROM_OUT} ({len(rom)} bytes)')

    # Sanity check of the header
    assert rom[0:2] == b'AB', 'bad signature'
    init_addr = struct.unpack_from('<H', rom, 2)[0]
    print(f'  signature "AB", INIT = ${init_addr:04X}')
    if not (0x4000 <= init_addr < 0x8000):
        print(f'WARNING: INIT is outside the cartridge window')

    return ROM_OUT


if __name__ == '__main__':
    build_rom()
