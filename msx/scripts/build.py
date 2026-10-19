#!/usr/bin/env python3
"""Build script for the Cybernoid MSX port.

Outputs
-------
  build/cybernoid.com   MSX-DOS 2 executable (needs a 64K TPA)
  build/cybernoid.rom   16K MSX ROM cartridge (logic + I/O only)

Memory layout of the .COM
------------------------
  $0100-$01FF : stub (entry point)
  $0200-$02FF : MSX I/O routines      (IO_BASE)
  $0300-$03FF : init code             (INIT_BASE)
  $0400-$07FF : video module          (VIDEO_BASE)
  $0800-$22FB : game part 1           (Spectrum $6504-$7FFF)
  $2300-$A2FF : game part 2           (Spectrum $8000-$FFFF)

The stub copies the game to its final place ($6504-$FFFF), switches
the machine to "all RAM" mode and jumps to the game entry point.

Why the game is split
---------------------
The game contains ~1200 absolute address references inside the
$6504-$FFFF range. They only work if the game sits at exactly the
same addresses as on the Spectrum.

MSX page 1 ($4000-$7FFF) is ROM (our cartridge) and pages 2-3
($8000-$FFFF) are RAM, which happens to match the Spectrum layout
perfectly:

    Spectrum $6504-$7FFF  ->  page 1
    Spectrum $8000-$FFFF  ->  pages 2-3

But the game also needs writable memory at $4000-$5AFF (the screen)
and $5B00-$64BF (attribute copy, sprite data, screen address
tables), so page 1 must be RAM as well. That means the machine has
to run in "all RAM" mode (MSX-DOS 2 with a memory mapper), where
the whole $0000-$FFFF is RAM.

Because of that, the .ROM cartridge variant can only offer the
game logic and the I/O shims - the screen buffer cannot live in
cartridge ROM.
"""
import os
import re
import sys
import shutil
import subprocess
import struct
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
MSX_DIR = SCRIPT_DIR.parent
TOOLS_DIR = MSX_DIR.parent / 'tools'
BUILD_DIR = MSX_DIR / 'build'
SRC_DIR = MSX_DIR / 'src'
TMP_DIR = BUILD_DIR / 'tmp'

GAME_IN = TOOLS_DIR.parent / 'spectrum' / 'cybernoid_after_lddr.bin'

# ---- .COM layout ----
COM_STUB   = 0x0100
COM_IO     = 0x0200
COM_INIT   = 0x0300
COM_VIDEO  = 0x0400
COM_GAME1  = 0x0800      # game part 1 (Spectrum $6504-$7FFF)
COM_GAME2  = 0x2300      # game part 2 (Spectrum $8000-$FFFF)

# ---- .ROM layout ----
ROM_STUB   = 0x4010
ROM_IO     = 0x4040
ROM_INIT   = 0x4200
ROM_VIDEO  = 0x4400
ROM_GAME1  = 0x6504

KBD_BUF_COM = 0x0700     # keyboard buffer (RAM)
KBD_BUF_ROM = 0x4700     # keyboard buffer... must be RAM, see note

# ---- Patches ----
# Part 1 ($6504-$7FFF) lives in ROM for the .ROM build and in RAM
# for the .COM build; either way the patches are applied to the
# binary before it is placed.
KBD_PATCHES = [0x65ED, 0x65F4, 0x660D, 0x7B4C]
BEEPER_PATCHES = [0x651F]
BEEPER_PATCHES_RAM = [0x8637]     # part 2, patched at runtime

GAME_SPEC_START = 0x6504
GAME_PART1_END = 0x7FFF
GAME_PART2_START = 0x8000
GAME_PART2_END = 0xFFFF


def run_pasmo(source, bin_out, sym_out=None):
    cmd = ['pasmo']
    if sym_out:
        cmd += [str(source), str(bin_out), str(sym_out)]
    else:
        cmd += ['--bin', str(source), str(bin_out)]
    print(f'  pasmo {source.name}')
    # pasmo resolves INCLUDE relative to the working directory
    result = subprocess.run(cmd, capture_output=True, text=True,
                            cwd=str(TMP_DIR))
    if result.returncode != 0:
        print('STDERR:', result.stderr)
        print('STDOUT:', result.stdout)
        sys.exit(1)
    return result


def parse_symbols(sym_file):
    symbols = {}
    if not sym_file.exists():
        return symbols
    with open(sym_file) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 3 and parts[1].upper() == 'EQU':
                try:
                    symbols[parts[0]] = int(parts[2].rstrip('H'), 16)
                except ValueError:
                    pass
    return symbols


def preprocess(source, dest, defines):
    """Replace @NAME@ placeholders and write the result to dest."""
    text = source.read_text(encoding='utf-8')
    for key, value in defines.items():
        text = text.replace(f'@{key}@', f'${value:04X}')
    dest.write_text(text, encoding='utf-8')


def build_module(name, defines, out_bin, out_sym=None):
    """Preprocess + assemble one module."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    src = SRC_DIR / name
    tmp = TMP_DIR / name
    preprocess(src, tmp, defines)
    # config.asm also carries the placeholders
    preprocess(SRC_DIR / 'config.asm', TMP_DIR / 'config.asm', defines)
    if out_sym:
        run_pasmo(tmp, out_bin, out_sym)
    else:
        run_pasmo(tmp, out_bin)


def write_call(buf, offset, target):
    buf[offset] = 0xCD
    buf[offset + 1] = target & 0xFF
    buf[offset + 2] = (target >> 8) & 0xFF


def patch_bytes(buf, spec_addr, target, base, what):
    """Patch a 2-byte instruction into a 3-byte CALL at spec_addr."""
    off = spec_addr - base
    if buf[off] != 0xDB and buf[off] != 0xD3:
        print(f'  WARNING: ${spec_addr:04X} = {buf[off]:02X} {buf[off+1]:02X}'
              f' (expected DB FE / D3 FE)')
    write_call(buf, off, target)
    print(f'  {what} at Spectrum ${spec_addr:04X} -> CALL ${target:04X}')


def build_com(symbols):
    """Build the MSX-DOS .COM executable."""
    print('\n[1/4] Assembling modules for the .COM...')
    defines = {
        'IO_BASE': COM_IO,
        'INIT_BASE': COM_INIT,
        'VIDEO_BASE': COM_VIDEO,
        'KBD_BUF': KBD_BUF_COM,
    }
    build_module('io.asm', defines, BUILD_DIR / 'com_io.bin',
                 BUILD_DIR / 'com_io.sym')
    build_module('init.asm', defines, BUILD_DIR / 'com_init.bin',
                 BUILD_DIR / 'com_init.sym')
    build_module('video.asm', defines, BUILD_DIR / 'com_video.bin',
                 BUILD_DIR / 'com_video.sym')
    build_module('stub.asm', defines, BUILD_DIR / 'com_stub.bin',
                 BUILD_DIR / 'com_stub.sym')

    com_syms = parse_symbols(BUILD_DIR / 'com_io.sym')
    kbd_addr = com_syms['MSX_KBD_READ']
    beeper_addr = com_syms['MSX_BEEPER']
    im2_addr = com_syms['MSX_IM2_HANDLER']
    print(f'  MSX_KBD_READ    = ${kbd_addr:04X}')
    print(f'  MSX_BEEPER      = ${beeper_addr:04X}')
    print(f'  MSX_IM2_HANDLER = ${im2_addr:04X}')

    print('\n[2/4] Preparing the game data...')
    with open(GAME_IN, 'rb') as f:
        mem = f.read()
    assert len(mem) == 49152

    part1 = bytearray(mem[GAME_SPEC_START - 0x4000:
                          GAME_PART1_END - 0x4000 + 1])
    part2 = bytearray(mem[GAME_PART2_START - 0x4000:
                          GAME_PART2_END - 0x4000 + 1])
    assert len(part1) == 0x1AFC, len(part1)
    assert len(part2) == 0x8000, len(part2)

    # Patch part 1 (its final location depends on the variant, but the
    # CALL targets are the same RAM addresses in both cases)
    for a in KBD_PATCHES:
        patch_bytes(part1, a, kbd_addr, GAME_SPEC_START, 'IN A,($FE)')
    for a in BEEPER_PATCHES:
        patch_bytes(part1, a, beeper_addr, GAME_SPEC_START, 'OUT ($FE),A')

    # Part 2 is patched at runtime (the init code does it), so we
    # record where the runtime patch must go.
    print('\n[3/4] Building the .COM file...')
    stub = (BUILD_DIR / 'com_stub.bin').read_bytes()
    io_bin = (BUILD_DIR / 'com_io.bin').read_bytes()
    init_bin = (BUILD_DIR / 'com_init.bin').read_bytes()
    video_bin = (BUILD_DIR / 'com_video.bin').read_bytes()

    # Assemble the file image at its final addresses
    image = bytearray(0xA300)
    image[COM_STUB:COM_STUB + len(stub)] = stub
    image[COM_IO:COM_IO + len(io_bin)] = io_bin
    image[COM_INIT:COM_INIT + len(init_bin)] = init_bin
    image[COM_VIDEO:COM_VIDEO + len(video_bin)] = video_bin
    image[COM_GAME1:COM_GAME1 + len(part1)] = part1
    image[COM_GAME2:COM_GAME2 + len(part2)] = part2

    # MSX-DOS .COM format: 256-byte header then the code
    header = bytearray(256)
    out = bytearray(header)
    out += image[0x0100:]

    com_path = BUILD_DIR / 'cybernoid.com'
    with open(com_path, 'wb') as f:
        f.write(out)
    print(f'  Saved {com_path} ({len(out)} bytes)')
    print(f'    game part 1 at ${COM_GAME1:04X}, part 2 at ${COM_GAME2:04X}')

    print('\n[4/4] Recording the runtime patch list...')
    with open(BUILD_DIR / 'runtime_patches.txt', 'w') as f:
        f.write('# Spectrum address -> target (patched at runtime by the init code)\n')
        for a in BEEPER_PATCHES_RAM:
            f.write(f'{a:04X} {beeper_addr:04X}\n')
    for a in BEEPER_PATCHES_RAM:
        print(f'  runtime: OUT ($FE),A at ${a:04X} -> CALL ${beeper_addr:04X}')

    return com_path


def build_rom():
    """Build the 16K MSX ROM cartridge (logic + I/O, no video)."""
    print('\nBuilding the .ROM cartridge variant...')
    defines = {
        'IO_BASE': ROM_IO,
        'INIT_BASE': ROM_INIT,
        'VIDEO_BASE': ROM_VIDEO,
        'KBD_BUF': 0x4700,      # NOTE: this is ROM space; see below
    }
    build_module('io.asm', defines, BUILD_DIR / 'rom_io.bin',
                 BUILD_DIR / 'rom_io.sym')
    build_module('init.asm', defines, BUILD_DIR / 'rom_init.bin',
                 BUILD_DIR / 'rom_init.sym')
    build_module('stub.asm', defines, BUILD_DIR / 'rom_stub.bin',
                 BUILD_DIR / 'rom_stub.sym')

    rom_syms = parse_symbols(BUILD_DIR / 'rom_io.sym')
    kbd_addr = rom_syms['MSX_KBD_READ']
    beeper_addr = rom_syms['MSX_BEEPER']

    with open(GAME_IN, 'rb') as f:
        mem = f.read()
    part1 = bytearray(mem[GAME_SPEC_START - 0x4000:
                          GAME_PART1_END - 0x4000 + 1])
    for a in KBD_PATCHES:
        patch_bytes(part1, a, kbd_addr, GAME_SPEC_START, 'IN A,($FE)')
    for a in BEEPER_PATCHES:
        patch_bytes(part1, a, beeper_addr, GAME_SPEC_START, 'OUT ($FE),A')

    stub = (BUILD_DIR / 'rom_stub.bin').read_bytes()
    io_bin = (BUILD_DIR / 'rom_io.bin').read_bytes()
    init_bin = (BUILD_DIR / 'rom_init.bin').read_bytes()

    rom = bytearray([0xFF] * 16384)
    rom[0] = ord('A')
    rom[1] = ord('B')
    rom[2] = ROM_STUB & 0xFF
    rom[3] = (ROM_STUB >> 8) & 0xFF
    rom[4] = rom[5] = rom[6] = rom[7] = rom[8] = rom[9] = 0

    off = ROM_STUB - 0x4000
    rom[off:off + len(stub)] = stub
    off = ROM_IO - 0x4000
    rom[off:off + len(io_bin)] = io_bin
    off = ROM_INIT - 0x4000
    rom[off:off + len(init_bin)] = init_bin
    off = ROM_GAME1 - 0x4000
    rom[off:off + len(part1)] = part1

    rom_path = BUILD_DIR / 'cybernoid.rom'
    with open(rom_path, 'wb') as f:
        f.write(rom)
    print(f'  Saved {rom_path} (16384 bytes)')
    return rom_path


def main():
    print('=' * 62)
    print('Building Cybernoid MSX port')
    print('=' * 62)
    BUILD_DIR.mkdir(exist_ok=True)

    com = build_com(symbols=None)
    rom = build_rom()

    print('\n' + '=' * 62)
    print('Build complete!')
    print(f'  {com}')
    print(f'  {rom}')
    print('=' * 62)


if __name__ == '__main__':
    main()
