"""Dump the structure of the built ROM so it can be checked by hand."""
import struct
from pathlib import Path

ROM = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom')
with open(ROM, 'rb') as f:
    rom = f.read()

print(f'File: {ROM}')
print(f'Size: {len(rom)} bytes ({len(rom)//1024} KB)\n')

print('HEADER at $4000 (file offset $0000):')
sig = rom[0:2].decode('latin-1')
init = struct.unpack_from('<H', rom, 2)[0]
stmt = struct.unpack_from('<H', rom, 4)[0]
dev = struct.unpack_from('<H', rom, 6)[0]
text = struct.unpack_from('<H', rom, 8)[0]
print(f'  $4000  DB "{sig}"')
print(f'  $4002  DW ${init:04X}   (INIT)')
print(f'  $4004  DW ${stmt:04X}   (STATEMENT)')
print(f'  $4006  DW ${dev:04X}   (DEVICE)')
print(f'  $4008  DW ${text:04X}   (TEXT)')
print(f'  $400A  DS 6,0    (reservado)  -> {rom[0x0A:0x10].hex(" ")}')
print()

print('BANKS:')
for bank in range(4):
    off = bank * 0x4000
    idbyte = rom[off]
    nonzero = sum(1 for b in rom[off:off + 0x4000] if b != 0)
    label = {0: 'motor + cabecera', 1: 'assets', 2: 'assets', 3: 'assets'}[bank]
    print(f'  banco {bank}  fichero ${off:04X}-${off + 0x3FFF:04X}  '
          f'-> MSX ${0x4000 + off:04X}  ID=${idbyte:02X}  '
          f'{nonzero:5d} bytes no nulos   ({label})')
print()

print('ENGINE code at $4010 (file offset $0010):')
i = 0x10
while i < 0x10 + 250 and i < len(rom):
    line = ' '.join(f'{rom[i + j]:02X}' for j in range(16))
    print(f'  ${0x4000 + i - 0x10:04X}: {line}')
    i += 16
