# Spectrum → MSX Porting Guide

Everything learned while porting Cybernoid, written to be reusable for
other ZX Spectrum → MSX ports.

Sections:

1. [The MSX machine](#1-the-msx-machine)
2. [The keyboard](#2-the-keyboard)
3. [The sound](#3-the-sound)
4. [The video](#4-the-video)
5. [The interrupts](#5-the-interrupts)
6. [The cartridge and the slots](#6-the-cartridge-and-the-slots)
7. [Two porting strategies](#7-two-porting-strategies)
8. [Getting the original graphics](#8-getting-the-original-graphics)
9. [Pitfalls](#9-pitfalls)

---

## 1. The MSX machine

### Memory map

```
$0000-$3FFF  page 0  system ROM (MSX BIOS)      - slot 0
$4000-$7FFF  page 1  user ROM / cartridge       - slot 1 usually
$8000-$BFFF  page 2  main RAM
$C000-$FFFF  page 3  main RAM (workspace $F380+)
```

The **primary slot register** (PPI port `$A8`) chooses which slot
provides each page:

```
bits 0-1  page 0    bits 4-5  page 2
bits 2-3  page 1    bits 6-7  page 3
```

Writing `$FF` points every page at slot 3, which on a MSX1 means the
main RAM - that is the "all RAM" mode a binary port needs.

The **workspace area** is `$F380-$FFFF` and is where the BIOS keeps its
variables, including:

| Address | Name | What it is |
|---------|------|------------|
| `$FCC1` | EXPTBL | 4 bytes, one per primary slot. `$80` if the slot is an expander, else `$00` |
| `$FCC5` | SLTTBL | 4 bytes, the secondary slot register of each primary slot |
| `$F35D` | - | the BIOS copy of the primary slot register |

### I/O ports

| Port | Device | Use |
|------|--------|-----|
| `$A0` | PSG | select register (also the keyboard row on MSX1 in some models) |
| `$A1` | PSG | write data |
| `$A2` | PSG | read data |
| `$A8` | PPI A | primary slot register (write) / read it back |
| `$A9` | PPI B | keyboard column inputs (read only) |
| `$AA` | PPI C | keyboard row select (write) / read back the value |
| `$AB` | PPI mode | do not touch |
| `$98` | VDP | VRAM data |
| `$99` | VDP | register select / status read |

---

## 2. The keyboard

### How the MSX keyboard is read

The MSX keyboard is an 11 row by 8 column matrix. The rows are selected
through **PPI port C** (`$AA`), whose lower four bits hold the row
number, and the columns come back through **PPI port B** (`$A9`).

```asm
; read row C, returns the 8 column bits in A
; (0 = key pressed, 1 = released)
READ_ROW:
        PUSH BC
        PUSH DE
        IN   A, ($AA)        ; current port C
        AND  $F0             ; keep the cas/led/click bits
        OR   C               ; select the row
        OUT  ($AA), A
        NOP
        NOP
        IN   A, ($A9)        ; the columns
        POP  DE
        POP  BC
        RET
```

The BIOS has a `SNSMAT` entry at `$0138` that does the same, but it
needs the BIOS mapped, so a direct read is safer inside a cartridge.

### The row layout

From the MSX Red Book key code table at `$0DA5` (NORMAL rows), the
column order is 7 = leftmost, 0 = rightmost:

```
         col 7 6 5 4 3 2 1 0
row 0        0 1 2 3 4 5 6 7      digits
row 1        8 9 . - @ [ ] ;
row 2        ' ` , . / (a) a b
row 3        c d e f g h i j
row 4        k l m n o p q r
row 5        s t u v w x y z
row 6        modifiers
row 7        F1 F2 F3 F4 F5
row 8        ESC TAB CAPS CODE SHIFT CTRL GRAPH
row 9        F2..F5, STOP, SELECT, HOME, INS, DEL
row 10       arrow keys
```

**SPACE is row 8, column 0.** Row 5 holds `S T U V W X Y Z`, so
**Z is row 5 column 7** and **X is row 5 column 5**.

### The Spectrum keyboard

The Spectrum has an 8x5 matrix read through port `$FE`. The row is
selected by the high byte of the port address, and the result is a
byte with one bit per key:

| Row | Bit 0 | 1 | 2 | 3 | 4 |
|-----|-------|---|---|---|---|
| `$FE` | CAPS | Z | X | C | V |
| `$FD` | A | S | D | F | G |
| `$FB` | Q | W | E | R | T |
| `$F7` | 1 | 2 | 3 | 4 | 5 |
| `$EF` | 0 | 9 | 8 | 7 | 6 |
| `$DF` | P | O | I | U | Y |
| `$BF` | ENTER | L | K | J | H |
| `$7F` | SPACE | SYM | M | N | B |

The row byte has exactly one bit clear, which is how the row is
selected. The bit values are the same convention as the MSX: 0 = pressed.

### Emulating the Spectrum keyboard on MSX

Keep an 8 byte buffer, one per Spectrum row, holding the 5 key bits.
When the game asks for a row, scan the MSX matrix, translate the MSX
keys into the Spectrum keys and return the buffer entry.

```asm
; A = the Spectrum row selector ($FE, $FD, ... $7F)
; Returns A = the 5 bit key state of that row
MSX_KBD_READ:
        PUSH HL
        PUSH BC
        PUSH DE
        LD   E, A                ; keep the row selector
        CALL SCAN_KBD             ; fill the row buffer

        ; find which buffer entry matches: the row selector has
        ; exactly one bit clear, and its position is the row index
        LD   A, E
        LD   HL, kbd_buf
        LD   B, 8
loop:   RRA                     ; the clear bit ends up in the carry
        JR   C, skip
        LD   A, (HL)             ; found it
        JR   done
skip:   INC  HL
        DJNZ loop
        LD   A, $1F              ; not found: nothing pressed
done:   POP  DE
        POP  BC
        POP  HL
        RET
```

**The buffer has to live in RAM**, not in cartridge ROM, because it is
written to on every scan. Put it at a fixed address in the RAM area
you have reserved.

---

## 3. The sound

### The Spectrum beeper

The Spectrum has one bit of sound: bit 4 of port `$FE`. Setting it
turns the speaker on, clearing it turns it off. A tone is produced by
toggling it at the right rate, and the games do that in a routine
driven by the frame interrupt.

Port `$FE` bit 0-2 also drive the border colour.

### The MSX PSG

The AY-3-8910 has 16 registers, selected through port `$A0`, with the
data written to port `$A1`:

| Register | What |
|----------|------|
| 0, 1 | channel A pitch |
| 2, 3 | channel B pitch |
| 4, 5 | channel C pitch |
| 6 | noise |
| 7 | mixer: bit 0-2 disable tone A/B/C, bit 3-5 disable noise A/B/C, bit 6-7 = I/O direction |
| 8, 9, 10 | channel A/B/C amplitude (bit 4 = modulated, bits 0-3 = level) |
| 11, 12 | envelope period |
| 13 | envelope shape |
| 14 | I/O port A (joystick) |
| 15 | I/O port B |

The master clock is 1.7897725 MHz, so the tone frequency is
`1789772.5 / (16 * (TP+1))` where TP is the 12 bit pitch value.

**Watch out:** register 7 bits 6 and 7 must be 1 (`10xxxxxx`), otherwise
the PSG's I/O pins can be damaged.

### Replacing the beeper

The simplest faithful replacement is to keep the game's own beeper
state machine and drive a PSG channel from it. If the game toggles the
beeper at the right rate, a square wave of that rate is what you hear.

A cruder approach, used in the Cybernoid binary port, is to treat the
beeper bit as on/off and enable or disable PSG channel A. It sounds
but loses the pitch.

If the game's sound routine is a self contained state machine (Cybernoid
has one at `$85BA` with tables at `$8710`), it is worth decoding it and
driving the PSG properly, with the pitch and the envelope coming from
the game's own tables.

---

## 4. The video

This is the hard part. The TMS9918 has no bitmap mode.

### The Spectrum screen

```
$4000-$57FF  pixels, 6144 bytes = 768 cells of 8x8, 1 bit per pixel
             the MSB of each byte is the leftmost pixel
             the rows are interleaved: line n of a block is $20 apart
$5800-$5AFF  attributes, 768 bytes, one per cell
             bits 0-2 = ink colour, bits 3-5 = paper colour
             bit 6 = flash, bit 7 = bright
```

The 32x24 cells are stored in a strange order: the screen is made of
three horizontal bands of 8 lines, and inside a band the lines are
interleaved. For cell (col, row):

```
pixel address = $4000 + (row/8)*$100 + (row%8)*$20 + col*8
attribute     = $5800 + row*32 + col
```

### The MSX in Graphics Mode 2 (SCREEN 2)

```
VRAM $0000-$17FF  pattern generator, 768 cells of 8 bytes
VRAM $1800-$1AFF  name table, 768 indices
VRAM $2000-$37FF  colour table
VRAM $3800-$3FFF  sprite patterns
VRAM $1B00-$1FFF  sprite attributes
```

Set up with the VDP registers:

```
R0 = $02   graphics mode (M3=1)
R1 = $E0   16K VRAM, IRQ enable, display on
R2 = $06   name table at $1800
R3 = $FF   colour table at $2000
R4 = $03   pattern generator at $0000
R5 = $36   sprite attributes at $1B00
R6 = $07   sprite patterns at $3800
R7 = $F1   border colour 1
```

**The pattern table and the colour table line up one to one.** The MSX
Red Book is explicit about it: "There is an exact byte-to-byte mapping
from the Character Pattern Table to the Colour Table". The entry at
the same offset gives the colours of that pixel line: the low nibble
for the 0 pixels, the high nibble for the 1 pixels.

The 6 KB of the pattern table are split in three 2 KB blocks, one per
third of the screen, because the character code is only 8 bits:

```
name table rows  0-7  use pattern block 0  ($0000-$07FF)
name table rows  8-15 use pattern block 1  ($0800-$0FFF)
name table rows 16-23 use pattern block 2  ($1000-$17FF)
```

The name table is initialised with the character code sequence 0 to
255 repeated three times, so the code of the cell at (column, row) is
`(row % 8) * 32 + column`, and the addresses of its pattern and its
colours are:

```
pattern = (row/8)*$800 + (row%8)*$100 + column*8
colour  = $2000 + (row/8)*$800 + (row%8)*$100 + column*8
```

**Use that layout and not "0 to 31 in every row".** With it every
cell has its own eight colour bytes, so a Spectrum screen with a
different ink and paper in every cell converts exactly. With the
shorter layout, all the rows of a third would share the colours of
their column, which is visible as big vertical bands of colour.

### Converting the Spectrum screen to mode 2

The pixel data needs no conversion: the Spectrum's 1 bpp 8x8 cell and
the TMS9918 pattern have the same layout, MSB leftmost.

What does need converting:

* the **row order**: the Spectrum interleaves 8 lines, MSX does not
* the **attribute**: Spectrum ink/paper in one byte, MSX wants a colour
  table entry per pattern line

So for each cell of the Spectrum screen, copy its 8 bytes to the
pattern table and write the converted attribute 8 times to the
matching place of the colour table. The colour numbers also change:

| Spectrum | MSX | | Spectrum | MSX |
|----------|-----|---|----------|-----|
| 0 black | 1 black | | 4 green | 2 medium green |
| 1 blue | 8 medium blue | | 5 cyan | 5 light blue |
| 2 red | 9 light red | | 6 yellow | 14 yellow |
| 3 magenta | 13 magenta | | 7 white | 15 white |

The Spectrum's "bright" attribute (bit 7) picks the lighter variant
of the MSX colour when there is one (medium blue becomes light blue,
medium green becomes light green). The "flash" attribute (bit 6) has
no equivalent in the MSX: either ignore it or use it to pick a
different colour.

**Two ways out:**

1. **Convert the bitmap.** Fill the pattern table from the Spectrum
   screen and build the colour table alongside it, as above. Every
   cell keeps its own colours, so the conversion is exact. The
   moving objects then have to be sprites, because a static bitmap
   cannot move.

2. **Use sprites for the moving objects.** The Spectrum's 8x8 sprite
   with an ink/paper attribute maps almost exactly onto a TMS9918
   sprite. The 32 sprites and the 4 per line limit are the
   constraints. A two colour sprite is made by overlapping two sprites.

### Getting the data into VRAM

The VDP is slow to access. A byte needs a minimum of 12 T states
between accesses, and on an MSX1 you cannot write to the VDP faster
than about every 24 T states without corrupting it.

Worse: **on real hardware the VDP only accepts VRAM writes during the
vertical blanking.** A 13 KB screen transfer cannot be done in one go
even in theory, and outside the blanking the writes are simply
ignored. So:

* transfer during **VBLANK** only, using the VDP frame interrupt
* spread the transfer over several frames, a slice per frame
* use `OUTI`/`OTIR` when the data is contiguous in memory, which is
  much faster than a byte at a time loop
* or, if the display is not time critical, spread the transfer over
  several frames and eat the tearing

A slice of 256 bytes costs about 2.4 ms at 3.58 MHz, which fits in
the blanking period. A whole 13 KB screen takes 51 frames, about a
second.

Reading the VDP status register (`$99`) tells you when the frame
starts: bit 7 is the interrupt flag, and it is set at the start of
the blanking.

**Do not clear the whole VRAM in one loop.** The classic
`LD BC,$4000 / OUT ($98),A / DEC BC` loop works in an emulator that
does not model the restriction, and fails on real hardware.

---

## 5. The interrupts

### The Spectrum

The game sets up `IM 2` with the interrupt vector at `$FDFD` and the
handler at, say, `$70D3`. The vector byte is `$FF`, so the CPU reads
the handler address from `$FEFF` and `$FF00`.

### On the MSX

The MSX VDP raises an interrupt at the start of each frame when
register 1 bit 5 is set. On a MSX1 the BIOS handles it in interrupt
mode 1 at `$0038`.

For a binary port, the simplest is to keep the game's own `IM 2` setup
and just make sure the VDP interrupt is enabled, because the game's
handler already does the work. The BIOS's own handler is bypassed
once the game switches to `IM 2`.

If the game never sets up `IM 2` itself, hook the BIOS handler
instead.

**Watch the vector address.** The Spectrum's `$FEFF` vector lives in
page 3, which on the MSX is RAM, so it is writable. But if the
vector byte is not `$FF` the vector lands somewhere else, and that
"somewhere else" has to be RAM too.

### The vblank hook of the MSX1 BIOS: `$FD9A` and `$FD9F`

This is the trick that makes a native cartridge possible, and it is
not in most books.

The MSX1 BIOS's own interrupt handler lives in the ROM at `$0C3C` and
starts like this:

```
$0C3C: PUSH HL / PUSH DE / PUSH BC / PUSH AF
$0C40: EXX / EX AF,AF' / PUSH ... / PUSH IY / PUSH IX
$0C4A: CALL $FD9A        ; called on EVERY interrupt
$0C4D: IN A,($99)        ; read the VDP status (this clears the F flag)
$0C4F: AND A
$0C50: JP P,$0D02        ; no interrupt pending: leave
$0C53: CALL $FD9F        ; called when the VDP raised the interrupt
```

`$FD9A` and `$FD9F` are in page 3, which is **RAM** on an MSX1, and
the BIOS leaves a `RET` in them. So a cartridge can put its own `JP`
there and get control at the start of every frame:

```
        ld   hl, $FD9F
        ld   (hl), $C3          ; JP nn
        inc  hl
        ld   de, MI_HANDLER
        ld   (hl), e
        inc  hl
        ld   (hl), d
```

Rules for the handler:

* the BIOS has already saved **every** register, so you can use the
  main register set freely, but **not** the alternate one: the BIOS
  did `EXX` and `EX AF,AF'` before saving, and it restores them
  afterwards
* the BIOS uses `A` right after the call (`LD ($F3E7),A`), so `A` and
  the flags have to be preserved
* the handler is called with the interrupts already disabled, so it
  can be as long as it wants (within one frame)
* the VDP status register has already been read, so its interrupt
  flag is clear: **you cannot use it to detect the blanking from
  inside the handler**, and the BIOS's read also means that a
  program polling the flag from the main loop will never see it

The alternative to the hook is to poll the status register for the
interrupt flag from the main loop. That only works if the VDP
interrupt is **disabled** (register 1 bit 5 clear), because otherwise
the BIOS's handler reads the status register first and clears the
flag. With the interrupt disabled the flag is still set at the start
of the blanking, and reading it from the main loop works.

### The main loop

`HALT` is the natural way to wait for the frame, but it has two
traps:

* with the interrupts disabled, a `HALT` is **not** woken up by an
  interrupt request on a real Z80, so the cartridge freezes
* the interrupt has to be enabled *before* the `HALT`, and an
  interrupt that arrives in that window is serviced before the
  `HALT`, so the program then waits a whole extra frame

The robust pattern is to wait for a counter that the interrupt
handler increments:

```
MAINLOOP:
        ei
        ld   a, (frame_count)
        ld   b, a
main_wait:
        ld   a, (frame_count)
        cp   b
        jr   z, main_wait
        ; ... the game logic, once per frame ...
        jr   MAINLOOP
```

It costs a busy loop, but it works everywhere, including with
debuggers and emulators that stop the CPU as soon as it halts.

---

## 6. The cartridge and the slots

### Finding our own slot

The BIOS maps the cartridge to page 1 before calling its INIT, so the
primary slot of page 1 is us:

```asm
        CALL $0138              ; RSLREG: A = primary slot register
        RRCA
        RRCA
        AND  $03                ; the slot of page 1
        LD   C, A
        LD   B, $00
        LD   HL, $FCC1          ; EXPTBL
        ADD  HL, BC
        OR   (HL)               ; bit 7 if the slot is an expander
        LD   C, A
        INC  HL
        INC  HL
        INC  HL
        INC  HL                 ; SLTTBL
        LD   A, (HL)
        AND  $0C
        OR   C                  ; A = F000SSPP
        LD   H, $80              ; the address of the page
        CALL $0024              ; ENASLT
```

`ENASLT` ("enable any slot permanently") switches a page to a slot. It
takes the **slot id** in A and the **address of the page** in HL. The
slot id is `FxxxSSPP`: bit 7 = the slot is expanded, bits 3-2 = the
secondary slot, bits 1-0 = the primary slot.

**Do not write to PPI port `$A8` yourself.** The BIOS keeps its own
copy of the slot register in the workspace and the two can get out of
sync.

### What ENASLT really computes

Worth knowing, because the masks it builds are not obvious. For the
address `$8000` and the slot id `$01` it produces:

```
B = $10   the OR mask: the slot number in the page 2 bits
C = $CF   the AND mask: keeps every page but page 2
D = $55   the slot number replicated over the register
E = $30   the page mask: the page 2 bits
```

so the new register is `(old & C) | B`. On a real MSX, `$04` (BIOS on
page 0, cartridge on page 1, RAM on pages 2 and 3) becomes `$14`:
page 2 now points at the cartridge.

### The ASCII16 mapper

A 64 KB cartridge with 16 KB banks and two independent bank
registers. The registers are **ordinary memory**, not I/O ports:

```
$6000-$67FF   selects the bank visible at $4000-$7FFF   (bank A)
$7000-$77FF   selects the bank visible at $8000-$BFFF   (bank B)
```

The decode has a granularity of `$0800`, so `$6800-$6FFF` and
`$7800-$7FFF` are **not** registers and writes there are ignored.
This matters: the MSX1 BIOS probes `$6000-$7FFF` to detect the
mapper type, and it only recognises a two window mapper if the
registers are where it expects them.

Other details of the real hardware, from openMSX's `RomAscii16kB`:

* the registers are **write only**: reading them returns the ROM
  content of the visible bank, not the register value
* reset leaves **bank A = 0 and bank B = 0**
* the bank number is masked: `block < n ? block : block & (n-1)`,
  so a 64 KB ROM (4 banks) mirrors `v & 3`
* pages 0 and 3 are **not connected** to the cartridge: reads give
  `$FF` and writes are ignored
* a ROM that is not a multiple of 16 KB is padded with `$FF`

```asm
SETBANK_B:
        ld   (cur_bank), a
        ld   (7000h), a
        ret
```

**The BIOS maps the cartridge to pages 1 *and* 2.** When it detects
a two window mapper the primary slot register ends up as `$D4`:
page 0 at slot 0 (the BIOS), pages 1 and 2 at the cartridge slot,
page 3 at slot 3 (the RAM). So a cartridge that follows this
convention does not have to call `ENASLT` at all. Calling it
anyway, with a wrong slot id, unmaps the BIOS and the cartridge at
the same time.

### The 64 KB cartridge layout used here

```
file $0000-$3FFF  bank 0 -> MSX $4000-$7FFF   header + engine
file $4000-$7FFF  bank 1 -> MSX $8000-$BFFF   assets
file $8000-$BFFF  bank 2 -> MSX $8000-$BFFF   assets
file $C000-$FFFF  bank 3 -> MSX $8000-$BFFF   assets
```

The header at `$4000`:

```
$4000  DB "AB"
$4002  DW INIT
$4004  DW 0        STATEMENT handler
$4006  DW 0        DEVICE handler
$4008  DW 0        TEXT pointer
$400A  DS 6,0      reserved
```

The MSX1 BIOS only checks the `"AB"` signature at `$4000`; the rest of
the header is not needed for the cartridge to start. Some collections
even use a compact 16 byte header with the INIT address at `$4002`.

Give each asset bank a signature byte (`$B0` + the bank number) at its
start. It makes the bank switching testable and it is a cheap way to
tell which bank is mapped.

---

## 7. Two porting strategies

### A. Binary port

The original Z80 code runs, with the I/O rewritten.

**The hard constraint**: the game contains absolute addresses, so it
only works if it sits at exactly the same addresses as on the
Spectrum. A 48 KB Spectrum game needs 48 KB of contiguous RAM, which
a MSX1 does not have.

**Solution**: run the machine in "all RAM" mode, where every page
points at the RAM slot:

```asm
        LD   A, $FF
        OUT  ($A8), A
```

This is what MSX-DOS 2 does for a program that needs more than
32 KB, and it is also what an MSX2 with a memory mapper can do.

The game then has to be assembled as a DOS `.COM` file, or loaded from
disk at the right address.

**What has to be rewritten:**

| Spectrum | MSX |
|----------|-----|
| `IN A,($FE)` | a call to the keyboard emulation |
| `OUT ($FE),A` | a call to the PSG and the border |
| `IM 2` setup | usually left alone, but the VDP IRQ has to be enabled |
| the screen | a conversion to mode 2, or sprites |

**The screen is the problem**: the game writes its bitmap to
`$4000-$57FF`, which in all-RAM mode is fine, but the conversion
costs CPU time every frame.

Cybernoid's binary port is `msx/build/cybernoid.com`.

### B. Native port

The game is rewritten in MSX terms. The engine is compact and lives in
the cartridge, and only the converted assets need to be stored.

**When to choose this**: when the game has to run on a plain MSX1,
when the video needs to be native anyway (sprites), or when the
Spectrum binary is too large.

**What has to be done:**

* decode the Spectrum's graphics data into tiles and sprites
* rebuild the screens from tiles
* port the game logic
* write the sound with the PSG

Cybernoid's native skeleton is `msx/build/cybernoid.rom`.

---

## 8. Getting the original graphics

To convert the graphics you first have to see them, and the fastest
way is to run the original game and photograph the screen.

**A minimal Spectrum is enough.** The 48K Spectrum has:

* 16 KB of RAM at `$4000-$FFFF` (the screen, the tables and the game)
* the screen is just RAM, so no ULA emulation is needed to read it
* the keyboard is `IN A,($FE)`, where **A holds the high byte of the
  port address and the bit that is 0 in it selects the half row**
* the border and the speaker are `OUT ($FE),A`: bit 4 is the speaker
  and bits 0-2 the border colour
* the frame interrupt is the only thing the game needs from the
  outside

So a Spectrum in fifty lines of C# runs a Spectrum game: give it the
memory image, generate the interrupt at 50 Hz and read the screen out
of RAM. The MSX Red Book is not needed, and neither is the Spectrum
ROM, because the game uses `IM 2` with the vector in RAM.

Two things that catch you out:

* `IN A,($FE)` puts **A** in the high byte of the address, not the
  port number. The half row is the one whose bit is 0, and the
  position of that bit (0 to 7) is the row index.
* the game may not want "any key". Cybernoid's menu waits for a digit
  from 1 to 6, which is row 3 bit 0. Pressing SPACE does nothing.

The tool is `msx/test/SpectrumTest.cs`; it writes the PNGs itself
without any image library.

**Then convert.** `msx/scripts/convert_spectrum.py` takes the raw
screen (6144 bytes of pixels plus 768 of attributes) and produces the
three tables of mode 2, ready to be put in the cartridge bank.

---

## 9. Pitfalls

Things that cost time while porting Cybernoid.

### The BIOS calls the INIT with a return address on the stack

If the INIT changes the stack pointer, that return address is lost.
**Never `RET` out of a cartridge INIT** unless the stack pointer is
left alone. The usual pattern is to end with a jump to the main loop.

### The workspace area is not RAM unless the BIOS put it there

`$F380-$FFFF` is the BIOS workspace. On a MSX1 it is RAM, but only
because the BIOS power-up copied the workspace code there. If a test
harness skips the power-up, the stack lands in ROM and the machine
behaves in impossible ways.

### `ENASLT` reads and writes `$FFFF`

The expanded-slot path of the BIOS routine reads `$FFFF` (where the
secondary slot register lives) and writes it back. On a plain slot
`$FFFF` is ordinary RAM. It is harmless, but it means `$FFFF` is
written during a slot switch.

### A wrong slot id breaks the whole machine

Passing a slot id of 0 makes ENASLT point every page at slot 0, which
unmaps the cartridge and the BIOS at the same time. The symptom is
the CPU running off into RAM.

**But usually ENASLT is not needed at all.** The BIOS already maps
pages 1 and 2 of the cartridge slot when it detects a two window
mapper. Call ENASLT only after checking that page 2 really points
somewhere else.

### The carry flag matters in the BIOS helpers

`RSLREG` is `IN A,($A8); RET` and does not touch the flags, so the
carry that `RSLREG` returns with is whatever the caller had. The
BIOS's own slot switching code depends on it. Clear the carry before
calling a BIOS helper that shifts.

### The slot id has to be built the way the BIOS expects

`ENASLT` takes a **slot id** in A, not a plain slot number:

```
FxxxSSPP   bit 7 = the slot is expanded
           bits 3-2 = the secondary slot
           bits 1-0 = the primary slot
```

The primary slot number comes from the slot register (the slot of
page 1, since that is where the BIOS put the cartridge), the
expanded flag from `EXPTBL` at `$FCC1` and the secondary slot from
`SLTTBL` at `$FCC5`. Getting this wrong is what made the first
version of this ROM remap the BIOS away.

### A wrong VDP register value can disable the display

VDP register 1 bit 6 is the display enable. Leaving it at 0 gives a
black screen even though everything else is right.

### The sprite pattern table and the name table overlap easily

In mode 2 the name table is 768 bytes. With `R2 = $06` it sits at
`$1800-$1AFF`, and the sprite attributes are at `$1B00`, so they
overlap. With `R2 = $50` the name table is at `$3800`, which is where
the sprite patterns want to be. Pick the layout first and then derive
`R2` to `R6` from it.

### The pattern and colour tables are 768 entries, not 256

A character code only reaches 255, so the 768 pattern slots are
divided between the three blocks. A conversion that writes the name
table as `0, 1, 2, ... 767` is wrong: it has to be the sequence 0 to
255 repeated three times, so that the code of a cell is
`(row % 8) * 32 + column`.

### Writing a register number as the data

Selecting a PSG register and writing its value are two different
`OUT`s:

```
        ld   a, $09                 ; select register 9
        out  (PSG_REG), a          ; OUT ($A0),A
        xor  a                     ; <-- the value to write
        out  (PSG_DAT), a          ; OUT ($A1),A
```

Without the `XOR A` the register number ends up in the data port, and
the channel is left with volume 9 instead of 0. The PSG then makes a
noise that sounds like a machine gun, and it is easy to miss because
the screen looks fine.

### The EXPTBL byte is masked, not merged

To build the slot id for `ENASLT`:

```
        and  $80                   ; the "expanded" bit of EXPTBL
        or   c                     ; the primary slot
```

`OR` with the whole EXPTBL byte works by accident (the low bits of
the byte get masked off later by `AND $0C`) and breaks the moment the
table holds something else. `AND $80` is what the reference
implementations do.

### A wrong slot id breaks the whole machine

`ENASLT` with a slot id of 0 maps page 2 to the BIOS, and the
cartridge's assets disappear with it. The BIOS's interrupt handler
keeps running, so the machine looks alive while nothing works. When
the assets are not visible, check the slot id before anything else.

### Clearing the VRAM outside the blanking does nothing

The loop that writes 16 KB to the VRAM in one go works in an emulator
that does not model the VRAM access restriction, and on real hardware
almost every write is discarded. Spread it over the frames and do it
from the vblank handler.

### HALT with the interrupts disabled never wakes up

The obvious way to wait for the frame is `EI` / `HALT`. With the
interrupts disabled the Z80 does not leave the halt state when an
interrupt is requested, so a cartridge that does `DI` at the start
and forgets to `EI` freezes.

### The Spectrum colour numbers are not the MSX ones

| Spectrum | MSX | Value |
|----------|-----|-------|
| 0 black | black | 1 |
| 1 blue | medium blue | 8 |
| 2 red | light red | 9 |
| 3 magenta | magenta | 13 |
| 4 green | medium green | 2 |
| 5 cyan | light blue | 5 (no cyan on MSX) |
| 6 yellow | yellow | 14 |
| 7 white | white | 15 |

The MSX palette is 0 transparent, 1 black, 2 medium green, 3 light
green, 4 dark blue, 5 light blue, 6 dark red, 7 medium grey,
8 medium blue, 9 light red, 10 dark grey, 11 light grey, 12 dark
green, 13 magenta, 14 yellow, 15 white.

### The Spectrum attribute byte has to be transposed

Spectrum: `ink` in bits 0-2, `paper` in bits 3-5.
MSX colour entry: `paper` in bits 0-3, `ink` in bits 4-7.

So the byte has to be split, both halves remapped and put back
together. A 256 entry lookup table built at start-up is the cheapest
way to do it.

### The game's own stack pointer is often below the workspace

Cybernoid does `LD SP,$0000`, so its stack grows down from the top of
the address space and overwrites the low RAM. That is fine on the
Spectrum, where the low RAM is the screen. On the MSX, `$0000-$3FFF`
is the BIOS, so the stack would land in ROM. This is another reason a
binary port has to run in all-RAM mode.

### The Z80 disassembler in the tool is not always in sync

When scanning for absolute references, a linear disassembly drifts as
soon as it hits data. Always start the scan at a known code entry
point, and never at a data block.
