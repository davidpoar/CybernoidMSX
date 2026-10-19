;==========================================================
; Cybernoid MSX - I/O routines
;----------------------------------------------------------
; Replaces the Spectrum's port $FE access:
;   IN A,($FE)   -> MSX_KBD_READ  (keyboard matrix emulation)
;   OUT ($FE),A   -> MSX_BEEPER    (PSG + VDP border)
;
; No BIOS calls are used: these routines must work in "all RAM"
; mode where the MSX BIOS is not mapped.
;==========================================================

        INCLUDE "config.asm"

;----------------------------------------------------------
; MSX hardware ports
;----------------------------------------------------------
PPI_A      EQU $A8
PPI_B      EQU $A9
PPI_C      EQU $AA
VDP_DATA   EQU $98
VDP_CMD    EQU $99
PSG_REG    EQU $A0
PSG_DATA   EQU $A1

;----------------------------------------------------------
        org IO_BASE

        PUBLIC MSX_KBD_READ
        PUBLIC MSX_BEEPER
        PUBLIC MSX_IM2_HANDLER
        PUBLIC MSX_KBD_BUF

;----------------------------------------------------------
; MSX_KBD_READ
;----------------------------------------------------------
; Replacement for Spectrum IN A,($FE).
;
; Input:  A = Spectrum row selector (one bit clear selects the row)
; Output: A = 5-bit Spectrum-style key state (0 = pressed, 1 = released)
;
; The Spectrum has an 8x5 keyboard matrix; the MSX has an 11x8 one.
; We scan the MSX rows that matter and translate them into the
; equivalent Spectrum rows.
;----------------------------------------------------------
MSX_KBD_READ:
        PUSH HL
        PUSH BC
        PUSH DE

        LD   E, A                ; save the Spectrum row selector
        CALL SCAN_KBD

        LD   A, E
        LD   HL, MSX_KBD_BUF
        LD   B, 8
kbd_lookup_loop:
        RRA                     ; rotate the clear bit into the carry
        JR   C, kbd_lookup_skip  ; bit was 1 -> not this row
        LD   A, (HL)             ; found the row
        JR   kbd_lookup_done
kbd_lookup_skip:
        INC  HL
        DJNZ kbd_lookup_loop
        LD   A, $1F              ; nothing found: no key pressed
kbd_lookup_done:
        POP  DE
        POP  BC
        POP  HL
        RET

;----------------------------------------------------------
; SCAN_KBD - scan the MSX keyboard into MSX_KBD_BUF
;----------------------------------------------------------
; MSX keyboard matrix (PPI bit 7 = leftmost column).
; From the MSX Red Book key code table at $0DA5 (NORMAL rows):
;
;   Row 0: 0 1 2 3 4 5 6 7          Row 4: k l m n o p q r
;   Row 1: 8 9 . - @ [ ] ;          Row 5: s t u v w x y z
;   Row 2: ' ` , . / (GBP) a b       Row 8: SPACE at column 0
;   Row 3: c d e f g h i j
;
; Mapping to the Spectrum keys Cybernoid uses:
;   MSX row 5 bit 7 (Z)     -> Spectrum row $FE bit 1
;   MSX row 5 bit 5 (X)     -> Spectrum row $FE bit 2
;   MSX row 8 bit 0 (SPACE) -> Spectrum row $F7 bit 0  (fire)
;                         -> Spectrum row $7F bit 1
;----------------------------------------------------------
SCAN_KBD:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL

        ; reset the buffer to "no key pressed"
        LD   HL, MSX_KBD_BUF
        LD   B, 8
        LD   A, $1F
kbd_reset_loop:
        LD   (HL), A
        INC  HL
        DJNZ kbd_reset_loop

        ; --- Z (MSX row 5, bit 7) -> Spectrum $FE bit 1 ---
        LD   C, 5
        CALL READ_MSX_ROW
        BIT  7, A
        JR   NZ, no_z             ; 1 = not pressed
        LD   HL, MSX_KBD_BUF + 0
        LD   A, (HL)
        AND  ~$02
        LD   (HL), A
no_z:

        ; --- X (MSX row 5, bit 5) -> Spectrum $FE bit 2 ---
        LD   C, 5
        CALL READ_MSX_ROW
        BIT  5, A
        JR   NZ, no_x
        LD   HL, MSX_KBD_BUF + 0
        LD   A, (HL)
        AND  ~$04
        LD   (HL), A
no_x:

        ; --- SPACE (MSX row 8, bit 0) -> Spectrum $F7 bit 0 + $7F bit 1 ---
        LD   C, 8
        CALL READ_MSX_ROW
        BIT  0, A
        JR   NZ, no_space
        LD   HL, MSX_KBD_BUF + 3
        LD   A, (HL)
        AND  ~$01
        LD   (HL), A
        LD   HL, MSX_KBD_BUF + 7
        LD   A, (HL)
        AND  ~$02
        LD   (HL), A
no_space:

        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RET

;----------------------------------------------------------
; READ_MSX_ROW - read one row of the MSX keyboard matrix
;----------------------------------------------------------
; Input:  C = row number (0-10)
; Output: A = 8 column bits (0 = pressed, 1 = released)
;----------------------------------------------------------
READ_MSX_ROW:
        PUSH BC
        PUSH DE
        IN   A, (PPI_C)
        AND  $F0                    ; keep the cas/LED/click bits
        OR   C                      ; select the keyboard row
        OUT  (PPI_C), A
        NOP
        NOP
        IN   A, (PPI_B)
        POP  DE
        POP  BC
        RET

;----------------------------------------------------------
; MSX_KBD_BUF - 8 bytes of Spectrum-style key state
;----------------------------------------------------------
; Must live in writable RAM, not in cartridge ROM.
;----------------------------------------------------------
        org DATA_KBD_BUF
MSX_KBD_BUF:
        ds 8, $1F

;----------------------------------------------------------
; MSX_BEEPER
;----------------------------------------------------------
; Replacement for Spectrum OUT ($FE),A.
;
; Input: A = value
;   bits 0-2 : border colour
;   bit 4    : beeper state (1 = on)
;----------------------------------------------------------
        org IO_BEEPER
MSX_BEEPER:
        PUSH AF
        PUSH BC
        PUSH DE
        LD   D, A

        ; --- border colour -> VDP register 7 ---
        LD   A, D
        AND  $07
        OR   $F0                    ; bits 7-4 = text colour 1
        LD   (VDPREG7), A
        LD   C, 7
        CALL VDP_SETREG

        ; --- beeper -> PSG channel A ---
        LD   A, D
        AND  $10
        JR   Z, beeper_off

        LD   A, $07                 ; mixer register
        LD   C, PSG_REG
        OUT  (C), A
        LD   A, $3E                 ; tone A on, noise A off
        OUT  (C), A
        LD   A, $08                 ; channel A amplitude
        OUT  (C), A
        LD   A, $0F                 ; volume 15
        OUT  (PSG_DATA), A
        JR   beeper_done

beeper_off:
        LD   A, $07
        LD   C, PSG_REG
        OUT  (C), A
        LD   A, $3F                 ; all channels off
        OUT  (C), A
        LD   A, $08
        OUT  (C), A
        LD   A, $00                 ; volume 0
        OUT  (PSG_DATA), A

beeper_done:
        POP  DE
        POP  BC
        POP  AF
        RET

;----------------------------------------------------------
; VDP_SETREG - write a VDP mode register
;----------------------------------------------------------
; Input: A = value, C = register number
;----------------------------------------------------------
VDP_SETREG:
        OUT  (VDP_CMD), A
        LD   A, C
        OR   $80
        OUT  (VDP_CMD), A
        RET

;----------------------------------------------------------
; VDPREG7 - shadow copy of VDP register 7
;----------------------------------------------------------
VDPREG7:
        db $F1

;----------------------------------------------------------
; MSX_IM2_HANDLER
;----------------------------------------------------------
; 50 Hz interrupt handler. Calls the game's original IM 2
; handler at $70D3 (the game runs at its original Spectrum
; addresses, so this works unchanged).
;----------------------------------------------------------
        org IO_IM2
MSX_IM2_HANDLER:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL
        PUSH IX
        PUSH IY
        CALL $70D3
        POP  IY
        POP  IX
        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RETI

        end
