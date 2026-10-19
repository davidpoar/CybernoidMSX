#!/usr/bin/env python3
"""Find all keyboard reading routines and analyze which keys they check."""
from z80dis import z80
from collections import defaultdict
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import MEM_AFTER_LDDR, SPECTRUM_DISASM_DIR


# Spectrum keyboard matrix:
# Port high byte -> keys (bits 0-4)
KEYBOARD_MAP = {
    0xFE: ('CAPS_SHIFT', 'Z', 'X', 'C', 'V'),          # Row 0
    0xFD: ('A', 'S', 'D', 'F', 'G'),                    # Row 1
    0xFB: ('Q', 'W', 'E', 'R', 'T'),                    # Row 2
    0xF7: ('1', '2', '3', '4', '5'),                    # Row 3
    0xEF: ('0', '9', '8', '7', '6'),                    # Row 4
    0xDF: ('P', 'O', 'I', 'U', 'Y'),                    # Row 5
    0xBF: ('ENTER', 'L', 'K', 'J', 'H'),                # Row 6
    0x7F: ('SPACE', 'SYM_SHIFT', 'M', 'N', 'B'),        # Row 7
}


def main():
    with open(MEM_AFTER_LDDR, 'rb') as f:
        mem = f.read()

    # Find all "LD A, nn; IN A, ($FE)" sequences
    sequences = []
    pos = 0x4000
    while pos < 0xFFFF:
        off = pos - 0x4000
        try:
            chunk = mem[off:off+4]
            decoded = z80.decode(chunk, pos)
            asm = z80.decoded2str(decoded)
            size = decoded.len
            if asm.startswith('LD A,'):
                # Check if next instruction is IN A, ($FE)
                next_off = off + size
                if next_off < len(mem) - 4:
                    next_chunk = mem[next_off:next_off+4]
                    next_decoded = z80.decode(next_chunk, pos + size)
                    next_asm = z80.decoded2str(next_decoded)
                    if 'IN A,(0x00fe)' in next_asm or 'IN A,(0xfe)' in next_asm:
                        # Extract port high byte from LD A, nn
                        try:
                            port_byte = int(asm.split('0x')[1], 16)
                            sequences.append((pos, port_byte, asm, next_asm))
                        except (IndexError, ValueError):
                            pass
            pos += size
        except:
            pos += 1

    # Find routines that read keyboard (group by routine)
    print(f'Found {len(sequences)} LD A,nn + IN A,($FE) sequences:')
    for addr, port, ld, ina in sequences:
        row = KEYBOARD_MAP.get(port, ('?',)*5)
        keys = ', '.join(row[:5])
        print(f'  ${addr:04X}: {ld} ; {ina}  (port high byte ${port:02X} = {keys})')

    # Save to file
    out_path = Path(SPECTRUM_DISASM_DIR) / 'cybernoid_keyboard.txt'
    lines = []
    lines.append('=' * 70)
    lines.append('CYBERNOID KEYBOARD MATRIX USAGE')
    lines.append('=' * 70)
    lines.append('\nSpectrum keyboard is read via IN A, ($FE) with different rows.')
    lines.append('The high byte of the port determines which row is selected.\n')
    for port_byte, keys in sorted(KEYBOARD_MAP.items(), reverse=True):
        lines.append(f'  Row ${port_byte:02X}: {", ".join(keys)}')
    lines.append('')
    lines.append(f'\nFound {len(sequences)} LD A,nn + IN A,($FE) sequences:')
    for addr, port, ld, ina in sequences:
        row = KEYBOARD_MAP.get(port, ('?',)*5)
        keys = ', '.join(row[:5])
        lines.append(f'  ${addr:04X}: {ld} ; {ina}  (row ${port:02X} = {keys})')

    # Also look at routine around $65EB and $660B (entry/main loop area)
    lines.append('\n\n' + '=' * 70)
    lines.append('DETAIL: KEYBOARD ROUTINES (around entry/main loop)')
    lines.append('=' * 70)
    lines.append('\n--- $65E0-67A0 (input handling) ---')

    out_fout = open(out_path, 'w')
    out_fout.write('\n'.join(lines) + '\n')
    out_fout.close()

    print(f'\nSaved to {out_path}')


if __name__ == '__main__':
    main()