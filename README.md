# Cybernoid MSX Port

Port of **Cybernoid** (ZX Spectrum 48K, Hewson Consultants, 1988) to MSX.

Based on the original `Cybernoid.tzx` tape image, reverse engineered from
the Spectrum ROM disassembly and the MSX Red Book.

**The documentation in `docs/` is the most valuable part of this
repository.** It is written to be reused for other Spectrum to MSX
ports. Start with [`docs/PORTING_GUIDE.md`](docs/PORTING_GUIDE.md).

## Status

| Step | Description | State |
|------|-------------|-------|
| 1 | Extract the TZX, decrypt the loader, rebuild the 48K memory image | done |
| 2 | Identify the I/O routines (video, sound, keyboard) | done |
| 3 | Rewrite the I/O for MSX (VDP / PSG / keyboard matrix) | done |
| 3b | Convert the bitmap to VDP graphics mode 2 | done (binary port) |
| 4 | Native 64K ASCII16 cartridge with the assets converted | engine done, assets pending |

Two ports exist:

| Port | File | What it is |
|------|------|------------|
| Binary | `msx/build/cybernoid.com` | The original Z80 code runs untouched at `$6504-$FFFF`, with the keyboard, the beeper and the video conversion rewritten. Needs MSX-DOS 2 in all-RAM mode. |
| Native | `msx/build/cybernoid.rom` | A 64 KB ASCII16 cartridge. The engine (boot, VDP, bank switching) works and is tested; the game logic and the converted assets are not written yet. |

## Building

```bash
py tools/run_all.py             # steps 1 and 2: extract and analyse
py msx/scripts/build.py         # the binary port (.COM)
py msx/scripts/build_rom.py      # the native port (.ROM)
py msx/scripts/verify_rom.py    # static check of the .ROM
```

Requirements: **pasmo** (Z80 cross assembler) and Python 3.

## Running the native port

```
1. Insert cybernoid.rom in the cartridge slot
2. The ROM initialises the VDP in SCREEN 2, silences the PSG,
   self tests the bank switching and waits in the main loop
```

The cartridge needs an MSX that has the ASCII16 mapper and 64 KB of
RAM. The BIOS detects the cartridge and maps it to pages 1 and 2.

## Running the binary port

Needs MSX-DOS 2 with a 64 KB transient program area (all-RAM mode),
because the game has to sit at its original Spectrum addresses.

```
A>cybernoid.com
```

## Project layout

```
cybernoidMSX/
├── README.md
├── docs/                     Documentation (see docs/README.md)
│   ├── PORTING_GUIDE.md       MSX hardware facts + conversion recipes
│   ├── cybernoid/            Analysis of this particular game
│   └── reference/            Unmodified source documents, split
├── original/                 The original tape image
│   ├── Cybernoid.tzx
│   └── raw_blocks/
├── tools/                    Spectrum analysis tools (Python)
├── spectrum/                 Spectrum binaries and disassembly
└── msx/                      The MSX ports
    ├── src/                  The assembly
    ├── scripts/              Build and analysis scripts
    ├── test/                 Test harness (Z80 core from z80emu)
    └── build/                Build output
```

## Testing

The test harness runs the built ROM and `.COM` on the Z80 core from
`z80emu`, with a slot based memory bus, a PPI keyboard and a small
TMS9918 model.

```bash
cd msx/test
dotnet run                        # ROM cartridge tests
$env:CYBERNOID_COM="1"; dotnet run # .COM tests
$env:CYBERNOID_SCREEN="1"; dotnet run  # dump the Spectrum screen
```

## Credits

* **Cybernoid** by Raffaele Cecco, Hewson Consultants, 1988
* The MSX Red Book, the Spectrum ROM disassembly, the Spectrum ULA book
  and *Programming the Z80* are in `docs/reference/`
