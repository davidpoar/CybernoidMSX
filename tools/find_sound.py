#!/usr/bin/env python3
"""Find sound/beeper routines in the Cybernoid memory image."""
from z80dis import z80
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import MEM_AFTER_LDDR, DISASM_SOUND


def disasm_at(mem, addr, length):
    out = []
    pos = addr
    end = addr + length
    while pos < end:
        off = pos - 0x4000
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            out.append(f'${pos:04X}: {asm:<32s}  ; {chunk[:decoded.len].hex()}')
            pos += decoded.len
        except:
            out.append(f'${pos:04X}: ???  ; {mem[off]:02X}')
            pos += 1
    return '\n'.join(out)


def main():
    with open(MEM_AFTER_LDDR, 'rb') as f:
        mem = f.read()

    io_addrs = []
    pos = 0x4000
    while pos < 0xFFFF:
        off = pos - 0x4000
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            if 'OUT (0x00fe)' in asm.lower() or 'OUT (0xfe)' in asm.lower():
                io_addrs.append(pos)
            pos += decoded.len
        except:
            pos += 1

    sections = []
    sections.append('=== SOUND / BEEPER ANALYSIS ===\n')
    sections.append(f'\nFound {len(io_addrs)} OUT ($FE) instructions:')
    for a in io_addrs:
        sections.append(f'  ${a:04X}')

    sections.append('\n\n=== $6600-66A0 area ===')
    sections.append(disasm_at(mem, 0x6600, 0xA0))

    sections.append('\n\n=== $7BFC area (sound init?) ===')
    sections.append(disasm_at(mem, 0x7BFC, 0x80))

    sections.append('\n\n=== $85BA area (called from interrupt handler) ===')
    sections.append(disasm_at(mem, 0x85BA, 0x80))

    out_path = DISASM_SOUND
    with open(out_path, 'w') as f:
        f.write('\n'.join(sections) + '\n')

    print(f'Saved sound analysis to {out_path}')


if __name__ == '__main__':
    main()