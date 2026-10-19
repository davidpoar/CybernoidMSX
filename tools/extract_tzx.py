#!/usr/bin/env python3
"""Parse TZX file and extract raw block data."""
import sys
import struct
from pathlib import Path

# Allow imports from this script's directory
sys.path.insert(0, str(Path(__file__).parent))
from paths import TZX_FILE, RAW_BLOCKS_DIR


def parse_tzx(tzx_path, output_dir):
    """Parse a TZX file and write each block's raw data to a separate file."""
    with open(tzx_path, 'rb') as f:
        data = f.read()

    assert data[:8] == b'ZXTape!\x1a', f'Not a TZX file: {data[:8]!r}'
    print(f'Version: {data[7]}.{data[8]}')

    pos = 10
    block_idx = 0
    while pos < len(data):
        bid = data[pos]
        pos += 1
        block_idx += 1
        name = {0x10: 'STD', 0x11: 'TURBO', 0x12: 'PURE', 0x13: 'PULSES',
                0x14: 'SEQ', 0x15: 'SEQ', 0x20: 'PAUSE', 0x21: 'GRPSTART',
                0x22: 'GRPEND', 0x23: 'JUMP', 0x24: 'LOOPSTART', 0x25: 'LOOPEND',
                0x26: 'CALL', 0x27: 'RETURN', 0x28: 'TABLE', 0x2A: 'STOP48',
                0x30: 'TEXT', 0x31: 'MSG', 0x32: 'ARC', 0x33: 'HW',
                0x34: 'EMUL', 0x35: 'CONFD', 0x40: 'STDROM'}.get(bid, f'0x{bid:02X}')

        if bid == 0x10:  # Standard Speed Data Block
            pause = struct.unpack_from('<H', data, pos)[0]; pos += 2
            length = struct.unpack_from('<H', data, pos)[0]; pos += 2
            print(f'Block {block_idx}: {name} pause={pause}ms len={length}')
            out_path = Path(output_dir) / f'raw_block_{block_idx:02d}.bin'
            with open(out_path, 'wb') as out:
                out.write(data[pos:pos+length])
            pos += length
        elif bid == 0x11:  # Turbo Speed Data Block
            length = struct.unpack_from('<H', data, pos + 14)[0]
            pos = pos + 18 + length  # skip header + data
            print(f'Block {block_idx}: TURBO len={length}')
        elif bid == 0x12:  # Pure Tone
            pos += 4
            print(f'Block {block_idx}: {name}')
        elif bid == 0x13:  # Pulse sequence
            n = data[pos]; pos += 1 + 2*n
            print(f'Block {block_idx}: {name}')
        elif bid == 0x20:  # Pause
            pos += 2
            print(f'Block {block_idx}: {name}')
        elif bid == 0x21:  # Group start
            n = data[pos]; pos += 1 + n
            print(f'Block {block_idx}: {name}')
        elif bid == 0x22:  # Group end
            print(f'Block {block_idx}: {name}')
        elif bid == 0x23:  # Jump
            pos += 2
            print(f'Block {block_idx}: {name}')
        elif bid == 0x24:  # Loop start
            n = struct.unpack_from('<H', data, pos)[0]; pos += 2
            print(f'Block {block_idx}: LOOPSTART x{n}')
        elif bid == 0x25:  # Loop end
            print(f'Block {block_idx}: LOOPEND')
        elif bid == 0x26:  # Call seq
            n = struct.unpack_from('<H', data, pos)[0]; pos += 2 + 2*n
            print(f'Block {block_idx}: CALLSEQ x{n}')
        elif bid == 0x27:  # Return
            print(f'Block {block_idx}: RET')
        elif bid == 0x28:  # Table
            n = data[pos]; pos += 1
            pos += n*5
            print(f'Block {block_idx}: TABLE')
        elif bid == 0x2A:  # Stop the tape if 48K
            pos += 4
            print(f'Block {block_idx}: STOP48')
        elif bid == 0x30:  # Text description
            n = data[pos]; pos += 1
            txt = data[pos:pos+n]; pos += n
            print(f'Block {block_idx}: TEXT "{txt.decode("latin-1", errors="replace")}"')
        elif bid == 0x31:  # Message block
            n = data[pos]; pos += 1
            pos += n
            print(f'Block {block_idx}: MSG')
        elif bid == 0x32:  # Archive info
            n = struct.unpack_from('<H', data, pos)[0]; pos += 2 + n
            print(f'Block {block_idx}: ARC')
        elif bid == 0x33:  # HW info
            n = data[pos]; pos += 1 + n*3
            print(f'Block {block_idx}: HW')
        elif bid == 0x35:  # Custom info
            n = struct.unpack_from('<I', data, pos)[0]; pos += 4 + n
            print(f'Block {block_idx}: CUSTOM')
        else:
            print(f'Block {block_idx}: UNKNOWN 0x{bid:02X}, stopping at pos {pos-1}')
            break

    print('Done')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        tzx_path = sys.argv[1]
    else:
        tzx_path = TZX_FILE
    if len(sys.argv) > 2:
        out_dir = sys.argv[2]
    else:
        out_dir = RAW_BLOCKS_DIR
    parse_tzx(tzx_path, out_dir)