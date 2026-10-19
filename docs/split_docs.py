#!/usr/bin/env python3
"""Split large documentation files into smaller, organized pieces and create an index."""
import os
import sys
from pathlib import Path


# === Configuration ===
PROJECT_DOCS = Path(r'C:\Dev\cybernoidMSX\docs')
SOURCE_DOCS = Path(r'C:\Dev\z80emu\docs\systems')

# Subfolders within docs/
MSX_DIR = PROJECT_DOCS / 'msx'
SPECTRUM_DIR = PROJECT_DOCS / 'spectrum'
Z80_DIR = PROJECT_DOCS / 'z80'
ULA_DIR = PROJECT_DOCS / 'ula'

# Files to copy
MSX_FILE = SOURCE_DOCS / 'msx' / 'the_msx_red_book.md'
SPECTRUM_ROM_FILE = SOURCE_DOCS / 'spectrum' / 'CompleteSpectrumROMDisassemblyThe_djvu.txt'
SPECTRUM_ULA_FILE = SOURCE_DOCS / 'spectrum' / 'The-ZX-Spectrum-ULA-How-to-Design-a-Micro-Chris-Smith.txt'
Z80_PROG_FILE = SOURCE_DOCS / 'z80' / 'ProgrammingTheZ80_djvu.txt'
Z80_OPCODES_FILE = SOURCE_DOCS / 'z80' / 'Z80_OPCODES_GUIDE.md'


def split_msx():
    """Split the MSX Red Book by chapters."""
    print(f'\n=== Splitting MSX Red Book ===')
    if not MSX_FILE.exists():
        print(f'ERROR: {MSX_FILE} not found')
        return

    with open(MSX_FILE, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # The MSX Red Book is structured with chapters delimited by
    # <a name="chapter_X"></a> ... <a name="next_chapter"></a>
    # We'll split by chapters.

    lines = content.split('\n')

    # Find chapter boundaries
    chapters = []  # (name, start_line, end_line)
    current_name = None
    current_start = 0

    for i, line in enumerate(lines):
        if '<a name="chapter_' in line:
            if current_name is not None:
                chapters.append((current_name, current_start, i))
            # Extract chapter name
            chapter_match = line.split('"')[1]  # e.g. chapter_1
            current_name = chapter_match
            current_start = i

    # Final chapter
    if current_name is not None:
        chapters.append((current_name, current_start, len(lines)))

    print(f'Found {len(chapters)} chapter boundaries')

    # Write each chapter
    chapter_titles = {
        'chapter_1': 'PPI (8255) - Programmable Peripheral Interface',
        'chapter_2': 'VDP (TMS9918) - Video Display Processor',
        'chapter_3': 'PSG (AY-3-8910) - Programmable Sound Generator',
        'chapter_4': 'ROM BIOS - Standard Routines',
        'chapter_5': 'ROM BASIC Interpreter',
        'chapter_6': 'Memory Map and Workspace Area',
        'chapter_7': 'Machine Code Programs - Examples',
    }

    # Also include introduction
    intro_start = 0
    intro_end = 0
    for i, line in enumerate(lines):
        if '<a name="chapter_1"' in line:
            intro_end = i
            break

    intro_lines = lines[intro_start:intro_end]
    intro_content = '\n'.join(intro_lines)

    with open(MSX_DIR / '00_introduction.md', 'w', encoding='utf-8') as f:
        f.write('# MSX Red Book - Introduction\n\n')
        f.write(intro_content)

    print(f'  -> 00_introduction.md ({len(intro_lines)} lines)')

    for chapter_name, start, end in chapters:
        chapter_lines = lines[start:end]
        title = chapter_titles.get(chapter_name, chapter_name.replace('_', ' ').title())
        filename = chapter_name.replace('_', '') + '.md'

        with open(MSX_DIR / filename, 'w', encoding='utf-8') as f:
            f.write(f'# MSX Red Book - {title}\n\n')
            f.write(f'Original chapter: `{chapter_name}`\n\n')
            f.write('---\n\n')
            f.write('\n'.join(chapter_lines))

        print(f'  -> {filename} ({len(chapter_lines)} lines)')


def split_spectrum_rom():
    """Split the Spectrum ROM Disassembly."""
    print(f'\n=== Splitting Spectrum ROM Disassembly ===')
    if not SPECTRUM_ROM_FILE.exists():
        print(f'ERROR: {SPECTRUM_ROM_FILE} not found')
        return

    with open(SPECTRUM_ROM_FILE, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Just copy - this is a text disassembly with line-by-line content
    # The structure is sequential (no clear chapter markers in MD format).
    # We'll split into reasonable chunks.

    lines = content.split('\n')

    # Try to find major section markers - in this disassembly, sections
    # are delineated by page numbers and titles like "THE KEYBOARD ROUTINES"
    section_starts = []
    for i, line in enumerate(lines):
        stripped = line.strip().upper()
        if stripped in ['THE RESTART ROUTINES AND TABLES',
                        'THE KEYBOARD ROUTINES',
                        'THE LOUDSPEAKER ROUTINES',
                        'THE CASSETTE HANDLING ROUTINES',
                        'THE SCREEN AND PRINTER HANDLING ROUTINES',
                        'THE EXECUTIVE ROUTINES',
                        'BASIC LINE AND COMMAND INTERPRETATION']:
            section_starts.append((stripped, i))

    print(f'Found {len(section_starts)} major sections')

    # Add start sentinel
    section_starts.insert(0, ('PREFACE AND INTRODUCTION', 0))

    sections = []
    for i, (name, start) in enumerate(section_starts):
        end = section_starts[i+1][1] if i+1 < len(section_starts) else len(lines)
        sections.append((name, start, end))

    section_filenames = {
        'PREFACE AND INTRODUCTION': '00_preface_and_intro.txt',
        'THE RESTART ROUTINES AND TABLES': '01_restart_routines.txt',
        'THE KEYBOARD ROUTINES': '02_keyboard_routines.txt',
        'THE LOUDSPEAKER ROUTINES': '03_loudspeaker_routines.txt',
        'THE CASSETTE HANDLING ROUTINES': '04_cassette_routines.txt',
        'THE SCREEN AND PRINTER HANDLING ROUTINES': '05_screen_printer_routines.txt',
        'THE EXECUTIVE ROUTINES': '06_executive_routines.txt',
        'BASIC LINE AND COMMAND INTERPRETATION': '07_basic_interpreter.txt',
    }

    for name, start, end in sections:
        section_lines = lines[start:end]
        filename = section_filenames.get(name, f'section_{start}.txt')
        with open(SPECTRUM_DIR / filename, 'w', encoding='utf-8') as f:
            f.write(f'# Spectrum ROM Disassembly - {name.title()}\n\n')
            f.write('---\n\n')
            f.write('\n'.join(section_lines))

        print(f'  -> {filename} ({len(section_lines)} lines)')


def split_spectrum_ula():
    """Split the Spectrum ULA book by chapters."""
    print(f'\n=== Splitting Spectrum ULA book ===')
    if not SPECTRUM_ULA_FILE.exists():
        print(f'ERROR: {SPECTRUM_ULA_FILE} not found')
        return

    with open(SPECTRUM_ULA_FILE, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Just copy as-is - this is a ULA design book and we mainly need
    # it as reference. We'll split into 2 parts for convenience.
    lines = content.split('\n')

    # Find chapter markers (Chapter X)
    chapter_starts = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Look for "Chapter N" at start of line
        if stripped.startswith('Chapter ') and len(stripped) < 30:
            chapter_starts.append((stripped, i))

    if not chapter_starts:
        # No chapters found, just copy
        with open(ULA_DIR / '00_spectrum_ula_full.txt', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  -> 00_spectrum_ula_full.txt (no chapters found, copied as-is)')
        return

    print(f'Found {len(chapter_starts)} chapters')
    chapter_starts.insert(0, ('PREFACE', 0))

    # Just copy the whole thing to a single file for now (this is a
    # reference document, not heavily used for porting)
    with open(ULA_DIR / '00_spectrum_ula_full.txt', 'w', encoding='utf-8') as f:
        f.write(content)

    # Also split into halves for easier reading
    half = len(lines) // 2
    with open(ULA_DIR / '01_spectrum_ula_part1.txt', 'w', encoding='utf-8') as f:
        f.write(f'# Spectrum ULA Book - Part 1 (Chapters 1-{half // 80})\n\n')
        f.write('---\n\n')
        f.write('\n'.join(lines[:half]))

    with open(ULA_DIR / '02_spectrum_ula_part2.txt', 'w', encoding='utf-8') as f:
        f.write(f'# Spectrum ULA Book - Part 2\n\n')
        f.write('---\n\n')
        f.write('\n'.join(lines[half:]))

    print(f'  -> 00_spectrum_ula_full.txt (full)')
    print(f'  -> 01_spectrum_ula_part1.txt (first half)')
    print(f'  -> 02_spectrum_ula_part2.txt (second half)')


def split_z80():
    """Split Z80 documentation."""
    print(f'\n=== Splitting Z80 docs ===')

    # Z80 OPCODES GUIDE - small file, copy as-is
    if Z80_OPCODES_FILE.exists():
        with open(Z80_OPCODES_FILE, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        with open(Z80_DIR / '00_z80_opcodes_guide.md', 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'  -> 00_z80_opcodes_guide.md')

    # Programming the Z80 - large file, split into parts
    if Z80_PROG_FILE.exists():
        with open(Z80_PROG_FILE, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        lines = content.split('\n')

        # Split into 4 roughly equal parts
        n = 4
        part_size = len(lines) // n
        for i in range(n):
            start = i * part_size
            end = (i + 1) * part_size if i < n - 1 else len(lines)
            with open(Z80_DIR / f'{i+1:02d}_programming_z80_part{i+1}.txt', 'w', encoding='utf-8') as f:
                f.write(f'# Programming the Z80 - Part {i+1}/{n}\n\n')
                f.write('---\n\n')
                f.write('\n'.join(lines[start:end]))
            print(f'  -> {i+1:02d}_programming_z80_part{i+1}.txt ({end-start} lines)')


def create_index():
    """Create the master index for the docs folder."""
    index_path = PROJECT_DOCS / 'README.md'

    content = '''# Documentation Index

This folder contains reference documentation for the Cybernoid Spectrum → MSX porting project.

## Folder structure

```
docs/
├── README.md         (this file)
│
├── msx/              MSX Red Book - MSX hardware reference
├── spectrum/         Spectrum ROM disassembly
├── ula/              Spectrum ULA technical book
└── z80/              Z80 CPU documentation
```

## MSX (`msx/`)

The MSX Red Book split by chapter.

| File | Content | Use for |
|------|---------|---------|
| `00_introduction.md` | TOC and intro | Overview |
| `chapter1.md` | Chapter 1: PPI (8255) - ports $A8-$AB | **Keyboard matrix reading**, slot selection |
| `chapter2.md` | Chapter 2: VDP (TMS9918) - ports $98/$99 | **Screen graphics**, modes, sprites |
| `chapter3.md` | Chapter 3: PSG (AY-3-8910) - ports $A0-$A1 | **Sound generation** |
| `chapter4.md` | Chapter 4: ROM BIOS standard routines | BIOS calls (INIT32, WRTVP, SNSMAT, etc.) |
| `chapter5.md` | Chapter 5: ROM BASIC interpreter | (less relevant) |
| `chapter6.md` | Chapter 6: Memory map, workspace area | RAM layout at $F380-$FFFF |
| `chapter7.md` | Chapter 7: Machine code program examples | Reference for keyboard/screen code |

### Quick reference: ports

| Port | Function | Documented in |
|------|----------|---------------|
| `$98` | VDP data | `chapter2.md` |
| `$99` | VDP command/status | `chapter2.md` |
| `$A0` | PSG register select / Keyboard row (PPI C) | `chapter1.md`, `chapter3.md` |
| `$A1` | PSG data write / Keyboard column (PPI B) | `chapter1.md`, `chapter3.md` |
| `$A8` | PPI port A (slot select) | `chapter1.md` |
| `$A9` | PPI port B (keyboard column read) | `chapter1.md` |
| `$AA` | PPI port C (keyboard row select) | `chapter1.md` |
| `$AB` | PPI mode | `chapter1.md` |

### Quick reference: BIOS calls (used in this port)

| Address | Name | Description | Documented in |
|---------|------|-------------|---------------|
| `$0041` | DISSCR | Disable screen | `chapter4.md` |
| `$0044` | ENASCR | Enable screen | `chapter4.md` |
| `$0047` | WRTVDP | Write VDP register (A=value, C=reg) | `chapter4.md` |
| `$006F` | INIT32 | Initialize graphics mode | `chapter4.md` |
| `$0093` | WRTPSG | Write PSG register (A=reg, E=value) | `chapter4.md` |
| `$0141` | SNSMAT | Read keyboard matrix row (C=row) | `chapter4.md` |
| `$1102` | WRTPSG (alt) | Alternative PSG write entry | `chapter4.md` |
| `$110E` | RDPSG | Read PSG register | `chapter4.md` |

## Spectrum (`spectrum/`)

Spectrum ROM disassembly (from the book by Dr. Ian Logan & Dr. Frank O\'Hara).

| File | Content | Use for |
|------|---------|---------|
| `00_preface_and_intro.txt` | Preface, contents | Overview |
| `01_restart_routines.txt` | RST 0, RST 8, RST 16, etc. tables | Interrupt handling |
| `02_keyboard_routines.txt` | Keyboard scanning routines | **Comparing Spectrum keyboard to MSX** |
| `03_loudspeaker_routines.txt` | Beeper routines | **Sound generation reference** |
| `04_cassette_routines.txt` | Tape loading | **For TZX extraction reference** |
| `05_screen_printer_routines.txt` | Screen/printer handling | **Video routines** |
| `06_executive_routines.txt` | Main execution loop | Runtime behavior |
| `07_basic_interpreter.txt` | BASIC interpreter | (less relevant) |

### Quick reference: Spectrum I/O

| Port | Function | Documented in |
|------|----------|---------------|
| `$FE` | Border + beeper + keyboard | `02_keyboard_routines.txt`, `03_loudspeaker_routines.txt` |
| `$7FFD` | 128K memory paging | `06_executive_routines.txt` |
| `$FFFD/$BFFD` | AY-3-8912 (128K only) | not in 48K game |

### Quick reference: Spectrum memory map

| Range | Use | Documented in |
|-------|-----|---------------|
| `$0000-$3FFF` | ROM (16K) | `00_preface_and_intro.txt` |
| `$4000-$5AFF` | Screen + attributes | `05_screen_printer_routines.txt` |
| `$5B00-$FFFF` | RAM (varies) | various |

## ULA (`ula/`)

Technical book about the Spectrum ULA chip (Chris Smith, 2010).

| File | Content |
|------|---------|
| `00_spectrum_ula_full.txt` | Full text of the book |
| `01_spectrum_ula_part1.txt` | First half |
| `02_spectrum_ula_part2.txt` | Second half |

This is a deep technical reference for the Spectrum ULA - useful for understanding the exact behavior of the beeper, video generation, and memory contention.

## Z80 (`z80/`)

| File | Content |
|------|---------|
| `00_z80_opcodes_guide.md` | Concise Z80 instruction guide (in Spanish) |
| `01_programming_z80_part1.txt` | Programming the Z80 - Part 1/4 |
| `02_programming_z80_part2.txt` | Programming the Z80 - Part 2/4 |
| `03_programming_z80_part3.txt` | Programming the Z80 - Part 3/4 |
| `04_programming_z80_part4.txt` | Programming the Z80 - Part 4/4 |

The "Programming the Z80" book (Rodnay Zaks) is the canonical Z80 reference. It covers assembly language programming in detail.

---

## When porting Cybernoid, consult these in order

1. **MSX Red Book Chapter 1** (PPI) - for the MSX keyboard matrix layout
2. **MSX Red Book Chapter 2** (VDP) - for graphics mode setup and sprite handling
3. **MSX Red Book Chapter 3** (PSG) - for replacing the Spectrum beeper
4. **MSX Red Book Chapter 4** (BIOS) - for the BIOS calls (SNSMAT, WRTVDP, etc.)
5. **MSX Red Book Chapter 6** (Memory map) - for RAM layout and workspace
6. **Spectrum keyboard routines** (`spectrum/02_keyboard_routines.txt`) - to understand what Spectrum keys the game uses
7. **Spectrum loudspeaker routines** (`spectrum/03_loudspeaker_routines.txt`) - to understand the beeper implementation

## Quick lookups

### Reading the MSX keyboard matrix

See `msx/chapter1.md`, sections "PPI Port B" and "PPI Port C":
- Use PPI Port C (port $AA) to select a row (0-10) in the lower 4 bits
- Read PPI Port B (port $A9) to get 8 column inputs
- 0 = pressed (active low)

### Setting MSX VDP register

See `msx/chapter4.md`, "WRTVDP" entry:
- A = value to write
- C = register number (0-7)

Or directly:
- Write value to port $99, then write $80|reg_num to port $99

### Writing to PSG register

See `msx/chapter3.md`:
- Write register number to port $A0
- Write value to port $A1

### Spectrum port $FE layout

```
bit 0: bit 0 of keyboard row (e.g. CAPS_SHIFT for row $FE)
bit 1: bit 1 of keyboard row (e.g. Z for row $FE)
bit 2: bit 2 of keyboard row (e.g. X for row $FE)
bit 3: bit 3 of keyboard row (e.g. C for row $FE)
bit 4: BEEPER state (1 = speaker ON)
bit 5: unused
bit 6: unused
bit 7: unused
+ MIC (bit 3) and EAR (bit 4) on 48K Spectrum via port $FE
```

Reading keyboard: write row high byte to upper 8 address bits, read byte.
Example: `LD A,$FE; IN A,($FE)` reads row 0 (CAPS, Z, X, C, V).
'''
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'\n=== Created master index: {index_path} ===')


def main():
    # Create output folders
    for d in [MSX_DIR, SPECTRUM_DIR, Z80_DIR, ULA_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    # Split documents
    split_msx()
    split_spectrum_rom()
    split_spectrum_ula()
    split_z80()

    # Create the index
    create_index()

    print('\n' + '=' * 60)
    print('Documentation split complete!')
    print('=' * 60)


if __name__ == '__main__':
    main()