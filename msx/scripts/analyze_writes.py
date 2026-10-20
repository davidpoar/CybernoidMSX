#!/usr/bin/env python3
"""Find every write the Cybernoid game performs into $4000-$7FFF.

That range is cartridge ROM in a normal MSX configuration, so every
one of these writes is lost if the game runs from a ROM cartridge.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))
from z80dis import z80

MEM = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin')
with open(MEM, 'rb') as f:
    mem = f.read()

# Store instructions and their 16-bit operands
STORE_OPS = {
    0x22: 'LD (nn),HL', 0x2A: 'LD HL,(nn)',
    0x32: 'LD (nn),A',  0x3A: 'LD A,(nn)',
    0x36: 'LD (HL),n',
}

print('Writes into $4000-$7FFF (cartridge ROM in a normal MSX config):')
print()

# Scan for absolute stores
hits = []
pos = 0x4000
while pos <= 0xFFFF:
    off = pos - 0x4000
    chunk = mem[off:off + 4]
    try:
        d = z80.decode(chunk, pos)
        asm = z80.decoded2str(d)
        size = d.len
    except Exception:
        pos += 1
        continue

    op = mem[off]
    if op in (0x22, 0x32) and size >= 3:
        addr = mem[off+1] | (mem[off+2] << 8)
        if 0x4000 <= addr <= 0x7FFF:
            hits.append((pos, addr, asm))
    pos += size

# Also: indirect stores through HL/DE are the common case; find the
# places where those pointers are set up.
print('Absolute stores (LD (nn),A / LD (nn),HL):')
for addr_pos, target, asm in hits:
    print(f'  ${addr_pos:04X}: {asm:24s} -> writes to ${target:04X}')

print()
print('Now the indirect ones. The game keeps screen pointers in variables;')
print('let us find every LD HL,nn / LD DE,nn that feeds a store into the')
print('screen area.')
print()

# Find all "LD HL,nn" / "LD DE,nn" where nn is in $4000-$7FFF, then look
# ahead a few instructions for a store.
pointers = []
pos = 0x4000
while pos <= 0xFFFF:
    off = pos - 0x4000
    chunk = mem[off:off + 4]
    try:
        d = z80.decode(chunk, pos)
        asm = z80.decoded2str(d)
        size = d.len
    except Exception:
        pos += 1
        continue

    op = mem[off]
    if op in (0x21, 0x11) and size >= 3:
        val = mem[off+1] | (mem[off+2] << 8)
        if 0x4000 <= val <= 0x7FFF:
            pointers.append((pos, val, 'HL' if op == 0x21 else 'DE'))
    pos += size

print(f'Pointers loaded with a screen address: {len(pointers)}')
for p, v, r in pointers[:40]:
    print(f'  ${p:04X}: LD {r},${v:04X}')

# The decisive check: does the game write to the variables in $6300-$64BF
# (the screen address tables) and to $67xx (sprite variables)?
print()
print('Variables the game writes in the $6300-$67FF area:')
for p, v, r in pointers:
    if 0x6300 <= v <= 0x67FF:
        print(f'  ${p:04X}: LD {r},${v:04X}   (a variable in the ROM area)')
