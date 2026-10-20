#!/usr/bin/env python3
"""Regenerate the split reference documentation.

The source documents live in docs/reference/_source/ so that the
project is self contained and does not depend on any other
repository.

  _source/red_book.md        the MSX Red Book
  _source/spectrum_rom.txt   the Spectrum ROM disassembly
  _source/spectrum_ula.txt   the Spectrum ULA book
  _source/z80_programming.txt  Programming the Z80
  _source/z80_opcodes.md     the Z80 opcode guide
"""
import shutil
from pathlib import Path

PROJECT_DOCS = Path(__file__).parent
SOURCE = PROJECT_DOCS / 'reference' / '_source'
REF = PROJECT_DOCS / 'reference'

MSX_CHAPTERS = {
    'chapter_1': 'PPI (8255) - Programmable Peripheral Interface',
    'chapter_2': 'VDP (TMS9918) - Video Display Processor',
    'chapter_3': 'PSG (AY-3-8910) - Programmable Sound Generator',
    'chapter_4': 'ROM BIOS - Standard Routines',
    'chapter_5': 'ROM BASIC Interpreter',
    'chapter_6': 'Memory Map and Workspace Area',
    'chapter_7': 'Machine Code Programs - Examples',
}

SPECTRUM_SECTIONS = [
    'THE RESTART ROUTINES and THE TABLES',
    'THE KEYBOARD ROUTINES',
    'THE LOUDSPEAKER ROUTINES',
    'THE CASSETTE HANDLING ROUTINES',
    'THE EXECUTIVE ROUTINES',
    'BASIC LINE AND COMMAND INTERPRETATION',
    'EXPRESSION EVALUATION',
    'THE ARITHMETIC ROUTINES',
    'THE FLOATING-POINT CALCULATOR',
    'APPENDIX',
]

MAX_LINES = 6000


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def split_msx():
    print('MSX Red Book')
    out = REF / 'msx'
    for f in out.glob('*.md'):
        if f.name not in ('ascii16_mapper_reference.md',):
            f.unlink()
    text = (SOURCE / 'red_book.md').read_text(encoding='utf-8', errors='replace')
    lines = text.split('\n')

    bounds = []
    for i, line in enumerate(lines):
        if '<a name="chapter_' in line:
            bounds.append((i, line.split('"')[1]))
    bounds.append((len(lines), None))

    write(out / '00_introduction.md',
          '# MSX Red Book - Introduction\n\n' + '\n'.join(lines[:bounds[0][0]]))

    for k in range(len(bounds) - 1):
        start, name = bounds[k]
        end = bounds[k + 1][0]
        title = MSX_CHAPTERS.get(name, name)
        write(out / f'{name}.md',
              f'# MSX Red Book - {title}\n\n'
              f'Original chapter: `{name}`\n\n---\n\n' +
              '\n'.join(lines[start:end]))
        print(f'  {name}.md  ({end - start} lines)')


def split_spectrum():
    print('Spectrum ROM disassembly')
    out = REF / 'spectrum'
    if out.exists():
        shutil.rmtree(out)
    text = (SOURCE / 'spectrum_rom.txt').read_text(
        encoding='utf-8', errors='replace')
    lines = text.split('\n')

    found = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s in SPECTRUM_SECTIONS:
            prev_blank = i == 0 or not lines[i - 1].strip()
            next_blank = i + 1 >= len(lines) or not lines[i + 1].strip()
            if prev_blank and next_blank:
                found.append((s, i))
    seen = set()
    unique = []
    for name, i in found:
        key = name.replace(' and THE ', ' AND ')
        if key not in seen:
            seen.add(key)
            unique.append((name, i))
    unique.append((None, len(lines)))

    write(out / '00_preface_intro.md',
          '# Spectrum ROM Disassembly - Preface and Introduction\n\n---\n\n' +
          '\n'.join(lines[:unique[0][1]]))

    for k in range(len(unique) - 1):
        name, start = unique[k]
        end = unique[k + 1][1]
        chunk = lines[start:end]
        slug = name.lower().replace('the ', '').replace(' ', '_')
        slug = ''.join(c for c in slug if c.isalnum() or c == '_')
        if len(chunk) > MAX_LINES:
            n = (len(chunk) + MAX_LINES - 1) // MAX_LINES
            for p in range(n):
                part = chunk[p * MAX_LINES:(p + 1) * MAX_LINES]
                write(out / f'{slug}_part{p+1}of{n}.txt',
                      f'# Spectrum ROM Disassembly - {name.title()}\n'
                      f'Part {p+1}/{n}\n\n---\n\n' + '\n'.join(part))
            print(f'  {slug}_part1of{n}.txt ... ({len(chunk)} lines)')
        else:
            write(out / f'{slug}.txt',
                  f'# Spectrum ROM Disassembly - {name.title()}\n\n---\n\n' +
                  '\n'.join(chunk))
            print(f'  {slug}.txt  ({len(chunk)} lines)')


def split_ula():
    print('Spectrum ULA book')
    out = REF / 'ula'
    if out.exists():
        shutil.rmtree(out)
    text = (SOURCE / 'spectrum_ula.txt').read_text(
        encoding='utf-8', errors='replace')
    lines = text.split('\n')
    write(out / '00_spectrum_ula_full.txt', text)
    half = len(lines) // 2
    write(out / '01_spectrum_ula_part1.txt',
          '# Spectrum ULA - Part 1\n\n---\n\n' + '\n'.join(lines[:half]))
    write(out / '02_spectrum_ula_part2.txt',
          '# Spectrum ULA - Part 2\n\n---\n\n' + '\n'.join(lines[half:]))
    print(f'  full + 2 halves ({len(lines)} lines)')


def split_z80():
    print('Z80 documentation')
    out = REF / 'z80'
    if out.exists():
        shutil.rmtree(out)
    write(out / '00_z80_opcodes_guide.md',
          (SOURCE / 'z80_opcodes.md').read_text(
              encoding='utf-8', errors='replace'))
    text = (SOURCE / 'z80_programming.txt').read_text(
        encoding='utf-8', errors='replace')
    lines = text.split('\n')
    n = 4
    size = len(lines) // n
    for i in range(n):
        part = lines[i * size:(i + 1) * size] if i < n - 1 else lines[i * size:]
        write(out / f'{i+1:02d}_programming_z80_part{i+1}.txt',
              f'# Programming the Z80 - Part {i+1}/{n}\n\n---\n\n' + '\n'.join(part))
    print(f'  opcodes guide + 4 parts ({len(lines)} lines)')


def main():
    missing = [p for p in ('red_book.md', 'spectrum_rom.txt', 'spectrum_ula.txt',
                            'z80_programming.txt', 'z80_opcodes.md')
               if not (SOURCE / p).exists()]
    if missing:
        print(f'ERROR: missing source files in {SOURCE}: {missing}')
        sys.exit(1)

    split_msx()
    split_spectrum()
    split_ula()
    split_z80()
    print('\nDone')


if __name__ == '__main__':
    import sys
    main()
