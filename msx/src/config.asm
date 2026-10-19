;==========================================================
; Cybernoid MSX - shared build configuration
;----------------------------------------------------------
; The build script substitutes these placeholders:
;   @IO_BASE@    base address of the I/O routines
;   @INIT_BASE@  base address of the init code
;   @VIDEO_BASE@ base address of the video module
;   @KBD_BUF@    address of the 8-byte keyboard buffer (must be RAM)
;
; Two variants are produced:
;   * .COM  (MSX-DOS 2)  - modules live in MSX RAM at $0200/$0300/$0400
;   * .ROM  (cartridge)  - modules live in cartridge ROM at $4040/$4200/$4400
;==========================================================

IO_BASE     EQU @IO_BASE@
INIT_BASE   EQU @INIT_BASE@
VIDEO_BASE  EQU @VIDEO_BASE@
KBD_BUF     EQU @KBD_BUF@

; Screen memory (Spectrum layout) - must be RAM
SCREEN_PIX  EQU $4000
SCREEN_ATT  EQU $5800

; MSX VDP VRAM layout (Graphics Mode 2)
PATTERN_TBL EQU $0000
COLOUR_TBL  EQU $2000
NAME_TBL    EQU $3800

; Game entry point (Spectrum address, unchanged)
GAME_ENTRY  EQU $6504

; I/O routine offsets relative to IO_BASE
IO_KBD_READ   EQU IO_BASE + 0
IO_BEEPER     EQU IO_BASE + 127
IO_IM2        EQU IO_BASE + 196

; Absolute addresses of the I/O routines, used by the other modules
ADDR_KBD_READ  EQU IO_KBD_READ
ADDR_BEEPER    EQU IO_BEEPER
ADDR_IM2       EQU IO_IM2

; Video routine offsets relative to VIDEO_BASE
; (the two VDP helpers come first, then the public routines)
VID_INIT      EQU VIDEO_BASE + 18
VID_SYNC      EQU VIDEO_BASE + 237
VID_SYNC_ROWS EQU VIDEO_BASE + 245

; Absolute addresses used by the other modules
ADDR_VID_INIT      EQU VID_INIT
ADDR_VID_SYNC      EQU VID_SYNC
ADDR_VID_SYNC_ROWS EQU VID_SYNC_ROWS

; Entry point of the init code
ADDR_INIT          EQU INIT_BASE

;----------------------------------------------------------
; Data areas (must be in writable RAM and must not overlap code)
;----------------------------------------------------------
; video module occupies $0400-$05B2, so the data starts at $05C0
DATA_SYNC_ROW  EQU $05C0      ; 1 byte  - rotating row cursor
DATA_COLTAB    EQU $05C1      ; 256 bytes - Spectrum attr -> MSX colour
DATA_KBD_BUF   EQU $0700      ; 8 bytes  - Spectrum-style key state
