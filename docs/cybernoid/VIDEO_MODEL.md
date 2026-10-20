# Cybernoid - how the Spectrum screen maps onto the MSX

## The Spectrum screen

```
$4000-$57FF   6144 bytes of pixels
               768 cells of 8x8, one bit per pixel, MSB = leftmost
               the 24 lines are interleaved in blocks of 8
$5800-$5AFF   768 bytes of attributes, one per cell
               bits 0-2 = ink colour
               bits 3-5 = paper colour
               bit 6    = flash
               bit 7    = bright ink
```

The address of cell (col, row):

```
pixels     = $4000 + (row/8)*$100 + (row%8)*$20 + col*8
attributes = $5800 + row*32 + col
```

The interleaving is the awkward part: line 0 is at `$4000`, line 1 at
`$4020`, line 2 at `$4040` and so on, and only after 8 lines does the
base jump by `$100`.

## The MSX VDP in graphics mode 2

```
VRAM $0000-$17FF   pattern generator, 768 cells of 8 bytes
VRAM $1800-$1AFF   name table, 768 indices
VRAM $2000-$37FF   colour table
VRAM $3800-$3FFF   sprite patterns
VRAM $1B00-$1FFF   sprite attributes
```

The registers that produce that layout:

```
R0 = $02   graphics mode
R1 = $E0   16K VRAM, IRQ on, display on
R2 = $06   name table at $1800
R3 = $FF   colour table at $2000
R4 = $03   pattern generator at $0000
R5 = $36   sprite attributes at $1B00
R6 = $07   sprite patterns at $3800
R7 = $F1   border colour
```

### The pattern table and the colour table are paired

The colour table has an **exact byte to byte mapping with the pattern
table**: the entry at the same offset gives the colours of that pixel
line, the low nibble for the 0 pixels and the high nibble for the 1
pixels.

Because the character code is only 8 bits, the 6 KB of the pattern
table are split into three 2 KB blocks, one per third of the screen:

```
name table rows  0-7  use pattern block 0  ($0000-$07FF)
name table rows  8-15 use pattern block 1  ($0800-$0FFF)
name table rows 16-23 use pattern block 2  ($1000-$17FF)
```

The name table is initialised with the character code sequence 0 to 255
repeated three times, so the code of a cell is `(row % 8) * 32 + col`
and the address of its pattern and its colours is:

```
pattern = (row/8)*$800 + (row%8)*$100 + col*8
colour  = $2000 + (row/8)*$800 + (row%8)*$100 + col*8
```

With that layout every cell has its **own** eight colour bytes, so the
Spectrum ink and paper can be reproduced exactly, cell by cell. That
is what the native port does.

## The conversion

### The pixels need no conversion

A Spectrum cell is 8 bytes of 1 bit per pixel with the MSB on the
left. A TMS9918 pattern is exactly the same. So the 8 bytes of a
Spectrum cell can go straight into a pattern slot.

### The rows have to be de-interleaved

The Spectrum stores 8 lines `$20` apart, MSX stores them `$100`
apart inside a block. So a row is copied separately:

```
for each row 0..23:
    src = $4000 + (row/8)*$100 + (row%8)*$20
    dst = $0000 + (row/8)*$800 + (row%8)*$100
    copy 256 bytes from src to dst
```

### The attributes have to be transposed and remapped

The Spectrum packs ink and paper into one byte, the MSX wants them
in two nibbles of a different table, and the colour numbers are
different.

A 256 entry lookup table built at start-up is the cheapest way:

| Spectrum attribute | Meaning | MSX colour entry |
|-------------------|---------|------------------|
| bits 0-2 = 0 | black ink | ink = 1 (black) |
| bits 0-2 = 1 | blue ink | ink = 8 (medium blue) |
| bits 0-2 = 2 | red ink | ink = 9 (light red) |
| bits 0-2 = 3 | magenta ink | ink = 13 (magenta) |
| bits 0-2 = 4 | green ink | ink = 2 (medium green) |
| bits 0-2 = 5 | cyan ink | ink = 5 (light blue) |
| bits 0-2 = 6 | yellow ink | ink = 14 (yellow) |
| bits 0-2 = 7 | white ink | ink = 15 (white) |
| bits 3-5 | the paper colour | paper = the same mapping |

The MSX palette for reference:

```
0 transparent   1 black         2 medium green   3 light green
4 dark blue     5 light blue    6 dark red       7 medium grey
8 medium blue   9 light red    10 dark grey     11 light grey
12 dark green   13 magenta     14 yellow        15 white
```

There is no cyan on the MSX, so Spectrum cyan becomes light blue.

## The timing

Copying 6 KB of pattern data and 6 KB of colour data to the VDP is
slow. The MSX1 VDP needs a minimum of 12 T states between accesses,
and 24 in practice.

The way to do it is to copy during **VBLANK**, using the VDP frame
interrupt. On a real MSX the VDP only allows the VRAM to be written
while the vertical blanking is active, so a full 13 KB of screen data
cannot be copied in one go: it has to be spread over several frames.

The VDP status register (`$99`) has the frame flag in bit 7, which
is set during VBLANK.

## The vblank handler of the native port

The MSX1 BIOS calls the address in `$FD9F` (which is RAM on page 3)
every time the VDP raises the interrupt, and `$FD9A` on every
interrupt. Putting a `JP` in `$FD9F` is the standard way for a
cartridge to get control at the start of the vertical blanking.

The BIOS has already saved every register when it calls the hook, but
it uses `A` right after the call, so the handler has to preserve it.

The native port copies **one page of 256 bytes per frame** from the
cartridge bank to the VRAM, which takes about 2.4 ms and fits
comfortably inside the blanking period. The whole screen takes 51
frames, about one second.

## What the Cybernoid port does

The binary port (`msx/build/cybernoid.com`) converts the whole
screen every time `MSX_VIDEO_SYNC` is called:

```
for each row 0..23:
    copy the 256 pixel bytes to the pattern table
    copy the 32 attribute bytes, converted, to the colour table
```

The conversion is incremental: `MSX_VIDEO_SYNC_ROWS` takes a number
of rows and a rotating cursor, so the work can be spread over
several frames. The name table is static and is written once.

The native port (`msx/build/cybernoid.rom`) uses the same pattern and
colour table layout, but the data comes from the
converted assets in the cartridge banks instead of from a live
Spectrum screen buffer.
