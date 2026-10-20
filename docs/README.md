# Documentation Index

Reference material for the Cybernoid MSX port. The hardware and protocol
notes are written so they can be reused for other Spectrum to MSX ports.

```
docs/
├── README.md              (this file - index)
├── PORTING_GUIDE.md       MSX hardware facts + conversion recipes
├── STATUS.md              what is done, what is missing, how to go on
├── cybernoid/             Analysis of this particular game
│   ├── README.md          Index of the game analysis
│   ├── MEMORY_MAP.md      Post-LDDR memory layout, what is where
│   ├── IO_ROUTINES.md     Keyboard / sound / video routines found
│   └── VIDEO_MODEL.md     How the Spectrum screen maps onto MSX
└── reference/             Unmodified source documentation
    ├── _source/           The originals, kept so the split can be redone
    ├── msx/               MSX Red Book + the ASCII16 mapper reference
    ├── spectrum/          Spectrum ROM disassembly
    ├── ula/              Spectrum ULA technical book
    └── z80/              Z80 CPU documentation
```

## The short version

The full details are in **[PORTING_GUIDE.md](PORTING_GUIDE.md)**. The
essentials:

| Spectrum | MSX | Notes |
|----------|-----|-------|
| `IN A,($FE)` keyboard | PPI ports `$AA` (row) / `$A9` (columns) | 8x5 matrix emulated over the 11x8 MSX matrix |
| `OUT ($FE),A` beeper | PSG port `$A0` (register) / `$A1` (data) | Channel A |
| `OUT ($FE),A` border | VDP register 7 | Low nibble |
| Screen `$4000-$57FF` | VDP pattern table `$0000-$17FF` | 1bpp, 8 bytes per cell, same pixel order |
| Attributes `$5800-$5AFF` | VDP colour table `$2000-$37FF` | Needs ink/paper transposition and a colour remap |
| - | VDP name table `$1800-$1AFF` | One index per 8x8 cell |
| `IM 2` at `$FDFD` | Same, but the VDP frame IRQ must be enabled | VDP register 1, bit 5 |

## The ASCII16 mapper

`reference/msx/ascii16_mapper_reference.md` is the definitive
description, quoting openMSX. The short version:

* two 16 KB windows: `$4000-$7FFF` (bank A) and `$8000-$BFFF` (bank B)
* the registers are **plain memory**: `$6000-$67FF` and `$7000-$77FF`
  (the `$0800` granularity matters, `$6800-$6FFF` and `$7800-$7FFF` are
  not registers)
* the registers are write only, reset leaves both banks at 0
* **the BIOS already maps pages 1 and 2 to the cartridge**, so a
  cartridge that follows this convention does not need `ENASLT`

## Two ways to port a Spectrum game

| | Binary port | Native port |
|---|---|---|
| What moves | The original Z80 code, patched | The game is rewritten |
| Needs | The game in RAM at its original addresses | Only the converted assets |
| Memory | 40 KB+ of RAM (MSX-DOS 2, or a memory mapper) | 16-32 KB |
| Video | Convert the bitmap every frame | Native tiles and sprites |
| Effort | Low | High |
| Works on | MSX-DOS 2 / MSX2 with mapper | Any MSX |

Cybernoid was done both ways:

* **Binary port** - `msx/build/cybernoid.com`. The original code runs
  untouched at `$6504-$FFFF`, with the keyboard, the beeper and the
  video conversion rewritten. Needs MSX-DOS 2 in all-RAM mode.
* **Native port** - `msx/build/cybernoid.rom`. A 64 KB ASCII16
  cartridge with the engine in bank 0 and the converted assets in banks
  1-3. The engine works and is tested: it boots, the BIOS maps the
  cartridge to pages 1 and 2, the screen is loaded into the VRAM
  during the vblank and the converted graphics are shown. The game
  logic is not written yet.

## Reference documentation

`reference/` holds the unmodified source documents, split into readable
chunks with an index each:

| Folder | Document | What it is good for |
|--------|----------|--------------------|
| `reference/msx/` | MSX Red Book | PPI, VDP, PSG, BIOS entries, memory map |
| `reference/msx/` | ASCII16 mapper reference | The cartridge mapper, from openMSX |
| `reference/spectrum/` | Spectrum ROM disassembly (Logan & O'Hara) | The keyboard and beeper routines, the screen layout |
| `reference/ula/` | The ZX Spectrum ULA (Chris Smith) | How the beeper and the video hardware really work |
| `reference/z80/` | Programming the Z80 (Zaks) | Assembly language reference |

The originals are kept in `reference/_source/` so that the split can be
regenerated without needing another repository.

## Regenerating the split documents

```bash
py docs/split_docs.py
```

It reads `docs/reference/_source/` and rewrites `docs/reference/`.
`docs/rebuild_sources.py` puts the originals back together from the
split copies, in case the sources are ever lost.

