"""Disassemble the I/O routines inside the built ROM."""
from z80dis import z80

ROM = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom'

with open(ROM, 'rb') as f:
    rom = f.read()


def disasm(start, end):
    pos = start
    out = []
    while pos < end:
        off = pos - 0x4000
        chunk = rom[off:off + 4]
        try:
            d = z80.decode(chunk, pos)
            out.append(f'${pos:04X}: {z80.decoded2str(d):<30s}  ; {chunk[:d.len].hex()}')
            pos += d.len
        except Exception as e:
            out.append(f'${pos:04X}: ??? {e}  ; {rom[off]:02X}')
            pos += 1
    return '\n'.join(out)


print('=== I/O routines $4040-$4110 ===')
print(disasm(0x4040, 0x4110))
print()
print('=== init code $4200-$43A0 ===')
print(disasm(0x4200, 0x43A0))