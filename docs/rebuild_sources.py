#!/usr/bin/env python3
"""Rebuild the reference source documents from the split copies.

The originals are not available any more, but the split files still
hold the whole text (only a small header was prepended to each one).
This puts them back together in docs/reference/_source/ so that
split_docs.py has something to work from.
"""
from pathlib import Path

REF = Path(__file__).parent / 'reference'
SRC = REF / '_source'
SRC.mkdir(parents=True, exist_ok=True)


def strip_header(lines, marker='---'):
    """Drop the header the splitter prepended."""
    # The header is: title, optional 'Part n/m', blank, '---', blank
    if lines and lines[0].startswith('#'):
        for i, l in enumerate(lines[:8]):
            if l.strip() == marker:
                return lines[i + 2:]
    return lines


def join(folder, pattern, out_name, keep_headers=False):
    files = sorted((REF / folder).glob(pattern))
    if not files:
        print(f'  no files for {folder}/{pattern}')
        return
    out = []
    for f in files:
        lines = f.read_text(encoding='utf-8', errors='replace').split('\n')
        if not keep_headers:
            lines = strip_header(lines)
        out.append('\n'.join(lines))
    text = '\n'.join(out)
    path = SRC / out_name
    path.write_text(text, encoding='utf-8')
    print(f'  {out_name}: {len(text)} bytes')


print('Rebuilding the reference sources:')
join('spectrum', '*.txt', 'spectrum_rom.txt')
join('ula', '0*.txt', 'spectrum_ula.txt')

# The ULA full file is the whole document, use it directly
full = REF / 'ula' / '00_spectrum_ula_full.txt'
if full.exists():
    (SRC / 'spectrum_ula.txt').write_text(
        full.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    print(f'  spectrum_ula.txt: {(SRC / "spectrum_ula.txt").stat().st_size} bytes')

# Z80: the four parts
parts = sorted((REF / 'z80').glob('0*_programming_z80_part*.txt'))
if parts:
    out = []
    for f in parts:
        out.append('\n'.join(strip_header(
            f.read_text(encoding='utf-8', errors='replace').split('\n'))))
    (SRC / 'z80_programming.txt').write_text('\n'.join(out), encoding='utf-8')
    print(f'  z80_programming.txt: {(SRC / "z80_programming.txt").stat().st_size} bytes')

# Z80 opcodes guide
guide = REF / 'z80' / '00_z80_opcodes_guide.md'
if guide.exists():
    (SRC / 'z80_opcodes.md').write_text(
        guide.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    print(f'  z80_opcodes.md: {(SRC / "z80_opcodes.md").stat().st_size} bytes')

# The MSX Red Book was downloaded already
rb = REF / 'msx' / '_source_red_book.md'
if rb.exists():
    (SRC / 'red_book.md').write_text(
        rb.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    print(f'  red_book.md: {(SRC / "red_book.md").stat().st_size} bytes')
