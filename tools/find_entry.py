#!/usr/bin/env python3
"""Comprueba donde esta el juego en cada imagen de memoria."""
from pathlib import Path

base = Path(r'C:\Dev\cybernoidMSX\spectrum')
for name in ('cybernoid_before_lddr.bin', 'cybernoid_after_lddr.bin',
             'cybernoid_block9_main.bin'):
    p = base / name
    d = p.read_bytes()
    print(f'\n=== {name} ({len(d)} bytes)')
    # la entrada del juego es DI (F3), LD SP,nn (31 nn nn)
    for i in range(len(d) - 4):
        if d[i] == 0xF3 and d[i + 1] == 0x31:
            addr = i
            print(f'  F3 31 en el offset ${addr:04X} -> {d[addr:addr+12].hex(" ")}')
            if i < 0x100:
                continue
    # busca la secuencia DI / LD SP,0 / CALL $70B4
    objetivo = bytes.fromhex('f3310000cdb470')
    pos = d.find(objetivo)
    print(f'  la secuencia de entrada esta en el offset '
          f'${pos:04X}' if pos >= 0 else '  no encontrada')
