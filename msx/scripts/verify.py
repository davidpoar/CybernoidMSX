"""Verify the built Cybernoid MSX ROM and BIN files."""
import struct

ROM = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom'
BIN = r'C:\Dev\cybernoidMSX\msx\build\cybernoid.bin'

with open(ROM, 'rb') as f:
    rom = f.read()
with open(BIN, 'rb') as f:
    binf = f.read()

print('=' * 62)
print('ROM VERIFICATION')
print('=' * 62)
print(f'Size: {len(rom)} bytes (16K cartridge)')
print(f'Header: {rom[0]:c}{rom[1]:c}  INIT=${rom[2] | (rom[3] << 8):04X}  '
      f'STAT=${rom[4] | (rom[5] << 8):04X}  DEV=${rom[6] | (rom[7] << 8):04X}  '
      f'TEXT=${rom[8] | (rom[9] << 8):04X}')
print()
print('Stub at $4010:')
print(f'  {rom[0x10:0x2D].hex()}')
print()
print('Init code at $4110 (first 32 bytes):')
print(f'  {rom[0x110:0x130].hex()}')
print()
print('I/O routines at $4200 (first 32 bytes):')
print(f'  {rom[0x200:0x220].hex()}')
print()

# Verify stub instructions
print('Stub decoded:')
stub = rom[0x10:0x2D]
i = 0
while i < len(stub):
    b = stub[i]
    addr = 0x4000 + 0x10 + i
    if b == 0xF3:
        print(f'  ${addr:04X}: DI'); i += 1
    elif b == 0x31:
        print(f'  ${addr:04X}: LD SP,${stub[i+1] | (stub[i+2] << 8):04X}'); i += 3
    elif b == 0x21:
        print(f'  ${addr:04X}: LD HL,${stub[i+1] | (stub[i+2] << 8):04X}'); i += 3
    elif b == 0x11:
        print(f'  ${addr:04X}: LD DE,${stub[i+1] | (stub[i+2] << 8):04X}'); i += 3
    elif b == 0x01:
        print(f'  ${addr:04X}: LD BC,${stub[i+1] | (stub[i+2] << 8):04X}'); i += 3
    elif b == 0xED and stub[i+1] == 0xB0:
        print(f'  ${addr:04X}: LDIR'); i += 2
    elif b == 0xC3:
        print(f'  ${addr:04X}: JP ${stub[i+1] | (stub[i+2] << 8):04X}'); i += 3
    else:
        print(f'  ${addr:04X}: {b:02X}'); i += 1

print()
print('=' * 62)
print('BIN VERIFICATION')
print('=' * 62)
print(f'Size: {len(binf)} bytes')
print(f'Header: {binf[:7].hex()}')
print(f'  signature: ${binf[0]:02X} (FE = MSX BIN)')
print(f'  load addr: ${struct.unpack_from("<H", binf, 1)[0]:04X}')
print(f'  end addr:  ${struct.unpack_from("<H", binf, 3)[0]:04X}')
print(f'  exec addr: ${struct.unpack_from("<H", binf, 5)[0]:04X}')
game = binf[7:-1]
print(f'  game data: {len(game)} bytes')
print(f'  checksum: ${binf[-1]:02X}')
print()
print('Patched call sites:')
for spec, label in [(0x65ED, 'IN A,($FE) #1'), (0x65F4, 'IN A,($FE) #2'),
                    (0x660D, 'IN A,($FE) #3'), (0x7B4C, 'IN A,($FE) #4'),
                    (0x651F, 'OUT ($FE),A')]:
    off = spec - 0x6504
    tgt = game[off+1] | (game[off+2] << 8)
    print(f'  Spectrum ${spec:04X} ({label:14s}) -> CALL ${tgt:04X}')
im2 = IM2 = 0x70B4 - 0x6504
print(f'  Spectrum $70B4 (IM 2 init)     -> {game[im2:im2+6].hex()} (NOPs)')
print()
print('Game entry point (MSX $0000):')
print(f'  {game[:16].hex()}')
print(f'  = DI; LD SP,$0000; CALL ${game[5] | (game[6] << 8):04X}; ...')