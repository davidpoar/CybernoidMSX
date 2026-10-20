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
; Mapper (ASCII16): the bank registers are ordinary memory, so they
; are written with LD (nn),A and not with OUT:
;
;   $6000-$67FF : selects the bank visible at $4000-$7FFF
;   $7000-$77FF : selects the bank visible at $8000-$BFFF
;
; The engine always keeps bank 0 in the $4000 window.
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
RSLREG  equ $0138              ; A = primary slot register
ENASLT  equ $0024              ; A = slot id, HL = address

;----------------------------------------------------------
; MSX I/O ports
;----------------------------------------------------------
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
bank_result equ $C004          ; result of the bank self test
kbd_state   equ $C010          ; 11 bytes of MSX keyboard state
spr_x       equ $C020          ; sprite X positions
spr_y       equ $C030
spr_pat     equ $C040
spr_col     equ $C050
spr_n       equ $C060          ; number of active sprites

;----------------------------------------------------------
; Bank registers of the ASCII16 mapper (ordinary memory)
;----------------------------------------------------------
BANK_A  equ $6000              ; selects the bank at $4000-$7FFF
BANK_B  equ $7000              ; selects the bank at $8000-$BFFF

;----------------------------------------------------------
; SCREEN 2 (Graphic II) VRAM layout
;   $0000-$17FF  pattern generator (3 thirds of 2 KB)
;   $1800-$1FFF  name table      (768 bytes)
;   $2000-$37FF  colour table     (3 thirds of 2 KB)
;   $3800-$3FFF  sprite patterns
;   $1B00-$1FFF  sprite attributes
;----------------------------------------------------------
PATTERN_BASE  equ $0000
NAME_BASE     equ $1800
COLOUR_BASE  equ $2000
SPRPAT_BASE  equ $3800
SPRATTR_BASE equ $1B00

;----------------------------------------------------------
; VDP mode registers for SCREEN 2
;----------------------------------------------------------
VDP_R0  equ $02                ; graphics mode (M3=1)
VDP_R1  equ $E0                ; 16K VRAM, IRQ on, display on
VDP_R2  equ $06                ; name table at $1800
VDP_R3  equ $FF                ; colour table at $2000
VDP_R4  equ $03                ; pattern generator at $0000
VDP_R5  equ $36                ; sprite attributes at $1B00
VDP_R6  equ $07                ; sprite patterns at $3800
VDP_R7  equ $F1                ; border colour 1

;==========================================================
; INIT - called by the MSX BIOS at boot
;==========================================================
; The BIOS has pushed a return address on the stack before calling
; us.  We replace the stack pointer, so that address is lost and we
; must NEVER return to the BIOS: INIT ends by jumping to MAINLOOP.
;==========================================================
INIT:
        di
        ld   sp, $F380             ; stack at the end of the RAM

        ; --- find our own slot -----------------------------------
        ; The BIOS has our ROM mapped on page 1, so the primary
        ; slot of page 1 is us.
        call RSLREG                ; A = primary slot register
        ld   (saved_reg), a
        rrca
        rrca
        and  $03                   ; slot of page 1
        ld   c, a
        ld   b, $00
        ld   hl, $FCC1              ; EXPTBL
        add  hl, bc
        or   (hl)                  ; bit 7 set when the slot is expanded
        ld   c, a
        inc  hl
        inc  hl
        inc  hl
        inc  hl                    ; SLTTBL
        ld   a, (hl)
        and  $0C
        or   c                     ; A = F000SSPP
        ld   h, $80
        ld   (slot_id), a

        ; --- switch page 2 ($8000-$BFFF) to our cartridge ------
        ; This also disables the MSX BASIC ROM that normally
        ; occupies page 2.
        ld   a, (slot_id)
        ld   hl, $8000
        call ENASLT

        ; --- bank registers -------------------------------------
        ; Bank 0 must stay in the $4000 window, so we never write
        ; to $6000.  The $8000 window starts on bank 1.
        ld   a, 1
        call SETBANK_B

        ; --- hardware ------------------------------------------
        call VDP_INIT
        call PSG_INIT

        ; --- self test of the mapper ----------------------------
        call BANK_SELFTEST

        ; --- the game ------------------------------------------
        ; Never returns: MAINLOOP does not come back here.
        jp   MAINLOOP

;==========================================================
; MAINLOOP - the main loop
;==========================================================
; The VDP frame interrupt wakes us up once per frame, so the loop
; stays in sync with the screen.
;==========================================================
MAINLOOP:
        ei
        halt
        ; --- game logic goes here ---
        jr   MAINLOOP

;==========================================================
; SETBANK_B - select the bank shown at $8000-$BFFF
;----------------------------------------------------------
; Input: A = bank number
; The bank register is plain memory, so it is written with LD (nn),A.
; The current bank is also kept in RAM.
;==========================================================
SETBANK_B:
        ld   (cur_bank), a
        ld   (BANK_B), a
        ret

;==========================================================
; GETBANK - return the bank currently at $8000-$BFFF
;==========================================================
GETBANK:
        ld   a, (cur_bank)
        ret

;==========================================================
; BANK_SELFTEST - check that the mapper really switches banks
;----------------------------------------------------------
; Reads $8000 after selecting each bank and compares the result with
; the ID byte that the build script puts at the start of every asset
; bank.  The result is left in bank_result:
;   $00 = all banks answered correctly
;   $FF = at least one bank answered wrongly
;==========================================================
BANK_SELFTEST:
        push af
        push bc
        push de
        push hl

        xor  a
        ld   (bank_result), a

        ld   b, 1                   ; banks 1, 2 and 3
st_bank_loop:
        ld   a, b
        call SETBANK_B
        ld   a, ($8000)              ; the ID byte of the bank
        ld   c, a                    ; keep it
        ld   a, b
        add  a, $B0                  ; expected $B1, $B2 or $B3
        cp   c
        jr   nz, st_fail
        inc  b
        ld   a, b
        cp   4
        jr   c, st_bank_loop

        ; restore bank 1
        ld   a, 1
        call SETBANK_B
        pop  hl
        pop  de
        pop  bc
        pop  af
        ret

st_fail:
        ld   a, $FF
        ld   (bank_result), a
        ld   a, 1
        call SETBANK_B
        pop  hl
        pop  de
        pop  bc
        pop  af
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
; The PSG has two ports: $A0 selects the register and $A1 takes
; the data.
;==========================================================
PSG_INIT:
        push af
        push bc

        ld   a, $07                 ; mixer register
        out  (PSG_REG), a
        ld   a, $3F                 ; all channels off
        out  (PSG_DAT), a

        ld   a, $08                 ; channel A volume
        out  (PSG_REG), a
        xor  a
        out  (PSG_DAT), a
        ld   a, $09                 ; channel B volume
        out  (PSG_REG), a
        out  (PSG_DAT), a
        ld   a, $0A                 ; channel C volume
        out  (PSG_REG), a
        out  (PSG_DAT), a

        pop   bc
        pop   af
        ret

        end
