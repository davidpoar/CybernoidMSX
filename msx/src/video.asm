;==========================================================
; Cybernoid MSX - Video layer
;----------------------------------------------------------
; Converts the Spectrum screen format into MSX VDP Graphics Mode 2.
;
; Spectrum screen (must live in MSX RAM):
;   $4000-$57FF : pixels, 768 cells of 8 bytes, 1 bit per pixel (MSB = left)
;   $5800-$5AFF : attributes, 768 bytes (one per cell)
;
; MSX VDP Graphics Mode 2 layout used here:
;   VRAM $0000-$17FF : Character Pattern Table (768 patterns x 8 bytes)
;   VRAM $2000-$37FF : Colour Table (768 bytes, 1:1 with the pattern table)
;   VRAM $3800-$3AFF : Name Table (768 character indices)
;
; The pattern table is split into three 2KB blocks because character
; codes are only 8 bit:
;   name table rows  0-7  use pattern block 0 ($0000-$07FF)
;   name table rows  8-15 use pattern block 1 ($0800-$0FFF)
;   name table rows 16-23 use pattern block 2 ($1000-$17FF)
; Within a block the character code is simply the column number.
;
; Row layout differs between the two systems:
;   Spectrum row r at $4000 + (r/8)*$100 + (r%8)*$20
;   MSX    row r at $0000 + (r/8)*$800 + (r%8)*$08
; so each row is copied separately (32 cells = 256 bytes).
;==========================================================

        INCLUDE "config.asm"

VDP_DATA   EQU $98
VDP_CMD    EQU $99

; Colour conversion table: 256 bytes (Spectrum attribute -> MSX colour)
COLTAB     EQU DATA_COLTAB

; Row sync cursor
sync_row   EQU DATA_SYNC_ROW

;----------------------------------------------------------
        org VIDEO_BASE

        PUBLIC MSX_VIDEO_INIT
        PUBLIC MSX_VIDEO_SYNC
        PUBLIC MSX_VIDEO_SYNC_ROWS

;----------------------------------------------------------
; VDP_SETREG - write a VDP mode register
;----------------------------------------------------------
; Input: B = value, C = register number
;----------------------------------------------------------
VDP_SETREG:
        LD   A, B
        OUT  (VDP_CMD), A
        LD   A, C
        OR   $80
        OUT  (VDP_CMD), A
        RET

;----------------------------------------------------------
; VDP_SETADDR - set the VDP write address
;----------------------------------------------------------
; Input: H = high byte, L = low byte
;----------------------------------------------------------
VDP_SETADDR:
        LD   A, L
        OUT  (VDP_CMD), A
        LD   A, H
        OR   $40
        OUT  (VDP_CMD), A
        RET
;----------------------------------------------------------
; MSX_VIDEO_INIT
;----------------------------------------------------------
MSX_VIDEO_INIT:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL

        ; --- VDP registers ---
        LD   B, $02
        LD   C, 0
        CALL VDP_SETREG         ; R0: graphics mode 2
        LD   B, $A0
        LD   C, 1
        CALL VDP_SETREG         ; R1: 16K VRAM + IRQ enabled
        LD   B, $0E
        LD   C, 2
        CALL VDP_SETREG         ; R2: name table at $3800
        LD   B, $C0
        LD   C, 3
        CALL VDP_SETREG         ; R3: colour table at $2000
        LD   B, $00
        LD   C, 4
        CALL VDP_SETREG         ; R4: pattern table at $0000
        LD   B, $76
        LD   C, 5
        CALL VDP_SETREG         ; R5: sprite attributes at $1B00
        LD   B, $03
        LD   C, 6
        CALL VDP_SETREG         ; R6: sprite patterns at $1800
        LD   B, $F1
        LD   C, 7
        CALL VDP_SETREG         ; R7: border black

        CALL BUILD_COLOUR_TABLE
        CALL BUILD_NAME_TABLE

        XOR  A
        LD   (sync_row), A

        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RET

;----------------------------------------------------------
; BUILD_COLOUR_TABLE
;----------------------------------------------------------
; 256-entry table at COLTAB mapping a Spectrum attribute byte to
; an MSX colour table entry (low nibble = paper, high nibble = ink).
;
; Spectrum attribute byte:
;   bits 0-2 : ink colour
;   bits 3-5 : paper colour
;   bit 6    : flash   (ignored)
;   bit 7    : bright ink
;
; Spectrum -> MSX colour:
;   0 black   -> 1  black
;   1 blue    -> 8  medium blue
;   2 red     -> 9  light red
;   3 magenta -> 13 magenta
;   4 green   -> 2  medium green
;   5 cyan    -> 5  light blue   (MSX has no cyan)
;   6 yellow  -> 14 yellow
;   7 white   -> 15 white
;
; Bright ink (bit 7) upgrades blue -> light blue, green -> light green.
;----------------------------------------------------------
BUILD_COLOUR_TABLE:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL

        LD   HL, COLTAB
        LD   D, 0                ; attribute value 0-255
ct_loop:
        ; --- paper colour (bits 3-5) ---
        LD   A, D
        AND  $38
        RRCA
        RRCA
        RRCA
        CALL STM_COLOUR
        LD   C, A                ; C = paper (MSX)

        ; --- ink colour (bits 0-2) ---
        LD   A, D
        AND  $07
        CALL STM_COLOUR
        LD   B, A                ; B = ink (MSX)

        ; --- bright ink (bit 7) ---
        LD   A, D
        BIT  7, A
        JR   Z, ct_no_bright
        LD   A, B
        CP   8
        JR   NZ, ct_b2
        LD   B, 5                ; bright blue -> light blue
        JR   ct_no_bright
ct_b2:
        CP   2
        JR   NZ, ct_no_bright
        LD   B, 3                ; bright green -> light green
ct_no_bright:

        LD   A, B
        RLCA
        RLCA
        RLCA
        RLCA
        OR   C
        LD   (HL), A

        INC  HL
        INC  D
        JR   NZ, ct_loop

        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RET

;----------------------------------------------------------
; STM_COLOUR - Spectrum colour code -> MSX colour code
;----------------------------------------------------------
; Input:  A = Spectrum colour 0-7
; Output: A = MSX colour code
;----------------------------------------------------------
STM_COLOUR:
        CP   $01
        JR   C, stm_black       ; 0 -> black
        CP   $02
        JR   Z, stm_blue        ; 1 -> medium blue
        CP   $03
        JR   Z, stm_red         ; 2 -> light red
        CP   $04
        JR   Z, stm_magenta     ; 3 -> magenta
        CP   $05
        JR   Z, stm_green       ; 4 -> medium green
        CP   $06
        JR   Z, stm_cyan        ; 5 -> light blue
        CP   $07
        JR   Z, stm_yellow      ; 6 -> yellow
        LD   A, 15              ; 7 -> white
        RET
stm_black:   LD   A, 1
        RET
stm_blue:    LD   A, 8
        RET
stm_red:     LD   A, 9
        RET
stm_magenta: LD   A, 13
        RET
stm_green:   LD   A, 2
        RET
stm_cyan:    LD   A, 5
        RET
stm_yellow:  LD   A, 14
        RET

;----------------------------------------------------------
; BUILD_NAME_TABLE
;----------------------------------------------------------
; Fills VRAM $3800 with 768 character indices.
; Each row of 32 cells gets the indices 0..31 (the column number).
;----------------------------------------------------------
BUILD_NAME_TABLE:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL

        LD   H, $38
        LD   L, $00
        CALL VDP_SETADDR

        LD   D, 24
nt_row:
        XOR  A
        LD   E, 32
nt_col:
        OUT  (VDP_DATA), A
        INC  A
        DEC  E
        JR   NZ, nt_col
        DEC  D
        JR   NZ, nt_row

        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RET

;----------------------------------------------------------
; MSX_VIDEO_SYNC - sync the whole screen
;----------------------------------------------------------
MSX_VIDEO_SYNC:
        PUSH AF
        LD   A, 24
        CALL MSX_VIDEO_SYNC_ROWS
        POP  AF
        RET

;----------------------------------------------------------
; MSX_VIDEO_SYNC_ROWS
;----------------------------------------------------------
; Syncs A screen rows starting at the rotating cursor.
; Input:  A = number of rows (1-24)
; Output: A = next row to sync
;----------------------------------------------------------
MSX_VIDEO_SYNC_ROWS:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL

        LD   C, A                ; rows to sync
        LD   B, 0                ; rows done

svr_loop:
        LD   A, (sync_row)
        CALL SYNC_ONE_ROW

        LD   A, (sync_row)
        INC  A
        CP   24
        JR   C, svr_nowrap
        XOR  A
svr_nowrap:
        LD   (sync_row), A

        INC  B
        LD   A, B
        CP   C
        JR   NZ, svr_loop        ; keep going until B == C

        LD   A, (sync_row)
        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RET

;----------------------------------------------------------
; SYNC_ONE_ROW
;----------------------------------------------------------
; Input: A = screen row (0-23)
;
; Spectrum layout for cell (col, row):
;   pixels : $4000 + (row/8)*$100 + (row%8)*$20 + col*8
;   attrib : $5800 + row*32        = $5800 + (row/8)*$100 + (row%8)*$20
;
; MSX layout for cell (col, row):
;   pattern : (row/8)*$800 + (row%8)*$100 + col*8
;   colour  : $2000 + (row/8)*$800 + (row%8)*$100 + col*8
;
; A whole row is 32 cells = 256 bytes = $100, so both the source
; and the destination are 256-byte aligned and one LDIR-like loop
; per row is enough.
;----------------------------------------------------------
SYNC_ONE_ROW:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL

        LD   E, A                ; E = row
        ; --- blk = row >> 3 (row is 0-23, so the top two bits) ---
        LD   A, E
        AND  $18
        RRA
        RRA
        RRA
        LD   D, A                ; D = blk (0-2)
        ; --- line = row & 7 ---
        LD   A, E
        AND  $07
        LD   C, A                ; C = line

        ; ==================================================
        ; --- copy the pixel row (256 bytes) ---
        ; source = $4000 + blk*$100 + line*$20
        ; ==================================================
        LD   A, D
        ADD  A, $40
        LD   H, A                ; H = $40 + blk
        LD   A, C
        RLCA
        RLCA
        RLCA
        RLCA
        RLCA
        LD   L, A                ; L = line*$20
        ; HL = source

        ; dest = blk*$800 + line*$100
        ;      = (blk*8 + line) * $100
        PUSH HL                  ; save the source pointer
        LD   A, D
        RLCA
        RLCA
        RLCA                    ; blk*8
        ADD  A, C                ; + line
        LD   H, A                ; high byte of the address
        LD   L, 0                ; the low byte is always 0
        CALL VDP_SETADDR
        POP  HL                  ; restore the source pointer

        LD   B, 64
cp_loop:
        LD   A, (HL)
        OUT  (VDP_DATA), A
        INC  HL
        LD   A, (HL)
        OUT  (VDP_DATA), A
        INC  HL
        LD   A, (HL)
        OUT  (VDP_DATA), A
        INC  HL
        LD   A, (HL)
        OUT  (VDP_DATA), A
        INC  HL
        DJNZ cp_loop

        ; ==================================================
        ; --- copy the colour row (32 bytes, converted) ---
        ; source = $5800 + row*32
        ; dest   = $2000 + blk*$800 + line*$100
        ; ==================================================
        LD   A, D
        ADD  A, $58
        LD   H, A                ; H = $58 + blk
        LD   A, C
        RLCA
        RLCA
        RLCA
        RLCA
        RLCA
        LD   L, A                ; L = line*$20
        ; HL = $5800 + row*32 (source)

        PUSH HL
        LD   A, D
        RLCA
        RLCA
        RLCA                    ; blk*8
        ADD  A, C                ; + line
        ADD  A, $20              ; + the colour table base
        LD   H, A                ; high byte of the address
        LD   L, 0                ; the low byte is always 0
        CALL VDP_SETADDR
        POP  HL                  ; restore the source pointer

        LD   B, 32
cc_loop:
        LD   A, (HL)
        INC  HL
        LD   C, A
        LD   E, A
        LD   D, 0
        LD   HL, COLTAB
        ADD  HL, DE
        LD   A, (HL)
        OUT  (VDP_DATA), A
        DJNZ cc_loop

        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RET

        end
