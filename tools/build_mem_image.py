#!/usr/bin/env python3
"""Build the complete 48K Spectrum memory image with all Cybernoid blocks
and simulate the LDDR to compute the final memory layout.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import (LOADER_DECRYPTED, RAW_BLOCK_07, RAW_BLOCK_09,
                   MEM_BEFORE_LDDR, MEM_AFTER_LDDR)


def build(loader_path, block7_path, block9_path, before_path, after_path):
    """Build both the pre-LDDR and post-LDDR memory images."""
    # 48K Spectrum RAM: $4000-$FFFF, 49152 bytes
    mem = bytearray(49152)

    # 1) Decrypted loader code at $FC00-$FEFF (768 bytes)
    with open(loader_path, 'rb') as f:
        loader = f.read()
    assert len(loader) == 768
    for i, b in enumerate(loader):
        mem[0xFC00 + i - 0x4000] = b

    # 2) Block 7 (data) at $8000-$912C (4405 bytes per header)
    with open(block7_path, 'rb') as f:
        raw7 = f.read()
    block7 = raw7[1:-1]
    assert len(block7) == 4405, f'Block 7 expected 4405 bytes, got {len(block7)}'
    for i, b in enumerate(block7):
        mem[0x8000 + i - 0x4000] = b

    # 3) Block 9 (main game code) at $6104-$FBFF (39676 bytes per header)
    with open(block9_path, 'rb') as f:
        raw9 = f.read()
    block9 = raw9[1:-1]
    assert len(block9) == 39676, f'Block 9 expected 39676 bytes, got {len(block9)}'
    for i, b in enumerate(block9):
        mem[0x6104 + i - 0x4000] = b

    with open(before_path, 'wb') as f:
        f.write(mem)
    print(f'Pre-LDDR memory image: {len(mem)} bytes -> {before_path}')

    # Apply LDDR step by step (with proper 16-bit wrapping)
    # HL=$FBFF, DE=$FFFF, BC=$9AFC (39676)
    # copies (HL) -> (DE), then HL--, DE--, BC--; loops while BC != 0
    hl = 0xFBFF
    de = 0xFFFF
    bc = 39676
    while bc > 0:
        a = mem[hl - 0x4000]
        mem[de - 0x4000] = a
        hl = (hl - 1) & 0xFFFF
        de = (de - 1) & 0xFFFF
        bc -= 1

    # Zero $6104-$6504 (1024 bytes) - the region between the original loader
    # area and the new game code
    for addr in range(0x6104, 0x6504):
        mem[addr - 0x4000] = 0

    with open(after_path, 'wb') as f:
        f.write(mem)
    print(f'Post-LDDR memory image: {len(mem)} bytes -> {after_path}')

    # Verify entry point
    print(f'\nGame entry at $6504:')
    entry = bytes(mem[0x6504 - 0x4000:0x6504 - 0x4000 + 16])
    print('  ' + ' '.join(f'{b:02X}' for b in entry))


if __name__ == '__main__':
    build(LOADER_DECRYPTED, RAW_BLOCK_07, RAW_BLOCK_09,
          MEM_BEFORE_LDDR, MEM_AFTER_LDDR)