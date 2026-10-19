#!/usr/bin/env python3
"""Disassemble parts of the Cybernoid loader and game block 9."""
from z80dis import z80
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import LOADER_DECRYPTED, BLOCK9_MAIN, DISASM_LOADER, DISASM_BLOCK9


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
    with open(LOADER_DECRYPTED, 'rb') as f:
        loader = f.read()
    with open(BLOCK9_MAIN, 'rb') as f:
        block9 = f.read()

    with open(DISASM_LOADER, 'w') as f:
        f.write('=== LOADER AT $FC00-$FEFF (decrypted) ===\n\n')
        f.write('=== Self-decrypt header ($FC00-$FC12) ===\n')
        disasm_to_file(loader, 0xFC00, 0xFC00, 0xFC16, f)
        f.write('\n=== Entry point $FE3A (after self-decrypt) ===\n')
        disasm_to_file(loader, 0xFC00, 0xFE3A, 0xFEB0, f)

    with open(DISASM_BLOCK9, 'w') as f:
        f.write('=== BLOCK 9 ($6104-$FBFF original / $6504-$FFFF after LDDR) ===\n\n')
        f.write('=== Entry point $6504 (offset 0 in block 9) ===\n')
        disasm_to_file(block9, 0x6104, 0x6104, 0x6180, f)

    print('Done')


if __name__ == '__main__':
    main()