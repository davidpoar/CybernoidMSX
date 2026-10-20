;==========================================================
; Cybernoid MSX - 64K ROM cartridge (ASCII16 mapper)
;----------------------------------------------------------
; File layout (64 KB = 4 banks of 16 KB):
;
;   file $0000-$3FFF (bank 0) -> MSX $4000-$7FFF
;        "AB" header, engine: INIT, VDP routines, bank switching,
;        music, input
;   file $4000-$7FFF (bank 1) -> MSX $8000-$BFFF (window)
;        assets: screen maps, tiles, sprites
;   file $8000-$BFFF (bank 2) -> MSX $8000-$BFFF (window)
;        assets: compressed data
;   file $C000-$FFFF (bank 3) -> MSX $8000-$BFFF (window)
;        assets: more data
;
; Mapper (ASCII16):
;   write to $6000-$6FFF : selects the bank visible at $4000-$7FFF
;   write to $7000-$7FFF : selects the bank visible at $8000-$BFFF
;   The engine always keeps bank 0 in the $4000 window.
;
; MSX RAM map:
;   $C000-$F37F : variables and buffers
;   $F380-$FFFF  : MSX workspace / stack top (SP = $F380)
;
; Header at $4000:
;   DB "AB"
;   DW INIT
;   DW 0          ; STATEMENT handler
;   DW 0          ; DEVICE handler
;   DW 0          ; TEXT pointer
;   DS 6,0        ; reserved
;==========================================================
        org $4000

;----------------------------------------------------------
; Cartridge header
;----------------------------------------------------------
        db  "AB"
        dw  INIT
        dw  0                   ; STATEMENT
        dw  0                   ; DEVICE
        dw  0                   ; TEXT
        ds  6,0                 ; reserved

;==========================================================
; Engine
;==========================================================

;----------------------------------------------------------
; BIOS entries used
;----------------------------------------------------------
RSLREG  equ $144C              ; A = primary slot register
WSLREG  equ $144F              ; A -> primary slot register
ENASLT  equ $0024              ; A = slot id, HL = address

;----------------------------------------------------------
; MSX I/O ports
;----------------------------------------------------------
PPI_A   equ $A8                ; primary slot register
PPI_C   equ $AA                ; keyboard row select
PPI_B   equ $A9                ; keyboard columns
VDP_CMD equ $99
VDP_DAT equ $98
PSG_REG equ $A0
PSG_DAT equ $A1

;----------------------------------------------------------
; RAM layout (page 3, $C000-$F37F)
;----------------------------------------------------------
cur_bank    equ $C000          ; bank currently in the $8000 window
our_slot    equ $C001          ; primary slot of this cartridge
slot_id     equ $C002          ; slot id (with the expander flag)
saved_reg   equ $C003          ; primary slot register at boot
kbd_state   equ $C010          ; 11 bytes of MSX keyboard state
spr_x       equ $C020          ; sprite X positions
spr_y       equ $C030
spr_pat     equ $C040
spr_col     equ $C050
spr_n       equ $C060          ; number of active sprites
vbl_flag    equ $C061          ; set by the VDP interrupt

;----------------------------------------------------------
; Bank registers of the ASCII16 mapper
;----------------------------------------------------------
BANK_A  equ $6000              ; selects the bank at $4000-$7FFF
BANK_B  equ $7000              ; selects the bank at $8000-$BFFF

;----------------------------------------------------------
; Screen 2 (Graphic II) VRAM layout
;   $0000-$0BFF  pattern generator (3 thirds of 1 KB)
;   $2000-$2BFF  colour table     (3 thirds of 1 KB)
;   $3800-$3AFF  name table       (768 bytes)
;   $1800-$1FFF  sprite patterns
;   $1B00-$1FFF  sprite attributes
;----------------------------------------------------------
PATTERN_BASE  equ $0000
COLOUR_BASE   equ $2000
NAME_BASE     equ $3800
SPRPAT_BASE   equ $1800
SPRATTR_BASE  equ $1B00

;----------------------------------------------------------
; VDP mode registers for SCREEN 2
;----------------------------------------------------------
VDP_R0  equ $02                ; graphics mode (M3=1)
VDP_R1  equ $A0                ; 16K VRAM, IRQ on, display on
VDP_R2  equ $50                ; name table at $3800
VDP_R3  equ $C0                ; colour table at $2000
VDP_R4  equ $00                ; pattern table at $0000
VDP_R5  equ $76                ; sprite attributes at $1B00
VDP_R6  equ $03                ; sprite patterns at $1800
VDP_R7  equ $F1                ; border colour 1

;==========================================================
; INIT - called by the MSX BIOS at boot
;==========================================================
INIT:
        di
        ld   sp, $F380             ; stack at the end of the RAM

        ; --- find our own slot -----------------------------------
        ; The BIOS has our ROM mapped on page 1, so the primary
        ; slot of page 1 is us.
        call RSLREG                ; A = primary slot register
        ld   (saved_reg), a
        and  $0C                    ; page 1 slot bits
        rrca
        rrca
        ld   (our_slot), a

        ; If our slot is expanded, EXPTBL holds $80 for it and the
        ; slot id must include the secondary slot number.
        ld   a, (our_slot)
        ld   e, a
        ld   d, 0
        ld   hl, $FCC1               ; EXPTBL
        add  hl, de
        ld   a, (hl)
        or   (our_slot)
        ld   (slot_id), a

        ; --- switch page 2 ($8000-$BFFF) to our cartridge ------
        ; This also disables the MSX BASIC ROM that normally
        ; occupies page 2.
        ld   a, (slot_id)
        ld   hl, $8000
        call ENASLT

        ; --- make sure page 3 is RAM ---------------------------
        ; The workspace area at $F380 must be reachable, so page 3
        ; has to point at the slot that holds the main RAM.
        in   a, (PPI_A)
        and  $3F                    ; keep pages 0, 1 and 2
        or   $C0                    ; page 3 -> slot 3
        out  (PPI_A), a

        ; --- bank registers -------------------------------------
        xor  a
        out  (BANK_A), a            ; bank 0 at $4000 (the engine)
        ld   a, 1
        out  (BANK_B), a            ; bank 1 at $8000
        ld   a, 1
        ld   (cur_bank), a

        ; --- hardware ------------------------------------------
        call VDP_INIT
        call PSG_INIT

        ; --- the game ------------------------------------------
        call GAME_START

        ; back to the BIOS
        ret

;==========================================================
; SETBANK - select the bank shown at $8000-$BFFF
;----------------------------------------------------------
; Input: A = bank number
; The current bank is kept in RAM so it can be restored.
;==========================================================
SETBANK:
        push af
        and  $0F                    ; 16 banks are enough
        out  (BANK_B), a
        ld   (cur_bank), a
        pop  af
        ret

;==========================================================
; GETBANK - return the bank currently at $8000-$BFFF
;==========================================================
GETBANK:
        ld   a, (cur_bank)
        ret

;==========================================================
; VDP_INIT - configure the VDP for SCREEN 2 by hand
;==========================================================
VDP_INIT:
        push af
        push bc
        push de
        push hl

        ld   b, VDP_R0
        ld   c, 0
        call VDP_SETREG
        ld   b, VDP_R1
        ld   c, 1
        call VDP_SETREG
        ld   b, VDP_R2
        ld   c, 2
        call VDP_SETREG
        ld   b, VDP_R3
        ld   c, 3
        call VDP_SETREG
        ld   b, VDP_R4
        ld   c, 4
        call VDP_SETREG
        ld   b, VDP_R5
        ld   c, 5
        call VDP_SETREG
        ld   b, VDP_R6
        ld   c, 6
        call VDP_SETREG
        ld   b, VDP_R7
        ld   c, 7
        call VDP_SETREG

        ; clear the whole VRAM
        call VDP_CLEAR

        pop   hl
        pop   de
        pop   bc
        pop   af
        ret

;----------------------------------------------------------
; VDP_SETREG - write a VDP mode register
;----------------------------------------------------------
; Input: B = value, C = register number
;----------------------------------------------------------
VDP_SETREG:
        ld   a, b
        out  (VDP_CMD), a
        ld   a, c
        or   $80
        out  (VDP_CMD), a
        ret

;----------------------------------------------------------
; VDP_SETADDR - set the VRAM write address
;----------------------------------------------------------
; Input: H = high byte, L = low byte
;----------------------------------------------------------
VDP_SETADDR:
        ld   a, l
        out  (VDP_CMD), a
        ld   a, h
        or   $40
        out  (VDP_CMD), a
        ret

;----------------------------------------------------------
; VDP_CLEAR - clear the 16K of VRAM
;----------------------------------------------------------
VDP_CLEAR:
        push af
        push bc
        push de
        push hl

        ld   h, 0
        ld   l, 0
        call VDP_SETADDR

        ld   bc, $4000
        xor  a
vdp_clear_loop:
        out  (VDP_DAT), a
        dec  bc
        ld   a, b
        or   c
        ld   a, 0
        jr   nz, vdp_clear_loop

        pop   hl
        pop   de
        pop   bc
        pop   af
        ret

;==========================================================
; PSG_INIT - silence every channel
;==========================================================
PSG_INIT:
        push af
        push bc

        ld   a, $07                 ; mixer register
        out  (PSG_REG), a
        ld   a, $3F                 ; all channels off
        out  (PSG_REG), a

        ld   a, $08                 ; channel A volume
        out  (PSG_REG), a
        xor  a
        out  (PSG_DAT), a
        ld   a, $09
        out  (PSG_REG), a
        out  (PSG_DAT), a
        ld   a, $0A
        out  (PSG_REG), a
        out  (PSG_DAT), a

        pop   bc
        pop   af
        ret

;==========================================================
; GAME_START - placeholder, the real game goes here
;==========================================================
GAME_START:
        ret

        end
