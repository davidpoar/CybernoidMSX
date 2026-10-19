#!/usr/bin/env python3
"""Step 2: Identify and disassemble the I/O routines of Cybernoid.

This script generates a comprehensive report of:
  - Keyboard reading routines (port $FE reads)
  - Sound/beeper routines (port $FE writes with bit 4)
  - Video routines (writes to screen memory $4000-$5AFF)
  - All CALL targets called from the entry area
  - All jump tables or RST usage
"""
from z80dis import z80
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import MEM_AFTER_LDDR, SPECTRUM_DISASM_DIR


def disasm_at(mem, addr, length, max_lines=200):
    """Disassemble a region; stop early if max_lines reached."""
    out = []
    pos = addr
    end = addr + length
    count = 0
    while pos < end and count < max_lines:
        off = pos - 0x4000
        if off < 0 or off >= len(mem):
            out.append(f'${pos:04X}: [out of bounds]')
            break
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            out.append(f'${pos:04X}: {asm:<32s}  ; {chunk[:decoded.len].hex()}')
            pos += decoded.len
            count += 1
        except:
            out.append(f'${pos:04X}: ???  ; {mem[off]:02X}')
            pos += 1
    return '\n'.join(out)


def main():
    with open(MEM_AFTER_LDDR, 'rb') as f:
        mem = f.read()

    # === Build a complete listing of the game ===
    # We'll generate a master map and several detailed analyses

    out_path = Path(SPECTRUM_DISASM_DIR) / 'cybernoid_io_map.txt'

    lines = []
    lines.append('=' * 70)
    lines.append('CYBERNOID I/O MAP (post-LDDR memory layout)')
    lines.append('=' * 70)

    # === 1. Keyboard routines ===
    lines.append('\n' + '=' * 70)
    lines.append('1. KEYBOARD READING ROUTINES')
    lines.append('=' * 70)
    lines.append('''
Spectrum keyboard is read via IN A, ($FE) with different rows.
The high byte of the port determines which row is selected:

  Row 0 ($FE) : CAPS SHIFT, Z, X, C, V
  Row 1 ($FD) : A, S, D, F, G
  Row 2 ($FB) : Q, W, E, R, T
  Row 3 ($F7) : 1, 2, 3, 4, 5
  Row 4 ($EF) : 0, 9, 8, 7, 6
  Row 5 ($DF) : P, O, I, U, Y
  Row 6 ($BF) : ENTER, L, K, J, H
  Row 7 ($7F) : SPACE, SYM SHIFT, M, N, B
''')

    # Find keyboard routines (port $FE reads)
    kbd_routines = set()
    pos = 0x4000
    while pos < 0xFFFF:
        off = pos - 0x4000
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            if 'IN A,(0x00fe)' in asm or 'IN A,(0xfe)' in asm:
                # Look backward to find start of routine (some LD A, nn just before)
                kbd_routines.add(pos - 2)  # account for LD A, nn prefix
            pos += decoded.len
        except:
            pos += 1
    # Also include the address that does the IN itself
    pos = 0x4000
    while pos < 0xFFFF:
        off = pos - 0x4000
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            if 'IN A,(0x00fe)' in asm or 'IN A,(0xfe)' in asm:
                kbd_routines.add(pos)
            pos += decoded.len
        except:
            pos += 1

    # Disassemble each keyboard routine
    lines.append('--- Keyboard routines in detail ---')
    for addr in sorted(kbd_routines):
        lines.append(f'\n--- Near ${addr:04X} ---')
        lines.append(disasm_at(mem, addr, 0x30, max_lines=20))

    # === 2. Sound routines ===
    lines.append('\n\n' + '=' * 70)
    lines.append('2. SOUND / BEEPER ROUTINES')
    lines.append('=' * 70)
    lines.append('''
Cybernoid likely uses the Spectrum beeper (bit 4 of port $FE) for sound.
Beeper routines set/clear bit 4 alternately with timing loops.
''')

    # Sound init at $7BFC (called early in main loop)
    lines.append('--- $7BFC: Sound init ---')
    lines.append(disasm_at(mem, 0x7BFC, 0x50, max_lines=40))

    # Sound driver called from IM 2 handler at $85BA
    lines.append('\n--- $85BA: Sound driver (called from IM 2 at $70E5) ---')
    lines.append(disasm_at(mem, 0x85BA, 0x80, max_lines=60))

    # IM 2 handler (already analyzed but show again)
    lines.append('\n--- $70D3: IM 2 handler (50 Hz interrupt, drives sound) ---')
    lines.append(disasm_at(mem, 0x70D3, 0x50, max_lines=40))

    # === 3. Video routines ===
    lines.append('\n\n' + '=' * 70)
    lines.append('3. VIDEO / SCREEN MEMORY ROUTINES')
    lines.append('=' * 70)
    lines.append('''
Spectrum video memory layout:
  $4000-$5AFF: screen pixels (6144 bytes, 256x192, 1 bit per pixel)
  $5800-$5AFF: attributes (768 bytes, 32x24, 8x8 cells, color)

Screen pixel byte layout: 8 pixels per byte, MSB=leftmost
''')

    # Find routines that reference screen memory
    lines.append('--- Screen clears ---')
    # Screen clear happens at entry. After LDDR, the entry code lives at $6504.
    # Note: post-LDDR $FE3A is overwritten by game data (loader code is gone),
    # so we use the PRE-LDDR memory for the loader analysis.
    lines.append('Note: post-LDDR $FE3A is overwritten by game data; see loader_disasm.txt for $FE3A.')

    lines.append('\n$650B: Clear $5B00-$6503 (LDIR $A03 bytes of 0) - BASIC area')
    lines.append(disasm_at(mem, 0x650B, 0x0C, max_lines=5))

    # Find LDIR / LD with screen area
    screen_refs = []
    pos = 0x4000
    while pos < 0xFFFF:
        off = pos - 0x4000
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            # Look for LD HL, 4608 ($1200) etc. - or LD HL, 5800 ($16A8)
            if 'LD HL,0x4000' in asm or 'LD HL,0x5800' in asm or 'LD DE,0x4000' in asm or 'LD DE,0x5800' in asm:
                screen_refs.append((pos, asm))
            pos += decoded.len
        except:
            pos += 1
    lines.append('\n--- References to $4000/$5800 (screen/attribute base) ---')
    for addr, asm in screen_refs[:20]:
        lines.append(f'  ${addr:04X}: {asm}')

    # === 4. Out ($FE) for border/beeper ===
    lines.append('\n\n' + '=' * 70)
    lines.append('4. OUT ($FE) USAGE')
    lines.append('=' * 70)
    out_fe = []
    pos = 0x4000
    while pos < 0xFFFF:
        off = pos - 0x4000
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            if 'OUT (0x00fe)' in asm or 'OUT (0xfe)' in asm:
                out_fe.append((pos, asm))
            pos += decoded.len
        except:
            pos += 1
    lines.append(f'\nFound {len(out_fe)} OUT ($FE) instructions')
    for addr, asm in out_fe:
        # Show a few instructions of context
        ctx = disasm_at(mem, max(0x4000, addr - 4), 8, max_lines=4)
        lines.append(f'  ${addr:04X}: {asm}')
        if len(out_fe) <= 5:
            lines.append('  context:')
            lines.append(ctx)

    # === 5. CALL targets from entry area ===
    lines.append('\n\n' + '=' * 70)
    lines.append('5. INITIALIZATION CALL CHAIN (from entry $6504)')
    lines.append('=' * 70)

    init_calls = []
    pos = 0x6504
    end = 0x6600
    while pos < end:
        off = pos - 0x4000
        chunk = mem[off:off+4]
        try:
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            if 'CALL' in asm or 'JP' in asm or 'JR' in asm:
                init_calls.append((pos, asm))
            pos += decoded.len
        except:
            pos += 1
    lines.append('\nCalls/Jumps in $6504-$6600 (init/main loop area):')
    for addr, asm in init_calls:
        lines.append(f'  ${addr:04X}: {asm}')

    # Disassemble main loop area
    lines.append('\n--- Main loop area $6560-$65A0 ---')
    lines.append(disasm_at(mem, 0x6560, 0x50, max_lines=40))

    with open(out_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Saved I/O map to {out_path}')


if __name__ == '__main__':
    main()