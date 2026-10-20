# Cybernoid - the tape image and the memory map

## The tape

`Cybernoid.tzx` holds nine blocks, all "standard speed data":

| Block | Bytes | What |
|-------|-------|------|
| 1 | - | text description: "Created with Ramsoft MakeTZX" |
| 2 | 19 | BASIC program header |
| 3 | 83 | the BASIC program, 81 bytes |
| 4 | 19 | CODE header, 768 bytes at `$FC00` |
| 5 | 770 | the loader code, 768 bytes plus flag and checksum |
| 6 | 19 | custom header, type 42 |
| 7 | 4407 | data block, 4405 bytes plus flag and checksum |
| 8 | 19 | custom header, type 42 |
| 9 | 39678 | the main game, 39676 bytes plus flag and checksum |

The BASIC program is a single line:

```
10 BORDER 0: PAPER 0: INK 7: CLEAR 24835: LOAD ""CODE : RANDOMIZE USR 64512
```

`CLEAR 24835` moves RAMTOP so the loader can live at the top of the
memory. `RANDOMIZE USR 64512` (`$FC00`) runs the loader.

## The two custom headers

Blocks 6 and 8 are not standard Spectrum headers, they use type 42.
The layout is the standard one, but the type byte differs:

```
byte 0       $00        flag
byte 1       $2A        type 42 (custom)
bytes 2-11   name       "cybernoid 5" / "cybernoid "
bytes 12-13  length     little endian
bytes 14-15  address    little endian
```

| Header | Length | Address |
|--------|--------|---------|
| block 6 | `$1135` = 4405 | `$8000` |
| block 8 | `$9AFC` = 39676 | `$6104` |

The custom loader reads these headers and uses the length and the
address from them, so the data lands exactly where the game expects
it.

## The loader

The loader occupies `$FC00-$FFFF` (768 bytes) and decrypts itself
before doing anything else.

### The self decryption

```
$FC00: LD BC,$029D      ; 669 bytes
$FC03: LD HL,$FC13      ; the encrypted region starts here
$FC06: LD DE,$FC14      ; one byte further on
$FC09: LD A,(DE)
$FC0A: XOR (HL)
$FC0B: LD (HL),A
$FC0C: INC HL
$FC0D: INC DE
$FC0E: DEC BC
$FC0F: LD A,B
$FC10: OR C
$FC11: JR NZ,$FC09
$FC13: JP $FE3A        ; continues at the decrypted code
```

It is a rolling XOR: each byte is xored with the byte that follows
it. The last byte of the region is xored with the first byte of the
copy.

The region that gets decrypted is `$FC13` to `$FEBF` (669 bytes). The
code after `$FC13` is:

```
$FE3A: DI
$FE3B: LD HL,$5800
$FE3E: LD DE,$5801
$FE41: LD BC,$02FF
$FE44: LDIR                 ; clear the attribute area
$FE46: LD HL,$4000
$FE49: LD B,$C0
$FE4B: LD (IX),H
$FE4E: LD (IY),L
$FE51: CALL $FE7E
...
$FE5F: ...                  ; a 31 byte stub
```

### What the loader does

1. decrypts itself
2. clears the attribute area at `$5800-$5AFF`
3. calls `$FE7E` twice, which reads a header and then its data block
   from the tape, using the address and the length from the header
4. copies a 31 byte stub from `$FE5F` to `$5B00` and jumps to it

The stub at `$FE5F` is the part that rearranges the memory:

```
LD   HL,$FBFF
LD   DE,$FFFF
LD   BC,$9AFC
LDDR                    ; copy $6104-$FBFF to $6504-$FFFF
LD   HL,$6104
LD   DE,$6105
LD   BC,$03FF
LDIR                    ; clear $6104-$6503
LD   SP,$61A8
EI
JP   $6504               ; the game starts here
```

**The LDDR is the key to the whole memory map.** It copies the
source range `$6104-$FBFF` to the destination range `$6504-$FFFF`,
so:

```
destination $6504-$FFFF  <-  source $6104-$FBFF
```

Everything the game touches at run time is in that destination
range, and every absolute address inside the game is one of those.

### The tape reading routine

`$FE7E` reads a custom header and then its data:

```
$FE7E: XOR A
$FE7F: LD ($FC1A),A
$FE82: LD IX,$FC21        ; the header buffer
$FE86: LD DE,$0011        ; 17 bytes
$FE89: XOR A
$FE8A: SCF
$FE8B: CALL $FC8A         ; read the header
$FE8E: JR NC,$FE7E        ; retry until it works
$FE90: LD A,($FC21)       ; the type byte
$FE93: CP $2A             ; must be 42
$FE95: JR NZ,$FE7E
$FE97: CALL $FE0F
$FE9A: LD A,1
$FE9C: LD ($FC1A),A
$FE9F: LD IX,($FC2E)      ; the address from the header
$FEA3: LD DE,($FC2C)      ; the length from the header
$FEA7: LD A,$FF
$FEA9: SCF
$FEAA: CALL $FC8A         ; read the data
$FEAD: JR NC,$FE7E
$FEAF: RET
```

The header is read into `$FC21`, so:
- `$FC2C`/`$FC2D` = the length
- `$FC2E`/`$FC2F` = the address

That is bytes 11-12 and 13-14 of the header, which is exactly where
the standard Spectrum header keeps them.

## The memory map once the game is running

This is the state after the LDDR, and it is what the game sees.

| Range | Size | What |
|-------|------|------|
| `$4000-$57FF` | 6144 | screen pixels, 768 cells of 8 bytes, 1 bit per pixel |
| `$5800-$5AFF` | 768 | screen attributes, one per cell |
| `$5B00-$5DFF` | 768 | a copy of the attributes |
| `$5F00-$62FF` | 1024 | sprite data and tables |
| `$6300-$63BF` | 192 | screen address table A, one entry per scan line |
| `$6400-$64BF` | 192 | screen address table B, one entry per scan line |
| `$6504-$FFFF` | 39676 | the game code and data |

The screen address tables hold the address of each of the 192 screen
lines, so the game can find a line without doing the
`(row/8)*$100 + (row%8)*$20` arithmetic every time. `$674C`
increments a line pointer, `$6779` computes the address of a cell
from a coordinate, and `$678F`, `$6799` and `$67A3` add the pixel,
attribute and attribute-copy bases.

### What the game writes where

The game writes to a lot of places inside `$6504-$FFFF`, so **that
whole range has to be writable RAM**. It uses:

| Address | What |
|---------|------|
| `$66A8` | a keyboard state buffer |
| `$67FE`, `$67FF` | two byte variables |
| `$6805`, `$6807` | the computed sprite position |
| `$680E`, `$6810` | the computed sprite position |
| `$6807`, `$6808` | the frame counter |
| `$696B`-`$696F` | scroll and sprite counters |
| `$6AEF`, `$6AF4` | object state |
| `$6B31`, `$6BBE`, `$6BD0`, `$6BFC` | object state |
| `$6C55`, `$6C56` | object state |
| `$711A` | the frame counter |
| `$711B` | a sound toggle |
| `$744B`, `$744C`, `$74E1` | object state |
| `$78D3` | a state byte |
| `$7B49`, `$7BFA` | state bytes |
| `$7E94` | a variable |
| `$65EA` | the frame counter |

`$5B00-$64BF` is also written to (the attribute copy, the sprite
data and the screen address tables), so page 1 has to be RAM as well.

**This is why the binary port needs all-RAM mode**: the game needs
`$4000-$7FFF` to be writable, and on a MSX that range is cartridge
ROM.
