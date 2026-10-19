;==========================================================
; Cybernoid MSX - Init code
;----------------------------------------------------------
; Runs after the game data has been placed in MSX RAM.
;
;   1. Switch to "all RAM" mode so that pages 0 and 1 are RAM
;      (the game needs writable memory at $4000-$7FFF)
;   2. Install the IM 2 interrupt handler
;   3. Initialise the VDP (graphics mode 2) and the PSG
;   4. Build the video tables and start the game
;
; No BIOS calls are used: after the slot switch the MSX BIOS is
; no longer mapped.
;==========================================================

        INCLUDE "config.asm"

VDP_DATA   EQU $98
VDP_CMD    EQU $99
PSG_REG    EQU $A0
PSG_DATA   EQU $A1
PPI_A      EQU $A8

;----------------------------------------------------------
        org INIT_BASE

        PUBLIC MSX_INIT

;----------------------------------------------------------
; MSX_INIT
;----------------------------------------------------------
MSX_INIT:
        DI
        LD   SP, $F380

        ; --- switch every page to the RAM slot ---
        ; The MSX primary slot register selects the slot for each
        ; 16K page. Writing $FF points all four pages at the
        ; primary slot that holds the main RAM.
        LD   A, $FF
        OUT  (PPI_A), A

        ; --- set up IM 2 ---
        LD   A, $F0
        LD   I, A
        LD   HL, ADDR_IM2
        LD   ($F0FE), HL
        IM   2

        ; --- init the VDP (graphics mode 2) and the PSG ---
        CALL ADDR_VID_INIT
        CALL PSG_INIT

        ; --- clear the Spectrum screen buffer ---
        ; (the game expects a clean screen)
        CALL CLEAR_SCREEN

        ; --- start the game ---
        EI
        JP   GAME_ENTRY

;----------------------------------------------------------
; CLEAR_SCREEN - clear the Spectrum pixel + attribute buffers
;----------------------------------------------------------
; $4000-$57FF pixels (6144 bytes) and $5800-$5AFF attributes (768)
;----------------------------------------------------------
CLEAR_SCREEN:
        PUSH AF
        PUSH BC
        PUSH DE
        PUSH HL

        LD   HL, SCREEN_PIX
        LD   DE, SCREEN_PIX + 1
        LD   BC, $1800          ; 6144 bytes
        XOR  A
        LDIR

        LD   HL, SCREEN_ATT
        LD   DE, SCREEN_ATT + 1
        LD   BC, $0300          ; 768 bytes
        LDIR

        POP  HL
        POP  DE
        POP  BC
        POP  AF
        RET

;----------------------------------------------------------
; PSG_INIT - silence all PSG channels
;----------------------------------------------------------
PSG_INIT:
        PUSH AF
        PUSH BC

        LD   A, $07
        OUT  (PSG_REG), A
        LD   A, $3F
        OUT  (PSG_REG), A

        LD   A, $08
        OUT  (PSG_REG), A
        LD   A, $00
        OUT  (PSG_DATA), A

        LD   A, $09
        OUT  (PSG_REG), A
        LD   A, $00
        OUT  (PSG_DATA), A

        LD   A, $0A
        OUT  (PSG_REG), A
        LD   A, $00
        OUT  (PSG_DATA), A

        POP  BC
        POP  AF
        RET

        end
