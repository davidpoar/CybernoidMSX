# Cybernoid - the I/O routines

Every place where the game talks to the Spectrum hardware, with the
address it happens at.

## Keyboard

Four places read the keyboard through port `$FE`. All of them are
`LD A,nn` + `IN A,($FE)`, where `nn` selects the row.

| Address | Row | What it does |
|---------|-----|--------------|
| `$65ED` | `$FE` | row 0: CAPS, Z, X, C, V |
| `$65F4` | `$7F` | row 7: SPACE, SYM, M, N, B |
| `$660D` | `$F7` | row 3: 1, 2, 3, 4, 5 |
| `$7B4C` | `$F7` | row 3, read in the game loop |

### The routine at `$662B` - press any key

```
$662B: PUSH BC
$662C: PUSH HL
$662D: LD HL,$6649       ; the key code table
$6630: LD D,$FE          ; the first row
$6632: LD A,D
$6633: IN A,($FE)
$6635: LD E,1
$6637: LD B,5
$6639: RRCA              ; the clear bit ends up in the carry
$663A: JR NC,$6645       ; not set: this key is not pressed
$663C: INC HL            ; set: the next key code
$663D: SLA E
$663F: DJNZ $6639
$6641: RLC D             ; the next row
$6643: JR C,$6632
$6645: LD A,(HL)         ; the key code
$6646: POP HL
$6647: POP BC
$6648: RET
```

It walks the 8 rows, counts the pressed keys and returns the
character from the table at `$6649`. The table is the Spectrum key
order, with `$01` for "no key":

```
$6649: 01                no key
$664A: 5A 'Z'  58 'X'  43 'C'  56 'V'  41 'A'  53 'S'  44 'D'  46 'F'
$6653: 47 'G'  51 'Q'  57 'W'  45 'E'  52 'R'  54 'T'
$665C: 31 '1'  32 '2'  33 '3'  34 '4'  35 '5'
$6661: 30 '0'  39 '9'  38 '8'  37 '7'  36 '6'
$6666: 50 'P'  4F 'O'  49 'I'  55 'U'  59 'Y'
$666B: 0D RET  4C 'L'  4B 'K'  4A 'J'  48 'H'  20 ' '
$6671: 02                (symbol shift)
$6672: 4D 'M'  4E 'N'  42 'B'
```

### The routine at `$65EB` - the shift keys

```
$65EB: LD A,$FE
$65ED: IN A,($FE)
$65EF: AND 1             ; CAPS SHIFT
$65F1: RET NZ
$65F2: LD A,$7F
$65F4: IN A,($FE)
$65F6: AND 2             ; SYMBOL SHIFT
$65F8: RET NZ
$65F9: LD BC,$01F4
$65FC: CALL $676A
$65FF: CALL $6672        ; is a key pressed?
$6602: JR NZ,$65FF
$6604: CALL $662B        ; which key?
$6607: OR A
$6608: JR Z,$6604
$660A: RET
$660B: LD A,$F7
$660D: IN A,($FE)
$660F: AND $1F
$6611: RET NZ
$6612: JP $6504          ; back to the entry point
```

It waits for a key and then jumps back to `$6504`.

### The routine at `$7B4A` - the fire button

```
$7B4A: LD A,$F7
$7B4C: IN A,($FE)
$7B4E: AND $1F
$7B50: CP $1F            ; nothing pressed?
$7B52: JR NZ,$7B59
$7B54: XOR A
$7B55: LD ($7B49),A
$7B58: RET
$7B59: LD D,A
$7B5A: LD A,($7B49)
$7B5D: OR A
$7B5E: RET NZ
$7B5F: INC A
$7B60: LD ($7B49),A
$7B63: LD A,D
$7B64: LD BC,$0500
$7B67: RRCA
$7B68: JR NC,$7B6E
$7B6A: INC C
$7B6B: DJNZ $7B67
$7B6D: RET
```

It reads row 3 (the number keys) and turns it into a value, with a
repeat delay. This is the fire button.

## Sound

### The beeper

One place writes to port `$FE` during the game loop, at `$651F`, in
the entry code:

```
$651F: OUT ($FE),A
```

and one more at `$8637`, inside the sound driver.

The port `$FE` bits:

| Bit | On read | On write |
|-----|---------|----------|
| 0-4 | keyboard row | border colour bits 0-2, MIC on bit 3, beeper on bit 4 |
| 5-7 | - | - |

### The sound driver at `$85BA`

The interrupt handler calls it, and it drives the beeper from a set
of tables:

| Address | What |
|---------|------|
| `$859A` | the sound channel state, one byte per channel |
| `$859B` | the "next event" counter |
| `$859E` | the current pitch, one byte per channel |
| `$85A4` | a control byte per channel |
| `$85A7` | the current volume, one byte per channel |
| `$8710` | the envelope data, 7 bytes per channel |

The routine at `$85BA` picks the next event, updates the pitch and
the volume, and then writes the beeper bit.

The data at `$7BAA` names the channels, which is handy when
decoding:

```
$7BAA: "BOMB    "
$7BBA: "MINES   "
$7BCA: "SHIELD  "
$7BDA: "BOUNCE  "
$7BEA: "SEEKER  "
```

### The interrupt handler at `$70D3`

The game sets up `IM 2` in the routine at `$70B4`:

```
$70B4: LD A,$C3
$70B6: LD ($FDFD),A
$70B9: LD HL,$70D3
$70BC: LD ($FDFE),HL
$70BF: LD HL,$FE00
$70C2: LD (HL),$FD
$70C4: LD DE,$FE01
$70C7: LD BC,$0101
$70CA: LDIR              ; fill $FE00-$FF00 with $FD
$70CC: IM 2
$70CE: LD A,$FE
$70D0: LD I,A
$70D2: RET
```

So the vector byte is `$FF`, the vector is at `$FEFF`, and it holds
`$FD` (the low byte of the handler address `$FDFD`). The `LDIR` fills
`$FE00-$FF00` with `$FD`, so `$FEFF` = `$FD` and `$FF00` = `$FD`, and
the handler is at `$FDFD`, which holds `JP $70D3`.

The handler itself:

```
$70D3: PUSH AF
$70D4: PUSH BC
$70D5: PUSH DE
$70D6: PUSH HL
$70D7: PUSH IX
$70D9: PUSH IY
$70DB: EXX
$70DC: EX AF,AF'
$70DD: PUSH AF
$70DE: PUSH BC
$70DF: PUSH DE
$70E0: PUSH HL
$70E1: LD HL,$711A       ; the frame counter
$70E4: INC (HL)
$70E5: LD A,($830A)
$70E8: OR A
$70E9: CALL Z,$EF3B
$70EC: LD A,($830A)
$70EF: OR A
$70F0: JR Z,$7109
$70F2: LD A,($8599)
$70F5: OR A
$70F6: JR NZ,$7106
$70F8: LD A,($711B)
$70FB: XOR 1
$70FD: LD ($711B),A
$7100: CALL Z,$85BA        ; the sound driver
$7103: JP $7109
$7106: CALL $EF38
$7109: POP HL
...                       ; restore and RETI
```

It counts the frames and drives the sound.

**On MSX this code works unchanged**, because it only writes to RAM
(`$FDFD`, `$FE00`, `$711A`...). The only thing needed on the MSX side
is to enable the VDP frame interrupt, which is VDP register 1 bit 5.

## Video

The game draws into the bitmap at `$4000-$57FF` and the attributes
at `$5800-$5AFF`. See [VIDEO_MODEL.md](VIDEO_MODEL.md) for how that
maps onto the MSX.

### The screen address tables

`$6300` and `$6400` hold 192 entries each: the address of every
screen line. The routine at `$674C` advances a line pointer:

```
$674C: INC H
$674D: LD A,H
$674E: AND 7
$6750: RET NZ            ; still inside the same 8 line block
$6751: LD A,L
$6752: ADD A,$20         ; next line is $20 further on
$6754: LD L,A
$6755: RET C
$6756: LD A,H
$6757: SUB 8
$6759: LD H,A
$675A: RET
```

and `$6779` computes the address of a cell from a coordinate:

```
$6779: PUSH AF
$677A: PUSH DE
$677B: LD A,D
$677C: AND $F8            ; the row, rounded down to 8
$677E: LD L,A
$677F: LD H,0
$6781: ADD HL,HL
$6782: ADD HL,HL
$6783: ADD HL,HL          ; *8
$6784: LD A,E
$6785: AND $7C            ; the column, rounded down to 8
$6787: RRCA
$6788: RRCA               ; /4
$6789: LD E,A
$678A: LD D,0
$678B: ADD HL,DE
$678C: POP DE
$678D: POP AF
$678E: RET
```

The three variants add the base:

| Routine | Adds |
|---------|------|
| `$678F` | `$5F00` (the sprite data) |
| `$6799` | `$5800` (the attributes) |
| `$67A3` | `$5B00` (the attribute copy) |

and the plain pixel address comes from `$6779` plus `$4000`.

### The screen clear at `$671E`

```
$671E: LD IX,$6300
$6722: LD IY,$6400
$6726: LD HL,$4000
$6729: LD B,$C0
$672B: LD (IX),H
$672E: LD (IY),L
$6731: CALL $674C
$6734: INC IX
$6736: INC IY
$6738: DJNZ $672B
$673A: RET
```

It fills the two address tables with the 192 screen line addresses.

### The sprite table at `$67EE`

Four bytes per sprite:

| Byte | What |
|------|------|
| 0 | X position |
| 1 | Y position |
| 2 | the sprite index, which selects the pattern and the colour |
| 3 | the frame or animation counter |

The routine at `$67B9` reads the entry and computes the screen
positions, storing them at `$6805`, `$6807`, `$680E` and `$6810`.

## Everything the game writes to

The list in [MEMORY_MAP.md](MEMORY_MAP.md) is the reason the binary
port needs 40 KB of RAM in one piece.
