#!/usr/bin/env python3
"""Show bytes at key addresses to understand Cybernoid structure."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import MEM_AFTER_LDDR


def show(mem, addr, length, label=''):
    print(f'\n=== {label}: 0x{addr:04X} ===')
    for i in range(length):
        b = mem[addr + i - 0x4000]
        c = chr(b) if 32 <= b < 127 else '.'
        print(f'  +{i:02X}: 0x{b:02X} ({c})')


def main():
    with open(MEM_AFTER_LDDR, 'rb') as f:
        mem = f.read()

    show(mem, 0x6649, 40, 'Keyboard scan lookup table at 0x6649')
    show(mem, 0x7B49, 0x40, 'Keyboard state at 0x7B49')
    show(mem, 0x7BAA, 0x40, 'Sound channel data at 0x7BAA')
    show(mem, 0x7BBA, 0x40, 'Sound data at 0x7BBA')
    show(mem, 0x859A, 0x40, 'Sound data at 0x859A')
    show(mem, 0x8710, 0x40, 'Sound envelope data at 0x8710')


if __name__ == '__main__':
    main()