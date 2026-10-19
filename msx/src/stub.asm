;==========================================================
; Cybernoid MSX - .COM entry stub
;----------------------------------------------------------
; Loaded by MSX-DOS at $0100. The game data follows this code
; in the same file:
;
;   $0100-$01FF : this stub
;   $0200-$02FF : I/O routines
;   $0300-$03FF : init code
;   $0400-$07FF : video module
;   $0800-$22FB : game part 1   (Spectrum $6504-$7FFF)
;   $2300-$A2FF : game part 2   (Spectrum $8000-$FFFF)
;
; The stub moves the game into its final place and starts it.
;==========================================================

        INCLUDE "config.asm"

        org $0100

;----------------------------------------------------------
; MSX_COM_STUB
;----------------------------------------------------------
        PUBLIC MSX_COM_STUB
MSX_COM_STUB:
        DI
        LD   SP, $F380

        ; --- copy game part 1: $0800 -> $6504 (6908 bytes) ---
        ; the destination is above the source, so a forward copy is safe
        LD   HL, $0800
        LD   DE, $6504
        LD   BC, $1AFC
        LDIR

        ; --- copy game part 2: $2300 -> $8000 (32768 bytes) ---
        ; the destination overlaps the source, so copy backwards
        LD   HL, $A2FF
        LD   DE, $FFFF
        LD   BC, $8000
        LDDR

        ; --- apply the runtime patch (part 2 lives in RAM) ---
        ; OUT ($FE),A at $8637 -> CALL MSX_BEEPER
        LD   HL, $8637
        LD   (HL), $CD
        INC  HL
        LD   A, ADDR_BEEPER & $FF
        LD   (HL), A
        INC  HL
        LD   A, ADDR_BEEPER / 256
        LD   (HL), A

        ; --- start the game ---
        JP   ADDR_INIT

        end
