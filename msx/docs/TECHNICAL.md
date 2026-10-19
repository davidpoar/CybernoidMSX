# MSX Port — Technical Notes

## Build system

```bash
py msx/scripts/build.py      # build ROM + BIN
py msx/scripts/verify.py     # verify the produced files
```

`build.py` does:
1. Assembles `src/init.asm` (org `$0100`), `src/io.asm` (org `$9AFC`) and
   `src/stub.asm` (org `$4010`) with **pasmo**
2. Patches the stub's length placeholders with the real sizes
3. Patches the game binary (see below)
4. Emits `build/cybernoid.rom` (16K cartridge) and `build/cybernoid.bin`

### pasmo syntax notes (this build)

- `EQU` not `:=` for constants
- `org`, `ds`, `db`, `dw`, `end` have **no leading dot**
- Low byte of a label: `label & $FF`; high byte: `label / 256`
- No `LOW()`/`HIGH()` functions
- String literals cannot contain doubled `""` — build the message with
  separate `db` statements

## Memory map

### MSX RAM at runtime

```
$0000-$9AFB   Game code + data (BLOADed from cybernoid.bin)
$9AFC-$9CFF   MSX I/O routines (persists above the .BIN range)
$F380-$FFFF   MSX workspace area (stack, BIOS vars)
```

### ROM cartridge (`$4000-$7FFF`)

```
$4000-$400F  "AB" header, INIT = $4010, other handlers = 0
$4010-$402C  Stub: DI; LD SP,$F380; 2x LDIR; JP $0100
$4110-$4205  Init code (also copied to RAM $0100)
$4200-$42BF  I/O routines (also copied to RAM $9AFC)
```

## Why the game is BLOADed at `$0000`

The Spectrum game code contains dozens of absolute addresses in the
`$0000-$FFFF` range (`CALL $70B4`, `LD HL,$5B00`, `JP $6504`, …).

By loading the game at MSX `$0000` we get **zero address shift**:

```
Spectrum $6504 (entry)  ->  MSX $0000
Spectrum $70B4 (IM 2)    ->  MSX $70B4   (game's own code, NOPed)
Spectrum $FFFF           ->  MSX $9AFB
```

Every absolute address inside the game therefore still points at the
right place. This avoids having to relocate ~40 KB of Z80 code.

The cost: the I/O routines cannot live in `$0000-$9AFB` (the game is
loaded there), so they are placed at `$9AFC`, just above the game.

## The ROM stub

On power-up MSX calls the cartridge INIT entry at `$4010`. The stub:

```asm
        DI
        LD   SP, $F380
        LD   HL, $4110          ; init code in ROM
        LD   DE, $0100          ; destination in MSX RAM
        LD   BC, $00F6          ; 246 bytes
        LDIR
        LD   HL, $4200          ; I/O routines in ROM
        LD   DE, $9AFC          ; destination in MSX RAM
        LD   BC, $00C0          ; 192 bytes
        LDIR
        JP   $0100              ; run init code
```

Why copy to RAM at all? Because the game's patched `CALL` instructions
must reach the I/O routines at MSX `$9AFC`. Those routines live in RAM so
the absolute addresses in the game binary (`CALL $9AFC`) stay valid
regardless of what ROM bank is mapped.

## Patches

Applied to the game binary in `build.py`:

| Spectrum | Bytes | Meaning |
|----------|-------|---------|
| `$65ED` | `DB FE` -> `CD FC 9A` | `IN A,($FE)` -> `CALL $9AFC` |
| `$65F4` | `DB FE` -> `CD FC 9A` | `IN A,($FE)` -> `CALL $9AFC` |
| `$660D` | `DB FE` -> `CD FC 9A` | `IN A,($FE)` -> `CALL $9AFC` |
| `$7B4C` | `DB FE` -> `CD FC 9A` | `IN A,($FE)` -> `CALL $9AFC` |
| `$651F` | `D3 FE` -> `CD 7B 9B` | `OUT ($FE),A` -> `CALL $9B7B` |
| `$70B4` | 30 bytes -> `00` | NOP out the game's IM 2 setup |

The `IN A,($FE)` sites were found by `tools/find_keyboard.py`, which scans
the disassembly for `LD A,nn` + `IN A,($FE)` pairs. Only known-good code
addresses are patched — data bytes that happen to look like `DB FE` are
left alone.

## MSX hardware references

See `docs/README.md` for the full index. The relevant bits:

### Keyboard (PPI 8255) — `docs/msx/chapter1.md`

- Port `$AA` (PPI C): write the row number (0-10) in bits 0-3, keeping
  bits 4-7 (cas motor, cas out, cap LED, key click)
- Port `$A9` (PPI B): read the 8 column inputs
- Active low: **0 = key pressed**

```asm
READ_MSX_ROW:
        IN   A, ($AA)
        AND  $F0
        OR   C
        OUT  ($AA), A
        NOP
        NOP
        IN   A, ($A9)
```

### VDP (TMS9918) — `docs/msx/chapter2.md`

- Port `$98` data, port `$99` command/status
- `INIGRP` (BIOS `$0072`) initialises Graphics Mode (256x192, 16 colours)
- `WRTVDP` (BIOS `$0047`) takes **B** = value, **C** = register number

### PSG (AY-3-8910) — `docs/msx/chapter3.md`

- Port `$A0` register select, port `$A1` data write
- `GICINI` (BIOS `$0090`) initialises it
- Register 7 = mixer (bit 0-2 disable tone A/B/C, bit 3-5 disable noise)
- Register 8/9/10 = channel A/B/C amplitude
- `WRTPSG` (BIOS `$0093`) takes **A** = register, **E** = value

### BIOS entry points used

| Address | Name | Input | Output |
|---------|------|-------|--------|
| `$0047` | WRTVDP | B=value, C=reg | — |
| `$0072` | INIGRP | — | graphics mode |
| `$0090` | GICINI | — | PSG init |
| `$009F` | CHGET | — | A=char (waits) |
| `$00A2` | CHPUT | E=char | — |
| `$00C2` | CLS | — | — |

## Keyboard emulation

The Spectrum has an 8x5 matrix read through port `$FE`; the MSX has an
11x8 matrix read through the PPI. `MSX_KBD_READ` (at `$9AFC`) receives the
Spectrum row selector in A and returns a Spectrum-shaped 5-bit value.

The Spectrum row byte has exactly one bit clear to select the row
(`$FE` = row 0, `$FD` = row 1, … `$7F` = row 7). `MSX_KBD_READ` finds that
clear bit and returns the cached state for that row.

`SCAN_KBD` reads three MSX rows and maps them:

| MSX row | Bit | MSX key | Spectrum row | Spectrum bit |
|----------|-----|---------|--------------|--------------|
| 0 | 3 | Z | `$FE` | 1 |
| 1 | 3 | X | `$FE` | 2 |
| 8 | 0 | SPACE | `$F7` | 0 |
| 8 | 0 | SPACE | `$7F` | 1 |

To add a key, add a `LD C,n` / `CALL READ_MSX_ROW` / `BIT n,A` block in
`SCAN_KBD` and clear the appropriate bit in `kbd_buf`.

## Interrupt handling

The Spectrum game uses IM 2 with the vector at `$FDFD` and its handler
at `$70D3`. On MSX we:

1. NOP out the game's IM 2 setup (`$70B4`)
2. Install our own IM 2 with vector base `$F0` and handler
   `MSX_IM2_HANDLER` (at `$9BA7`)
3. `MSX_IM2_HANDLER` saves all registers, calls the game's original
   handler at MSX `$70D3` (which is still valid — the game is at `$0000`),
   restores, and `RETI`

## Remaining work

### Video (the big one)

The Spectrum game renders into a 6144-byte bitmap at `$4000-$5AFF` plus
768 bytes of attributes at `$5800-$5AFF`. On MSX that address range is
cartridge ROM, so those writes go nowhere and the screen stays blank.

Options:
1. **Sprites** (recommended): convert the game's bitmap drawing into VDP
   sprite writes. The Spectrum version already uses 8x8 cells with
   attributes, which maps well onto MSX sprites (8x8 or 16x16).
2. **Character/bitmap mode**: MSX Graphics Mode 2 uses an 8x8 character
   generator; the game would need full re-rendering.
3. **TMS9918 in bitmap mode**: not available — the MSX VDP has no bitmap
   mode like the Spectrum ULA.

The relevant Spectrum routines (from `spectrum/disasm/PORTING_NOTES.txt`):

- `$671E` — screen clear
- `$6726` — `LD HL,$4000` (pixel base)
- `$679D` / `$67AD` — `LD DE/$HL,$5800` (attribute base)
- `$77F0` — `LD DE,$4000`

### Sound

The Spectrum beeper is a single bit; the game toggles it to make
sounds. `MSX_BEEPER` maps that to PSG channel A on/off, which loses the
pitch. To restore it, the game's sound state (in the routine at `$85BA`
and the tables at `$8710`) would need to be decoded into PSG frequency
and volume registers.

### Packaging

The current ROM requires the separate `.BIN` file. A single-file
cartridge would need a megaROM (Konami mapper, 8 KB banks) holding the
game data in banks 1..N, with the init code copying them into RAM at
boot.
