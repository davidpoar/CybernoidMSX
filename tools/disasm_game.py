#!/usr/bin/env python3
"""Disassemble the Cybernoid game entry point from the post-LDDR memory image."""
from z80dis import z80
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import MEM_AFTER_LDDR, DISASM_FULL


def disasm_to_file(data, base_addr, start_addr, end_addr, fout):
    pos = start_addr
    while pos < end_addr:
        offset = pos - base_addr
        if offset < 0 or offset >= len(data):
            fout.write(f'${pos:04X}: [out of bounds]\n')
            break
        chunk = data[offset:offset+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm_str = z80.decoded2str(decoded)
            size = decoded.len
            raw = data[offset:offset+size]
            fout.write(f'${pos:04X}: {asm_str:<32s}  ; {raw.hex()}\n')
            pos += size
        except Exception as e:
            fout.write(f'${pos:04X}: ??? {e}  ; byte: ${data[offset]:02X}\n')
            pos += 1


def main():
    with open(MEM_AFTER_LDDR, 'rb') as f:
        mem = f.read()
    assert len(mem) == 49152

    with open(DISASM_FULL, 'w') as f:
        f.write('=== CYBERNOID GAME ENTRY ($6504) ===\n\n')
        f.write('=== Entry point ===\n')
        disasm_to_file(mem, 0x4000, 0x6504, 0x6530, f)
        f.write('\n=== Subroutine at $70B4 (interrupt init) ===\n')
        disasm_to_file(mem, 0x4000, 0x70B4, 0x7160, f)
        f.write('\n=== Initial call sites ===\n')
        disasm_to_file(mem, 0x4000, 0x6518, 0x65A0, f)

    print('Done')


if __name__ == '__main__':
    main()