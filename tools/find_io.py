#!/usr/bin/env python3
"""Scan the Cybernoid memory image for I/O instructions and report usage by port."""
from z80dis import z80
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import MEM_AFTER_LDDR, DISASM_IO_MAP


def main():
    with open(MEM_AFTER_LDDR, 'rb') as f:
        mem = f.read()

    io_instrs = []
    pos = 0x4000
    end = 0xFFFF
    while pos <= end:
        offset = pos - 0x4000
        chunk = mem[offset:offset+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            if 'OUT' in asm or 'IN A' in asm:
                io_instrs.append((pos, asm, chunk[:decoded.len].hex()))
            pos += decoded.len
        except:
            pos += 1

    by_port = defaultdict(list)
    for addr, asm, raw in io_instrs:
        if '(0x' in asm:
            try:
                port_str = asm.split('(0x')[1].split(')')[0]
                port = int(port_str, 16)
                by_port[port].append((addr, asm, raw))
            except (ValueError, IndexError):
                pass

    lines = []
    lines.append('=== I/O INSTRUCTIONS BY PORT (post-LDDR memory) ===\n')
    for port in sorted(by_port.keys()):
        lines.append(f'\nPort ${port:02X} ({port}): {len(by_port[port])} instructions')
        for addr, asm, raw in by_port[port][:8]:
            lines.append(f'  ${addr:04X}: {asm}')
        if len(by_port[port]) > 8:
            lines.append(f'  ... and {len(by_port[port])-8} more')

    out_path = DISASM_IO_MAP
    with open(out_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Total I/O instructions: {len(io_instrs)}')
    print(f'Saved to {out_path}')


if __name__ == '__main__':
    main()