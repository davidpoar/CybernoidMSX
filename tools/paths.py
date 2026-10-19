#!/usr/bin/env python3
"""Common paths for Cybernoid porting tools."""
import os

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(TOOLS_DIR)

ORIGINAL_DIR = os.path.join(PROJECT_DIR, 'original')
RAW_BLOCKS_DIR = os.path.join(ORIGINAL_DIR, 'raw_blocks')

SPECTRUM_DIR = os.path.join(PROJECT_DIR, 'spectrum')
SPECTRUM_DISASM_DIR = os.path.join(SPECTRUM_DIR, 'disasm')

MSX_DIR = os.path.join(PROJECT_DIR, 'msx')

# Specific files
TZX_FILE = os.path.join(ORIGINAL_DIR, 'Cybernoid.tzx')
RAW_BLOCK_05 = os.path.join(RAW_BLOCKS_DIR, 'raw_block_05.bin')  # Encrypted loader
RAW_BLOCK_07 = os.path.join(RAW_BLOCKS_DIR, 'raw_block_07.bin')  # 4405 bytes data
RAW_BLOCK_09 = os.path.join(RAW_BLOCKS_DIR, 'raw_block_09.bin')  # 39676 bytes main game

LOADER_DECRYPTED = os.path.join(SPECTRUM_DIR, 'loader_decrypted.bin')
BLOCK9_MAIN = os.path.join(SPECTRUM_DIR, 'cybernoid_block9_main.bin')
MEM_BEFORE_LDDR = os.path.join(SPECTRUM_DIR, 'cybernoid_before_lddr.bin')
MEM_AFTER_LDDR = os.path.join(SPECTRUM_DIR, 'cybernoid_after_lddr.bin')

DISASM_LOADER = os.path.join(SPECTRUM_DISASM_DIR, 'loader_disasm.txt')
DISASM_BLOCK9 = os.path.join(SPECTRUM_DISASM_DIR, 'block9_disasm_start.txt')
DISASM_FULL = os.path.join(SPECTRUM_DISASM_DIR, 'cybernoid_full_disasm.txt')
DISASM_IO_MAP = os.path.join(SPECTRUM_DISASM_DIR, 'cybernoid_io_map.txt')
DISASM_SOUND = os.path.join(SPECTRUM_DISASM_DIR, 'cybernoid_sound.txt')


def abs_list():
    """Print all key paths (for debugging)."""
    for k, v in sorted(globals().items()):
        if k.isupper() and isinstance(v, str):
            print(f'{k:30s} {v}')


if __name__ == '__main__':
    print(f'Tools dir:    {TOOLS_DIR}')
    print(f'Project dir:  {PROJECT_DIR}')
    print()
    abs_list()