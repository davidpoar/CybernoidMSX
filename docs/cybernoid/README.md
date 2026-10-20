# Cybernoid - Analysis of the original Spectrum game

What was found in the `Cybernoid.tzx` tape image, and what it means
for the port.

| Document | Contents |
|----------|----------|
| [MEMORY_MAP.md](MEMORY_MAP.md) | What is in the tape, and the memory layout once the game starts |
| [IO_ROUTINES.md](IO_ROUTINES.md) | The keyboard, sound and video routines, with their addresses |
| [VIDEO_MODEL.md](VIDEO_MODEL.md) | How the Spectrum screen maps onto the MSX VDP |

## Summary

Cybernoid is a 48K Spectrum game with a self modifying loader:

```
$0000-$3FFF   MSX ROM (on the Spectrum: the 16K monitor)
$4000-$5AFF   screen pixels (6144 B) and attributes (768 B)
$5B00-$6103   system variables, zeroed at boot
$6104-$FBFF   the game, 39676 bytes
$FC00-$FFFF   the loader, 768 bytes, self decrypting
```

The tape has three payloads:

| Block | Bytes | What it is |
|-------|-------|------------|
| 1 | 17 | BASIC program header |
| 2 | 81 | `10 BORDER 0: PAPER 0: INK 7: CLEAR 24835: LOAD ""CODE : RANDOMIZE USR 64512` |
| 3 | 17 | CODE header, 768 bytes at `$FC00` |
| 4 | 770 | the loader, encrypted |
| 5 | 17 | custom header, type 42 |
| 6 | 4407 | the game data, loaded at `$8000` |
| 7 | 17 | custom header, type 42 |
| 8 | 39678 | the main game, loaded at `$6104` |

The loader decrypts itself, loads the two data blocks, and then runs a
`LDDR` that rearranges the whole address space. The game entry point
ends up at `$6504`.

**The game is 39676 bytes and has about 1200 absolute address
references inside `$6504-$FFFF`.** That is the fact that decides the
whole porting strategy: the code only runs if it sits at exactly the
same addresses as on the Spectrum, which needs 40 KB of contiguous
RAM. A MSX1 has 32 KB, so the binary port only works in all-RAM
mode (MSX-DOS 2, or an MSX2 with a memory mapper).

## Tooling

Everything in `tools/` works from the tape image:

| Script | What it does |
|--------|--------------|
| `extract_tzx.py` | splits the TZX into its blocks |
| `decrypt_loader.py` | undoes the loader's XOR cipher |
| `build_mem_image.py` | rebuilds the 48K image, simulating the LDDR |
| `disasm.py`, `disasm_game.py` | disassemble the loader and the game entry |
| `find_io.py`, `find_io_routines.py` | group the IN/OUT instructions by port |
| `find_keyboard.py` | find the keyboard scanning routines |
| `find_sound.py` | find the sound routines |
| `show_bytes.py` | dump the important data structures |
| `generate_notes.py` | write `spectrum/disasm/PORTING_NOTES.txt` |

Run them all with:

```bash
py tools/run_all.py
```

## Files produced

| File | What |
|------|------|
| `spectrum/loader_decrypted.bin` | the 768 byte loader, decrypted |
| `spectrum/cybernoid_before_lddr.bin` | the 48K image before the LDDR |
| `spectrum/cybernoid_after_lddr.bin` | the 48K image after the LDDR, which is what the game sees |
| `spectrum/cybernoid_block9_main.bin` | block 8 of the tape, 39676 bytes |
| `spectrum/disasm/PORTING_NOTES.txt` | the summary of the I/O routines |
