#!/usr/bin/env python3
"""Analyse the Cybernoid sprite/video model to design the MSX VDP port."""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))
from z80dis import z80

MEM = Path(r'C:\Dev\cybernoidMSX\spectrum\cybernoid_after_lddr.bin')
with open(MEM, 'rb') as f:
    mem = f.read()


def disasm(start, length, label=''):
    print(f'\n--- ${start:04X} {label} ---')
    pos = start
    end = start + length
    while pos < end:
        off = pos - 0x4000
        if off < 0 or off >= len(mem):
            break
        chunk = mem[off:off + 4]
        try:
            d = z80.decode(chunk, pos)
            print(f'   ${pos:04X}: {z80.decoded2str(d):<30s} ; {chunk[:d.len].hex()}')
            pos += d.len
        except Exception:
            print(f'   ${pos:04X}: ??? ; {mem[off]:02X}')
            pos += 1


def dump(addr, length, label):
    print(f'\n--- {label} @ ${addr:04X} ---')
    for row in range(length // 16 + (1 if length % 16 else 0)):
        a = addr + row * 16
        data = ' '.join(f'{mem[a - 0x4000 + i]:02X}' for i in range(16)
                        if a - 0x4000 + i < len(mem))
        asc = ''.join(chr(mem[a - 0x4000 + i]) if 32 <= mem[a - 0x4000 + i] < 127
                       else '.' for i in range(16) if a - 0x4000 + i < len(mem))
        print(f'   ${a:04X}: {data:<47s} {asc}')


# The sprite drawing routine
disasm(0x67B9, 0x70, 'sprite draw routine')
disasm(0x6820, 0x50, 'after sprite draw')

# The sprite table at $67EE
dump(0x67EE, 0x60, 'sprite table')

# Screen address tables $6300 / $6400
dump(0x6300, 0x20, 'screen addr table A')
dump(0x6400, 0x20, 'screen addr table B')

# The "shadow"/sprite data area at $5F00
dump(0x5F00, 0x40, 'sprite data at $5F00')

# Graphics data in block 7 ($8000-$912C in post-LDDR)
dump(0x8000, 0x60, 'block 7 graphics data')
dump(0x8060, 0x60, 'block 7 graphics data +60')

# Count distinct 8-byte patterns in block 7 (candidate sprite sheets)
patterns = Counter()
for i in range(0x8000, 0x912C - 7, 8):
    pat = bytes(mem[i - 0x4000:i - 0x4000 + 8])
    if pat != b'\x00' * 8:
        patterns[pat] += 1
print(f'\nDistinct non-blank 8-byte patterns in block 7: {len(patterns)}')
print(f'Total 8-byte slots in block 7: {(0x912C - 0x8000) // 8}')
