#!/usr/bin/env python3
"""Run the full Cybernoid extraction pipeline (step 1)."""
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


def main():
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

    print('\n' + '=' * 60)
    print('Step 1 complete. Files in:')
    print(f'  - original/   : source TZX and raw blocks')
    print(f'  - spectrum/   : decrypted loader, memory images, disasm')
    print('=' * 60)


if __name__ == '__main__':
    main()