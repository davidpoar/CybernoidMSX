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

The TMS9918 gives each **group of eight character codes** one set of
eight line colours. The colour table entry `i` holds the colours of
pixel line `i` of the pattern in slot `i`: the low nibble is the
colour of the 0 pixels and the high nibble the colour of the 1
pixels.

Because the character code is only 8 bits, the 768 slots of the
pattern table are split into three 2 KB blocks:

```
name table rows  0-7  use pattern block 0  ($0000-$07FF)
name table rows  8-15 use pattern block 1  ($0800-$0FFF)
name table rows 16-23 use pattern block 2  ($1000-$17FF)
```

and inside a block the character code is just the column number. So
the name table is 24 rows of `0, 1, 2, ... 31`, and the pattern
slot of cell (col, row) is:

```
slot = (row/8)*$800 + (row%8)*$100 + col*8
```

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

## The limitation of mode 2

A mode 2 colour table entry covers a **group of eight character
codes**, and all of them share the same eight line colours. The
Spectrum has a separate ink and paper for **every cell**.

So a faithful conversion is only possible if the cells that share a
character code also share their colours. For a game where the
background is one colour and the moving objects are another, that
works. For a game where every cell is a different colour, it does
not.

This is what forces the choice between:

* **converting the bitmap** and accepting that the colour table can
  only hold 32 distinct colour groups, with the moving objects drawn
  as sprites on top
* **rewriting the drawing** with native TMS9918 sprites, which give
  a colour per sprite

## The timing

Copying 6 KB of pattern data and 768 bytes of colour data to the
VDP is slow. The MSX1 VDP needs a minimum of 12 T states between
accesses, and 24 in practice.

The way to do it is to copy during **VBLANK**, using the VDP frame
interrupt, and to use `OUTI`/`OTIR` when the data is contiguous,
because they are much faster than a byte at a time loop.

The VDP status register (`$99`) has the frame flag in bit 7, which
is set during VBLANK.

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

The native port (`msx/build/cybernoid.rom`) will use the same
pattern and colour table layout, but the data comes from the
converted assets in the cartridge banks instead of from a live
Spectrum screen buffer.
