#!/usr/bin/env python3
"""Analyse the Cybernoid video routines: find every access to the Spectrum
screen memory ($4000-$5AFF pixels, $5800-$5AFF attributes) so we can work out
what has to be rewritten for the MSX VDP.
"""
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))
from paths import SPECTRUM_DISASM_DIR

from z80dis import z80

MEM = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin')

with open(MEM, 'rb') as f:
    mem = f.read()

SCREEN_PIXELS = (0x4000, 0x5AFF)
SCREEN_ATTRS = (0x5800, 0x5AFF)


def disasm_at(addr, length):
    """Disassemble and yield (addr, asm_text, size)."""
    pos = addr
    end = addr + length
    while pos < end:
        off = pos - 0x4000
        if off < 0 or off >= len(mem):
            break
        chunk = mem[off:off + 4]
        try:
            d = z80.decode(chunk, pos)
            yield pos, z80.decoded2str(d), d.len
            pos += d.len
        except Exception:
            yield pos, '???', 1
            pos += 1


def find_refs(target_range):
    """Find instructions whose 16-bit operand falls in target_range."""
    hits = []
    pos = 0x4000
    while pos <= 0xFFFF:
        off = pos - 0x4000
        chunk = mem[off:off + 4]
        try:
            d = z80.decode(chunk, pos)
            size = d.len
            asm = z80.decoded2str(d)
        except Exception:
            pos += 1
            continue

        # Look for a 16-bit operand in the instruction bytes
        operand = None
        for i in range(1, min(size - 1, 3)):
            v = chunk[i] | (chunk[i + 1] << 8)
            if target_range[0] <= v <= target_range[1]:
                operand = v
                break
        if operand is not None:
            hits.append((pos, asm, operand))
        pos += size
    return hits


print('=' * 70)
print('CYBERNOID VIDEO ANALYSIS')
print('=' * 70)

# ------------------------------------------------------------------
# 1. Direct references to the screen / attribute areas
# ------------------------------------------------------------------
print('\n1. Instructions referencing $4000-$5AFF (screen + attributes)')
hits = find_refs((0x4000, 0x5AFF))
print(f'   Found {len(hits)} instructions\n')
by_addr = defaultdict(list)
for addr, asm, operand in hits:
    by_addr[operand].append((addr, asm))

for operand in sorted(by_addr):
    entries = by_addr[operand]
    print(f'   ${operand:04X} ({len(entries)} refs):')
    for addr, asm in entries[:6]:
        print(f'      ${addr:04X}: {asm}')
    if len(entries) > 6:
        print(f'      ... and {len(entries) - 6} more')
    print()

# ------------------------------------------------------------------
# 2. Locate the main drawing routines
# ------------------------------------------------------------------
print('\n' + '=' * 70)
print('2. Candidate drawing routines')
print('=' * 70)

# Known from the earlier analysis
CANDIDATES = [
    (0x671E, 'screen clear (called from entry)'),
    (0x6726, 'LD HL,$4000 (pixel base)'),
    (0x679D, 'LD DE,$5800 (attr base)'),
    (0x67AD, 'LD HL,$5800 (attr base)'),
    (0x77F0, 'LD DE,$4000 (pixel base)'),
    (0x6E7B, 'LD DE,$4000'),
    (0x7465, 'wait / sync (called from entry)'),
    (0x688F, 'called from main loop (frame 1)'),
    (0x68AC, 'called from main loop (frame 2)'),
]

for addr, note in CANDIDATES:
    print(f'\n--- ${addr:04X}  ({note}) ---')
    for a, asm, size in disasm_at(addr, 0x40):
        print(f'   ${a:04X}: {asm}')

# ------------------------------------------------------------------
# 3. Writes to screen memory (LD (HL),A / LD (DE),A patterns)
# ------------------------------------------------------------------
print('\n' + '=' * 70)
print('3. Instructions that WRITE to screen memory')
print('=' * 70)

write_hits = []
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

    # LD (HL),A / LD (DE),A / LD (HL),n etc. inside the screen area
    if ('LD (HL)' in asm or 'LD (DE)' in asm or 'LD (BC)' in asm
            or 'LDIR' in asm or 'LDDR' in asm):
        operand = None
        for i in range(1, min(size - 1, 3)):
            v = chunk[i] | (chunk[i + 1] << 8)
            if 0x4000 <= v <= 0x5AFF:
                operand = v
                break
        if operand is not None:
            write_hits.append((pos, asm, operand))
    pos += size

print(f'\n   {len(write_hits)} write instructions with a screen operand:')
for addr, asm, operand in write_hits[:40]:
    print(f'      ${addr:04X}: {asm}   (operand ${operand:04X})')
if len(write_hits) > 40:
    print(f'      ... and {len(write_hits) - 40} more')

# ------------------------------------------------------------------
# 4. Sprite / bitmap data references
# ------------------------------------------------------------------
print('\n' + '=' * 70)
print('4. Where the graphics data lives')
print('=' * 70)
# The block 7 data (loaded at $8000 in the original) contains graphics.
# In the post-LDDR image it lives at $8000-$912C.
print('\n   Block 7 (graphics/tables) in post-LDDR layout: $8000-$912C')
print('   First 64 bytes:')
for row in range(4):
    addr = 0x8000 + row * 16
    data = ' '.join(f'{mem[addr - 0x4000 + i]:02X}' for i in range(16))
    ascii_ = ''.join(chr(mem[addr - 0x4000 + i]) if 32 <= mem[addr - 0x4000 + i] < 127
                      else '.' for i in range(16))
    print(f'   ${addr:04X}: {data}  {ascii_}')

print('\n   Screen memory content in the post-LDDR image ($4000-$403F):')
for row in range(4):
    addr = 0x4000 + row * 16
    data = ' '.join(f'{mem[addr - 0x4000 + i]:02X}' for i in range(16))
    print(f'   ${addr:04X}: {data}')
