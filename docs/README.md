# Documentation Index

Reference documentation for the Cybernoid Spectrum → MSX porting project.

## Folder structure

```
docs/
├── README.md         (this file)
├── split_docs.py     Script that generated these files
│
├── msx/              MSX Red Book - MSX hardware reference
├── spectrum/         Spectrum ROM disassembly (Logan & O'Hara)
├── ula/              Spectrum ULA technical book (Chris Smith)
└── z80/              Z80 CPU documentation
```

## MSX (`msx/`)

The MSX Red Book split by chapter.

| File | Content | When to consult |
|------|---------|-----------------|
| `00_introduction.md` | TOC, intro, organization | Overview |
| `chapter1.md` | Chapter 1: PPI (8255) - ports `$A8`-`$AB` | **Keyboard matrix** (port `$AA` row, `$A9` col), slot select |
| `chapter2.md` | Chapter 2: VDP (TMS9918) - ports `$98`/`$99` | **Screen graphics**, modes, sprites |
| `chapter3.md` | Chapter 3: PSG (AY-3-8910) - ports `$A0`/`$A1` | **Sound generation** |
| `chapter4.md` | Chapter 4: ROM BIOS standard routines | **BIOS calls** (INIT32, WRTVDP, SNSMAT, etc.) |
| `chapter5.md` | Chapter 5: ROM BASIC interpreter | (less relevant) |
| `chapter6.md` | Chapter 6: Memory map, workspace area | RAM layout, `$F380`-`$FFFF` |
| `chapter7.md` | Chapter 7: Machine code program examples | Sample code |

### Quick reference: MSX I/O ports

| Port | Function | See in |
|------|----------|--------|
| `$98` | VDP data | `chapter2.md` |
| `$99` | VDP command/status | `chapter2.md` |
| `$A0` | PSG register select | `chapter3.md` |
| `$A1` | PSG data write | `chapter3.md` |
| `$A8` | PPI port A (slot select) | `chapter1.md` |
| `$A9` | PPI port B (keyboard column) | `chapter1.md` |
| `$AA` | PPI port C (keyboard row + misc) | `chapter1.md` |
| `$AB` | PPI mode | `chapter1.md` |

### Quick reference: MSX BIOS calls (used in this port)

| Address | Name | Description | See in |
|---------|------|-------------|--------|
| `$0041` | DISSCR | Disable screen | `chapter4.md` |
| `$0044` | ENASCR | Enable screen | `chapter4.md` |
| `$0047` | WRTVDP | Write VDP register (A=value, C=reg) | `chapter4.md` |
| `$006F` | INIT32 | Initialize graphics mode 2 | `chapter4.md` |
| `$0093` | WRTPSG | Write PSG register (A=reg, E=value) | `chapter4.md` |
| `$0141` | SNSMAT | Read keyboard matrix row (C=row) | `chapter4.md` |
| `$1102` | WRTPSG | Alternative PSG write entry | `chapter4.md` |
| `$110E` | RDPSG | Read PSG register | `chapter4.md` |

## Spectrum (`spectrum/`)

Spectrum 48K ROM disassembly (Dr. Ian Logan & Dr. Frank O'Hara, 1983).

| File | Content | When to consult |
|------|---------|-----------------|
| `00_preface_intro.txt` | Preface, contents, intro | Overview |
| `01_restart_routines.txt` | RST 0-56 routines and tables | Interrupt handling |
| `02_keyboard_routines.txt` | Keyboard scanning routines | **Comparing Spectrum keyboard to MSX** |
| `03_loudspeaker_routines.txt` | BEEPER subroutine | **Sound generation reference** |
| `04_cassette_routines_part1of3.txt` | Cassette handling (1/3) | TZX format details |
| `04_cassette_routines_part2of3.txt` | Cassette handling (2/3) | TZX format details |
| `04_cassette_routines_part3of3.txt` | Cassette handling (3/3) | TZX format details |
| `05_executive_screen_routines_part1of2.txt` | Executive + screen handling (1/2) | **Video routines** |
| `05_executive_screen_routines_part2of2.txt` | Executive + screen handling (2/2) | **Video routines** |
| `06_basic_interpreter_part1of3.txt` | BASIC interpreter (1/3) | (less relevant) |
| `06_basic_interpreter_part2of3.txt` | BASIC interpreter (2/3) | (less relevant) |
| `06_basic_interpreter_part3of3.txt` | BASIC interpreter (3/3) | (less relevant) |
| `07_expression_evaluation_part1of2.txt` | Expression evaluator (1/2) | (less relevant) |
| `07_expression_evaluation_part2of2.txt` | Expression evaluator (2/2) | (less relevant) |
| `08_arithmetic_routines_part1of2.txt` | Arithmetic routines (1/2) | (less relevant) |
| `08_arithmetic_routines_part2of2.txt` | Arithmetic routines (2/2) | (less relevant) |
| `09_floating_point_calculator_part1of2.txt` | Floating point calculator (1/2) | (less relevant) |
| `09_floating_point_calculator_part2of2.txt` | Floating point calculator (2/2) | (less relevant) |
| `99_appendix.txt` | Appendix: SIN/EXP/LN/ATN programs | Reference |

### Quick reference: Spectrum I/O

| Port | Function | See in |
|------|----------|--------|
| `$FE` | Border + beeper + keyboard | `02_keyboard_routines.txt`, `03_loudspeaker_routines.txt` |
| `$7FFD` | 128K memory paging | `06_*.txt` (128K only) |
| `$FFFD` / `$BFFD` | AY-3-8912 (128K only) | not in 48K game |

### Quick reference: Spectrum memory map

| Range | Use |
|-------|-----|
| `$0000-$3FFF` | ROM (16K) |
| `$4000-$5AFF` | Screen pixels (6144) + attributes (768) |
| `$5B00-$FFFF` | RAM (varies) |

## ULA (`ula/`)

Technical book about the Spectrum ULA chip (Chris Smith, 2010).

| File | Content |
|------|---------|
| `00_spectrum_ula_full.txt` | Full text of the book |
| `01_spectrum_ula_part1.txt` | First half (chapters 1-12) |
| `02_spectrum_ula_part2.txt` | Second half (chapters 13-25) |

Deep technical reference for the Spectrum ULA - useful for understanding exact behavior of beeper, video generation, and memory contention.

## Z80 (`z80/`)

| File | Content |
|------|---------|
| `00_z80_opcodes_guide.md` | Concise Z80 instruction guide (in Spanish) |
| `01_programming_z80_part1.txt` | Programming the Z80 - Part 1/4 (Ch 1-3) |
| `02_programming_z80_part2.txt` | Programming the Z80 - Part 2/4 (Ch 4-6) |
| `03_programming_z80_part3.txt` | Programming the Z80 - Part 3/4 (Ch 7-10) |
| `04_programming_z80_part4.txt` | Programming the Z80 - Part 4/4 (Ch 11-13+) |

The "Programming the Z80" book (Rodnay Zaks, 1980) is the canonical Z80 reference. It covers assembly language programming in detail.

---

## Reading order for Cybernoid porting

1. **MSX `chapter1.md`** (PPI) - for the MSX keyboard matrix layout
2. **MSX `chapter2.md`** (VDP) - for graphics mode setup and sprite handling
3. **MSX `chapter3.md`** (PSG) - for replacing the Spectrum beeper
4. **MSX `chapter4.md`** (BIOS) - for BIOS calls (SNSMAT, WRTVDP, INIT32, etc.)
5. **MSX `chapter6.md`** (Memory) - for RAM layout and workspace area
6. **`spectrum/02_keyboard_routines.txt`** - to understand Spectrum keyboard layout
7. **`spectrum/03_loudspeaker_routines.txt`** - to understand the beeper implementation
8. **`spectrum/05_executive_screen_routines_part1of2.txt`** - to understand screen routines

## Quick lookups

### Reading the MSX keyboard matrix (one row)

```z80
; Read MSX keyboard row N
LD   C, N           ; row number 0-10
LD   A, $F0
AND  $F0            ; preserve other bits of PPI C
OR   C              ; set row number
OUT  ($AA), A       ; PPI C - select row
IN   A, ($A9)       ; PPI B - read 8 columns
; A now contains: bit 0 = column 0 (rightmost), bit 7 = column 7 (leftmost)
; 0 = key pressed, 1 = key released (active low)
```

See `msx/chapter1.md` sections "PPI Port B" and "PPI Port C".

### Setting an MSX VDP register

```z80
; Set VDP register R to value V
; Method 1: via BIOS WRTVDP (recommended)
LD   C, R           ; register number
LD   A, V           ; value
CALL $0047          ; WRTVDP

; Method 2: direct I/O
LD   A, V
OUT  ($99), A
LD   A, $80 | R
OUT  ($99), A
```

See `msx/chapter4.md`, "WRTVDP" entry.

### Writing to a PSG register

```z80
; Method 1: via BIOS WRTPSG (recommended)
LD   A, R           ; register number (0-15)
LD   E, V           ; value
CALL $0093          ; WRTPSG

; Method 2: direct I/O
LD   A, R
OUT  ($A0), A       ; register select
LD   A, V
OUT  ($A1), A       ; data write
```

See `msx/chapter3.md`.

### Spectrum port $FE layout

| bit | function when reading (keyboard) | function when writing |
|-----|----------------------------------|----------------------|
| 0   | CAPS_SHIFT (row $FE) | Border bit 0 (blue) |
| 1   | Z (row $FE) | Border bit 1 (red) |
| 2   | X (row $FE) | Border bit 2 (green) |
| 3   | C (row $FE) | MIC |
| 4   | V (row $FE) | **BEEPER** |
| 5-7 | (depends on row) | unused |

Reading keyboard: write row high byte to upper 8 address bits, read byte.
Example: `LD A,$FE; IN A,($FE)` reads row 0 (CAPS, Z, X, C, V).

See `spectrum/02_keyboard_routines.txt`.

### Spectrum beeper

The beeper is controlled by bit 4 of `OUT ($FE),A`. Setting it high turns the speaker on; setting it low turns it off. A tone is produced by rapidly toggling this bit.

See `spectrum/03_loudspeaker_routines.txt`.

## Updating this folder

If you need to re-run the split, use:

```bash
py docs/split_docs.py
```

This regenerates all the split files from the source documents in `C:\Dev\z80emu\docs\systems\`.