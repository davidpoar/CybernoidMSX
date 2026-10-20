;==========================================================
; Cybernoid MSX - 64K ROM cartridge (ASCII16 mapper)
;----------------------------------------------------------
; File layout (64 KB = 4 banks of 16 KB):
;
;   file $0000-$3FFF (bank 0) -> MSX $4000-$7FFF
;        "AB" header, engine: INIT, VDP routines, bank switching,
;        the vblank handler and the VRAM loader
;   file $4000-$7FFF (bank 1) -> MSX $8000-$BFFF (window)
;        the screen: name table, pattern table, colour table
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
; The interrupt hook of the BIOS
;
; The MSX1 BIOS calls the address in $FD9A on every interrupt and the
; address in $FD9F when the VDP raises the interrupt.  Both live in
; the RAM of page 3, so we can put a JP there and get control at the
; start of every vblank.  That is where the VRAM has to be written:
; on real hardware the VDP only allows VRAM access during the
; vertical blanking period.
;----------------------------------------------------------
INT_HOOK_VDP equ $FD9F

;----------------------------------------------------------
; RAM layout (page 3, $C000-$F37F)
;----------------------------------------------------------
cur_bank    equ $C000          ; bank currently in the $8000 window
our_slot    equ $C001          ; primary slot of this cartridge
slot_id     equ $C002          ; slot id (with the expander flag)
saved_reg   equ $C003          ; primary slot register at boot
bank_result equ $C004          ; result of the bank self test
page2_test equ $C005          ; what was read at $8000 in the check
frame_count equ $C006         ; incremented by the vblank handler
job_phase   equ $C010          ; phase of the VRAM loader
job_dst     equ $C011          ; 2 bytes: the VRAM address to write
job_src     equ $C013          ; 2 bytes: the source in the bank
job_pages   equ $C015          ; 2 bytes: 256 byte pages left

;----------------------------------------------------------
; Bank registers of the ASCII16 mapper (ordinary memory)
;----------------------------------------------------------
BANK_A  equ $6000              ; selects the bank at $4000-$7FFF
BANK_B  equ $7000              ; selects the bank at $8000-$BFFF

;----------------------------------------------------------
; SCREEN 2 (Graphic II) VRAM layout
;   $0000-$17FF  pattern generator (3 thirds of 2 KB)
;   $1800-$1AFF  name table      (768 bytes)
;   $2000-$37FF  colour table     (3 thirds of 2 KB)
;   $3800-$3FFF  sprite patterns
;   $1B00-$1FFF  sprite attributes
;
; The colour table has an exact byte to byte mapping with the pattern
; table: the entry at the same offset gives the colour of the 0 and
; the 1 pixels of that pixel line.
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

;----------------------------------------------------------
; The VRAM loader
;
; The screen data lives in the first asset bank, so the engine only
; has to copy it to the VRAM.  On real hardware that copy can only
; happen during the vblank, so it is spread over several frames:
; one page (256 bytes) per frame.
;
; job_pages counts the pages that are left.  It is stored with the
; count in the high byte, because every part starts at an address
; that is a multiple of 256.
;----------------------------------------------------------
SLICE        equ 256           ; bytes copied per frame
NAME_PAGES   equ $0300         ; 3 pages: 768 bytes
PAT_PAGES    equ $1800         ; 24 pages: 6144 bytes
COL_PAGES    equ $1800         ; 24 pages: 6144 bytes
SPR_PAGES    equ $0100         ; 1 page: 256 bytes
SPRPAT_PAGES equ $0800         ; 8 pages: 2048 bytes

; The addresses of each part inside the asset bank, as they are seen
; through the $8000 window.  Offset 0 of the bank is the ID byte, so
; the data starts at $8001.
DATA_NAME     equ $8001
DATA_PATTERN  equ $8301        ; $8001 + 3 pages
DATA_COLOUR   equ $9B01        ; $8301 + 24 pages
DATA_SPRATTR  equ $B301        ; $9B01 + 24 pages
DATA_SPRPAT   equ $B401        ; $B301 + 1 page

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
        and  $03                   ; the subslot of page 1
        ld   (our_slot), a

        ; --- slot id for ENASLT ------------------------------------
        ; The format is FxxxSSPP: bit 7 says the slot is expanded,
        ; bits 2-3 are the secondary slot and bits 0-1 the primary
        ; slot.  The MSX1 BIOS only looks at bits 0-1, but the MSX2
        ; BIOS needs the secondary slot as well.
        ld   a, (our_slot)
        ld   e, a
        ld   d, 0
        ld   hl, $FCC1              ; EXPTBL
        add  hl, de
        ld   a, (hl)
        and  $80                   ; only the "expanded" flag
        ld   c, a
        ld   hl, $FCC5              ; SLTTBL
        add  hl, de
        ld   a, (hl)
        and  $0C
        or   e                      ; the primary slot
        or   c                      ; A = FxxxSSPP
        ld   (slot_id), a

        ; --- make sure page 2 shows our cartridge -----------------
        ; The MSX1 BIOS already maps pages 1 AND 2 of the cartridge
        ; slot when it detects a two window mapper, so normally
        ; there is nothing to do.  We check it with the ID byte of
        ; the first asset bank: if page 2 were not the cartridge the
        ; read would come from the RAM and the value would not be $B1.
        ld   a, 1
        call SETBANK_B
        ld   a, ($8000)
        ld   (page2_test), a
        cp   $B1
        jr   z, page2_ok
        ld   a, (slot_id)
        ld   hl, $8000
        call ENASLT
        ld   a, 1
        call SETBANK_B
page2_ok:

        ; --- our vblank handler -----------------------------------
        ; Put a JP in the hook the BIOS calls on a VDP interrupt.
        ld   hl, INT_HOOK_VDP
        ld   (hl), $C3              ; JP nn
        inc  hl
        ld   de, ISR
        ld   (hl), e                ; the low byte
        inc  hl
        ld   (hl), d                ; the high byte

        ; --- bank registers -------------------------------------
        ; The bank registers are plain memory in the ASCII16 mapper:
        ;   $6000-$67FF selects the bank shown at $4000-$7FFF
        ;   $7000-$77FF selects the bank shown at $8000-$BFFF
        ; Bank 0 must stay in the $4000 window (it holds the engine),
        ; so we never write to $6000.  The $8000 window starts on the
        ; first asset bank, which holds the screen.
        ld   a, 1
        call SETBANK_B

        ; --- hardware ------------------------------------------
        call VDP_INIT
        call PSG_INIT

        ; --- self test of the mapper ----------------------------
        call BANK_SELFTEST

        ; --- load the screen into the VRAM ----------------------
        call JOB_START

        ; --- the game ------------------------------------------
        ; Never returns: MAINLOOP does not come back here.
        jp   MAINLOOP

;==========================================================
; MAINLOOP - the main loop
;==========================================================
; The vblank handler increments frame_count, so the loop runs once
; per frame, in sync with the screen.
;
; We do not use HALT here on purpose: the loop waits for the frame
; counter with a software spin.  That keeps the cartridge usable by
; debuggers that stop the CPU as soon as it halts, and it costs
; nothing on a real MSX, where the same thing happens with the
; "wait for the vblank flag" technique.
;==========================================================
MAINLOOP:
        ei
        ld   a, (frame_count)
        ld   b, a
main_wait:
        ld   a, (frame_count)
        cp   b
        jr   z, main_wait
        ; --- game logic goes here ---
        jr   MAINLOOP

;==========================================================
; ISR - our VDP interrupt handler
;----------------------------------------------------------
; The BIOS calls the address in $FD9F at the start of the vblank,
; with every register already saved.  It uses A after the call, so A
; has to be preserved.
;==========================================================
ISR:
        push af
        push bc
        push de
        push hl
        call JOB_NEXT
        ld   hl, frame_count
        inc  (hl)                  ; the main loop waits for this
        pop   hl
        pop   de
        pop   bc
        pop   af
        ret

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
        pop   hl
        pop   de
        pop   bc
        pop   af
        ret

st_fail:
        ld   a, $FF
        ld   (bank_result), a
        ld   a, 1
        call SETBANK_B
        pop   hl
        pop   de
        pop   bc
        pop   af
        ret

;==========================================================
; JOB_START - prepare the VRAM loader
;----------------------------------------------------------
; The screen data is in the first asset bank.  It is copied to the
; VRAM one page per frame, during the vblank.
;==========================================================
JOB_START:
        xor  a
        ld   (job_phase), a
        ld   hl, NAME_BASE
        ld   (job_dst), hl
        ld   hl, DATA_NAME
        ld   (job_src), hl
        ld   hl, NAME_PAGES
        ld   (job_pages), hl
        ret

;==========================================================
; JOB_NEXT - copy the next page of the screen to the VRAM
;----------------------------------------------------------
; Called from the vblank handler.  Copies 256 bytes and advances to
; the next part of the screen when this one is finished.
;==========================================================
JOB_NEXT:
        ld   a, (job_phase)
        cp   5
        jp   nc, job_idle

        ; --- point the VDP at the destination ---
        ld   a, (job_dst)
        out  (VDP_CMD), a
        ld   a, (job_dst+1)
        or   $40
        out  (VDP_CMD), a

        ; --- the source inside the asset bank ---
        ; job_src is the full address in the $8000 window, so the
        ; data is read straight out of the cartridge.
        ld   a, (job_src)
        ld   l, a
        ld   a, (job_src+1)
        ld   h, a
        ld   d, a                  ; D keeps the high byte: the copy
                                  ; loop below moves HL

        ; --- copy one page ---
        ld   bc, SLICE
job_copy:
        ld   a, (hl)
        out  (VDP_DAT), a
        inc  hl
        dec  bc
        ld   a, b
        or   c
        jr   nz, job_copy

        ; --- advance the source by one page ($100) ---
        ; Every part starts at an address that is a multiple of 256,
        ; so only the high byte changes.
        inc  d
        ld   a, d
        ld   (job_src+1), a

        ; --- advance the destination by one page ($100) ---
        ld   a, (job_dst+1)
        inc  a
        ld   (job_dst+1), a

        ; --- one page less ---
        ld   a, (job_pages+1)
        dec  a
        ld   (job_pages+1), a
        ld   a, (job_pages+1)
        or   a
        jr   nz, job_done        ; there are still pages left

        ; --- this part is finished: on to the next one ---
        ld   a, (job_phase)
        inc  a
        ld   (job_phase), a
        cp   5
        ret  z
        cp   1
        jp   z, job_pattern
        cp   2
        jp   z, job_colour
        cp   3
        jp   z, job_sprattr
        ; the sprite patterns
        ld   hl, SPRPAT_BASE
        ld   (job_dst), hl
        ld   hl, DATA_SPRPAT
        ld   (job_src), hl
        ld   hl, SPRPAT_PAGES
        ld   (job_pages), hl
        ret
job_pattern:
        ld   hl, PATTERN_BASE
        ld   (job_dst), hl
        ld   hl, DATA_PATTERN
        ld   (job_src), hl
        ld   hl, PAT_PAGES
        ld   (job_pages), hl
        ret
job_colour:
        ld   hl, COLOUR_BASE
        ld   (job_dst), hl
        ld   hl, DATA_COLOUR
        ld   (job_src), hl
        ld   hl, COL_PAGES
        ld   (job_pages), hl
        ret
job_sprattr:
        ld   hl, SPRATTR_BASE
        ld   (job_dst), hl
        ld   hl, DATA_SPRATTR
        ld   (job_src), hl
        ld   hl, SPR_PAGES
        ld   (job_pages), hl
        ret

job_done:
        ret

job_idle:
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

;==========================================================
; PSG_INIT - silence every channel
;==========================================================
; The PSG has two ports: $A0 selects the register and $A1 takes
; the data.  Every channel needs its volume at zero, otherwise it
; would make noise at boot.
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
        xor  a
        out  (PSG_DAT), a
        ld   a, $0A                 ; channel C volume
        out  (PSG_REG), a
        xor  a
        out  (PSG_DAT), a

        pop   bc
        pop   af
        ret

        end
