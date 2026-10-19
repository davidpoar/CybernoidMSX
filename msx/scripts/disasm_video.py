#!/usr/bin/env python3
"""Disassemble specific Cybernoid video routines (targeted, not a blind scan)."""
import sys
from pathlib import Path

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
        except Exception as e:
            print(f'   ${pos:04X}: ??? ; {mem[off]:02X}')
            pos += 1


# The routines that reference the screen memory
disasm(0x66C0, 0x90, 'screen/attr area ($66C0)')
disasm(0x671E, 0xC0, 'screen clear + draw ($671E)')
disasm(0x77E0, 0x60, 'LD DE,$4000 ($77F0)')
disasm(0x851E, 0x60, 'LD HL,$4040 / $4140 ($8526)')
disasm(0x79D8, 0x30, 'LD HL,$4020 ($79E2)')
disasm(0x84F0, 0x30, 'LD HL,$4102 ($84FB)')
