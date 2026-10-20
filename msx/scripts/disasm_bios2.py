"""Disassemble more of the MSX BIOS to understand ENASLT."""
import sys
sys.path.insert(0, r'C:\Dev\cybernoidMSX\tools')
from z80dis import z80

with open(r'C:\Dev\cybernoidMSX\msx\build\msx.rom', 'rb') as f:
    b = f.read()

for lo, hi in [(0x02A3, 0x02F0), (0x026B, 0x027E)]:
    print(f'--- ${lo:04X}-${hi:04X} ---')
    pos = lo
    while pos < hi:
        c = b[pos:pos + 4]
        try:
            d = z80.decode(c, pos)
            raw = ' '.join(f'{x:02X}' for x in c[:d.len])
            print(f'  ${pos:04X}: {z80.decoded2str(d):<26s} ; {raw}')
            pos += d.len
        except Exception:
            print(f'  ${pos:04X}: ???')
            pos += 1
    print()