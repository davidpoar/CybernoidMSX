# Cybernoid MSX Port

Port of **Cybernoid** (ZX Spectrum 48K, Hewson Consultants, 1988) to MSX.

Based on the original `Cybernoid.tzx` tape image, reverse engineered from the
Spectrum ROM disassembly and the MSX Red Book.

## Status

| Step | Description | State |
|------|-------------|-------|
| 1 | Extract TZX, decrypt the loader, rebuild the 48K memory image | done |
| 2 | Identify the I/O routines (video, sound, keyboard) | done |
| 3 | Rewrite the I/O for MSX (VDP / PSG / keyboard matrix) | done |
| 3b | Port the video layer (Spectrum bitmap -> VDP mode 2) | done |
| 4 | Polish: sound quality, single-file cartridge, docs | pending |

## Building

```bash
py tools/run_all.py             # steps 1 and 2: extract and analyse
py msx/scripts/build.py         # build the ROM and the .COM
```

Requirements: **pasmo** (Z80 cross assembler) and Python 3.

### Output

| File | Description |
|------|-------------|
| `msx/build/cybernoid.com` | MSX-DOS 2 executable, self contained (41728 bytes) |
| `msx/build/cybernoid.rom` | 16K MSX ROM cartridge (game logic + I/O shims) |

## Running

### The .COM (recommended)

Needs **MSX-DOS 2 with a memory mapper** (a 64 KB transient program area),
because the game needs writable memory on all four pages of the Z80 address
space (see "Memory layout" below).

```
A>cybernoid.com
```

### The .ROM cartridge

Insert `cybernoid.rom` in the cartridge slot. The ROM initialises the MSX
hardware and provides the I/O shims, but the game data has to be loaded
separately, so the screen stays blank. Useful for testing the input and
sound shims on a plain MSX.

## How the port works

### Memory layout

The Spectrum game contains roughly 1200 absolute address references inside
the `$6504-$FFFF` range. They only work if the game sits at exactly the
same addresses as on the Spectrum, so the port avoids relocating any of
the 39 KB of game code.

The MSX memory map happens to line up perfectly:

| Spectrum | MSX | Contents |
|----------|-----|----------|
| `$4000-$5AFF` | page 1 | screen pixels + attributes |
| `$5B00-$64BF` | page 1 | attribute copy, sprite data, screen tables |
| `$6504-$7FFF` | page 1 | game part 1 (code) |
| `$8000-$FFFF` | pages 2-3 | game part 2 (code + graphics data) |

The catch: the game also needs *writable* memory at `$4000-$64BF`, so page 1
has to be RAM too. That means the machine must run in **"all RAM" mode**
(the primary slot register pointing every page at the main RAM slot),
which is what MSX-DOS 2 does for programs that need a 64 KB TPA.

The `.COM` stub does exactly that:

```
LD   A, $FF
OUT  ($A8), A      ; every page -> the RAM slot
```

### Video: the Spectrum screen maps almost 1:1 onto VDP mode 2

The TMS9918 in Graphics Mode 2 has a very similar structure to the
Spectrum screen, which made the conversion cheap:

| Spectrum | MSX mode 2 | Notes |
|----------|-------------|-------|
| pixels `$4000-$57FF` (768 cells x 8 bytes, 1bpp, MSB = left) | pattern table VRAM `$0000-$17FF` | same pixel format, no conversion needed |
| attributes `$5800-$5AFF` (768 bytes) | colour table VRAM `$2000-$37FF` | 1:1 mapping, only the colour codes differ |
| - | name table VRAM `$3800-$3AFF` | the cell index (the column number) |

The only differences are the row order and the colour encoding:

* the Spectrum interleaves 8 screen lines `$20` apart, MSX stores them
  contiguously, so a row is copied with a separate 256 byte loop
* the Spectrum attribute is `ink:3 | paper:3 | flash | bright`, the MSX
  colour entry is `bg:4 | fg:4`, so a 256 entry conversion table is
  built at start-up

Spectrum colour to MSX colour:

| Spectrum | MSX | Value |
|----------|-----|-------|
| black | black | 1 |
| blue | medium blue | 8 |
| red | light red | 9 |
| magenta | magenta | 13 |
| green | medium green | 2 |
| cyan | light blue | 5 (MSX has no cyan) |
| yellow | yellow | 14 |
| white | white | 15 |

The video layer (`msx/src/video.asm`) is incremental: `MSX_VIDEO_SYNC_ROWS`
converts a configurable number of rows per call, so a rotating cursor can
spread the work over several frames.

### Input: the keyboard matrix

The Spectrum has an 8x5 matrix read through port `$FE`; the MSX has an
11x8 matrix read through the 8255 PPI (row select on port `$AA`, columns
on port `$A9`).

`MSX_KBD_READ` receives the Spectrum row selector in A, scans the MSX rows
that matter and returns a Spectrum-shaped 5 bit value.

MSX keyboard matrix (from the Red Book key code table at `$0DA5`):

```
         Column 7 6 5 4 3 2 1 0
Row 0:            0 1 2 3 4 5 6 7
Row 3:            c d e f g h i j
Row 4:            k l m n o p q r
Row 5:            s t u v w x y z
Row 8:        SPACE at column 0
```

Current mapping:

| MSX key | Spectrum row | Bit | Game action |
|----------|--------------|-----|-------------|
| `SPACE` | `$F7` | 0 | fire |
| `SPACE` | `$7F` | 1 | - |
| `Z` | `$FE` | 1 | - |
| `X` | `$FE` | 2 | - |

### Sound

The Spectrum beeper is a single bit in port `$FE`; the port is emulated by
`MSX_BEEPER`, which maps the border colour onto VDP register 7 and the
beeper onto PSG channel A.

### Interrupts

The game sets up its own IM 2 vector at `$FDFD` with the handler at
`$70D3`. That code only writes to RAM, so it works unchanged on MSX. The
init code additionally installs `MSX_IM2_HANDLER` (which calls the game's
handler) and enables the VDP frame interrupt (register 1 bit 5), which is
what actually generates the interrupts on MSX.

### Patches applied to the game binary

| Spectrum address | Original | Patched | Where |
|------------------|----------|---------|-------|
| `$65ED` | `DB FE` | `CALL MSX_KBD_READ` | ROM / build time |
| `$65F4` | `DB FE` | `CALL MSX_KBD_READ` | ROM / build time |
| `$660D` | `DB FE` | `CALL MSX_KBD_READ` | ROM / build time |
| `$7B4C` | `DB FE` | `CALL MSX_KBD_READ` | ROM / build time |
| `$651F` | `D3 FE` | `CALL MSX_BEEPER` | ROM / build time |
| `$8637` | `D3 FE` | `CALL MSX_BEEPER` | RAM / run time |

Only known code addresses are patched, so data bytes that happen to look
like `DB FE` are left alone.

## Project layout

```
cybernoidMSX/
├── README.md
├── docs/                     Reference documentation (see docs/README.md)
│   ├── README.md             Master index of all the documentation
│   ├── split_docs.py         Regenerates the split files
│   ├── msx/                  MSX Red Book, split by chapter
│   ├── spectrum/             Spectrum ROM disassembly, split by section
│   ├── ula/                  Spectrum ULA technical book
│   └── z80/                  Z80 CPU documentation
├── original/                 The original tape image and raw blocks
│   ├── Cybernoid.tzx
│   └── raw_blocks/
├── tools/                    Spectrum analysis tools (Python)
│   ├── paths.py              Shared path constants
│   ├── extract_tzx.py        TZX -> raw blocks
│   ├── decrypt_loader.py     Decrypt the self-modifying loader
│   ├── build_mem_image.py    Rebuild the 48K memory image
│   ├── disasm.py             Disassemble the loader
│   ├── disasm_game.py        Disassemble the game entry point
│   ├── find_io.py            Group all IN/OUT instructions by port
│   ├── find_io_routines.py   Detailed I/O routine map
│   ├── find_keyboard.py      Find the keyboard scanning routines
│   ├── find_sound.py         Find the sound routines
│   ├── show_bytes.py         Dump the key data structures
│   ├── generate_notes.py     Generate spectrum/disasm/PORTING_NOTES.txt
│   ├── run_step1.py          Master script for step 1
│   └── run_all.py            Master script for steps 1 and 2
├── spectrum/                 Spectrum binaries and disassembly
│   ├── loader_decrypted.bin
│   ├── cybernoid_block9_main.bin
│   ├── cybernoid_before_lddr.bin
│   ├── cybernoid_after_lddr.bin
│   └── disasm/               Disassembly output + PORTING_NOTES.txt
└── msx/                      The MSX port
    ├── src/
    │   ├── config.asm        Shared addresses (preprocessed by the build)
    │   ├── io.asm            Keyboard, beeper, IM 2 handler
    │   ├── video.asm         Spectrum screen -> VDP mode 2
    │   ├── init.asm          MSX hardware set-up
    │   └── stub.asm          .COM entry point
    ├── scripts/
    │   ├── build.py          Master build script
    │   ├── verify.py         Verify the ROM and .COM
    │   └── analyze_*.py      Analysis helpers
    ├── test/                 Test harness (uses the z80emu Z80 core)
    │   ├── Program.cs        ROM cartridge tests
    │   ├── com/ComTest.cs    .COM tests
    │   └── debug/            Debug helpers
    ├── docs/TECHNICAL.md     Technical notes for the port
    └── build/                Build output
```

## Testing

The test harness runs the built ROM and `.COM` on the Z80 core from
`C:\Dev\z80emu` with a minimal MSX machine (slot-mapped memory bus, PPI
keyboard, and a small TMS9918 model) and checks the behaviour end to end.

```bash
cd msx/test
dotnet run                        # ROM cartridge tests
$env:CYBERNOID_COM="1"; dotnet run # .COM tests
$env:CYBERNOID_SCREEN="1"; dotnet run  # dump the Spectrum screen
```

## Documentation

`docs/README.md` is the index of all the reference documentation, with
quick reference tables for the MSX ports, the BIOS entry points and the
Spectrum port `$FE` layout, plus the recommended reading order for
porting.
