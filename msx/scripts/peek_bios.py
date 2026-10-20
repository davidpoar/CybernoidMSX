"""Inspect the real MSX BIOS at the entries the ROM uses."""
BIOS = r'C:\Dev\cybernoidMSX\msx\build\msx.rom'

with open(BIOS, 'rb') as f:
    bios = f.read()


def show(addr, n=16, label=''):
    print(f'{label:<14} ${addr:04X}: ' +
          ' '.join(f'{bios[addr + i]:02X}' for i in range(n)))


show(0x0024, 12, 'ENASLT entry')
show(0x0138, 12, 'RSLREG entry')
show(0x025E, 12, 'ENASLT impl')
show(0x144C, 12, 'RSLREG impl')
show(0xFCC1, 8, 'EXPTBL')
show(0xFCC5, 8, 'SLTTBL')
print()
print('ENASLT entry  $0024: ' +
      ' '.join(f'{bios[0x0024 + i]:02X}' for i in range(6)))
# C3 xx xx = JP nn
if bios[0x0024] == 0xC3:
    tgt = bios[0x0025] | (bios[0x0026] << 8)
    print(f'  -> JP ${tgt:04X}')
if bios[0x0138] == 0xC3:
    tgt = bios[0x0139] | (bios[0x013A] << 8)
    print(f'  -> JP ${tgt:04X}')