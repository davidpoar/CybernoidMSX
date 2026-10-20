#!/usr/bin/env python3
"""Busca en el motor de la ROM las instrucciones que tocan un rango de
la RAM (para encontrar quien pisa una variable)."""
import sys
from pathlib import Path

rom = Path(r'C:\Dev\cybernoidMSX\msx\build\cybernoid.rom').read_bytes()[:0x4000]

ini = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xC0B0
fin = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0xC0B7

print(f'las instrucciones que tocan ${ini:04X}-${fin:04X}:')
for i in range(len(rom) - 3):
    op = rom[i]
    if op in (0x32, 0x3A):        # LD (nn),A / LD A,(nn)
        addr = rom[i + 1] | (rom[i + 2] << 8)
        if ini <= addr <= fin:
            print(f'  ${0x4000 + i:04X}: {"LD (nn),A" if op == 0x32 else "LD A,(nn)"}'
                  f'  ${addr:04X}')
    if op == 0x22 and (i + 3 < len(rom)):   # LD (nn),HL
        addr = rom[i + 1] | (rom[i + 2] << 8)
        if ini <= addr <= fin:
            print(f'  ${0x4000 + i:04X}: LD (nn),HL  ${addr:04X}')
    if op == 0x2A and (i + 3 < len(rom)):   # LD HL,(nn)
        addr = rom[i + 1] | (rom[i + 2] << 8)
        if ini <= addr <= fin:
            print(f'  ${0x4000 + i:04X}: LD HL,(nn)  ${addr:04X}')
    if op == 0x77:                  # LD (HL),A
        print(f'  ${0x4000 + i:04X}: LD (HL),A  (depende de HL)')
