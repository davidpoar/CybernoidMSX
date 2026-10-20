"""Disassemble the MSX BIOS ENASLT routine."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'tools'))
from z80dis import z80

BIOS = Path(r'C:\Dev\cybernoidMSX\msx\build\msx.rom')
with open(BIOS, 'rb') as f:
    bios = f.read()


def dis(lo, hi):
    pos = lo
    while pos < hi:
        chunk = bios[pos:pos + 4]
        try:
            d = z80.decode(chunk, pos)
            print(f'  ${pos:04X}: {z80.decoded2str(d):<28s} ; {chunk[:d.len].hex(" ")}')
            pos += d.len
        except Exception as e:
            print(f'  ${pos:04X}: ??? {e}')
            pos += 1


print('ENASLT ($0024 entry, impl at $025E):')
dis(0x025E, 0x02A3)
print()
print('Mask builder $027E:')
dis(0x027E, 0x02D0)
print()
print('RSLREG ($0138 entry, impl at $144C):')
dis(0x144C, 0x1460)