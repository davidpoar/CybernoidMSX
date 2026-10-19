#!/usr/bin/env python3
"""Run all Cybernoid analysis tools (steps 1 and 2)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import paths
from extract_tzx import parse_tzx
from decrypt_loader import decrypt
from build_mem_image import build
from disasm import main as disasm_main
from disasm_game import main as disasm_game_main
from find_io import main as find_io_main
from find_sound import main as find_sound_main
from find_io_routines import main as find_io_routines_main
from find_keyboard import main as find_keyboard_main
from show_bytes import main as show_bytes_main
from generate_notes import main as generate_notes_main


def step1():
    """Step 1: Extract TZX and build memory image."""
    print('=' * 60)
    print('STEP 1: Extracting Cybernoid from TZX')
    print('=' * 60)
    print('\n[1/6] Parsing TZX...')
    parse_tzx(paths.TZX_FILE, paths.RAW_BLOCKS_DIR)

    print('\n[2/6] Decrypting loader...')
    decrypt(paths.RAW_BLOCK_05, paths.LOADER_DECRYPTED)

    print('\n[3/6] Building memory images...')
    build(paths.LOADER_DECRYPTED, paths.RAW_BLOCK_07, paths.RAW_BLOCK_09,
          paths.MEM_BEFORE_LDDR, paths.MEM_AFTER_LDDR)

    print('\n[4/6] Disassembling loader...')
    disasm_main()

    print('\n[5/6] Disassembling game block 9 and entry...')
    disasm_game_main()

    print('\n[6/6] Analyzing I/O and sound...')
    find_io_main()
    find_sound_main()


def step2():
    """Step 2: Identify I/O routines."""
    print('=' * 60)
    print('STEP 2: Identifying I/O routines')
    print('=' * 60)

    print('\n[1/4] Finding I/O routines...')
    find_io_routines_main()

    print('\n[2/4] Finding keyboard routines...')
    find_keyboard_main()

    print('\n[3/4] Showing key data structures...')
    show_bytes_main()

    print('\n[4/4] Generating porting notes...')
    generate_notes_main()


def main():
    step1()
    print()
    step2()
    print()
    print('=' * 60)
    print('Steps 1-2 complete. See:')
    print(f'  {paths.SPECTRUM_DISASM_DIR}/PORTING_NOTES.txt')
    print('=' * 60)


if __name__ == '__main__':
    main()