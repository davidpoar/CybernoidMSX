#!/usr/bin/env python3
"""Muestra las direcciones de los simbolos del motor ensamblado."""
import sys
from pathlib import Path

SYM = Path(r'C:\Dev\cybernoidMSX\msx\build\rom_engine.sym')
Nombres = ['INIT', 'MAINLOOP', 'ISR', 'SETBANK_B', 'GETBANK', 'BANK_SELFTEST',
           'JOB_START', 'JOB_NEXT', 'VDP_INIT', 'VDP_SETREG', 'PSG_INIT',
           'GAME_FRAME', 'UPDATE_SPRITES', 'SPRITES_TO_VRAM', 'SET_GAME_SCREEN',
           'MOVE_SHIP', 'MOVE_BULLETS', 'MOVE_ENEMIES', 'COLLISIONS',
           'READ_KEY', 'START_GAME', 'UPDATE_HUD', 'SOUND_SHOT',
           'SOUND_EXPLODE', 'SOUND_UPDATE']

simbolos = {}
for linea in SYM.read_text().splitlines():
    p = linea.split()
    if len(p) >= 3:
        try:
            simbolos[p[0]] = int(p[2].rstrip('H'), 16)
        except ValueError:
            pass

for n in Nombres:
    if n in simbolos:
        print(f'  {n:18s} = ${simbolos[n]:04X}')
print(f'\n  {len(simbolos)} simbolos en total')
