#!/usr/bin/env python3
"""Decrypt the Cybernoid loader code (XOR with consecutive bytes)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import RAW_BLOCK_05, LOADER_DECRYPTED


def decrypt(encrypted_path, output_path):
    with open(encrypted_path, 'rb') as f:
        data = bytearray(f.read())

    # Layout (770 bytes = 1 flag + 768 code + 1 checksum):
    # - byte 0: 0xFF flag (data)
    # - bytes 1-768: code (starts at $FC00)
    # - byte 769: checksum
    code = data[1:-1]
    assert len(code) == 768, f'Expected 768 bytes, got {len(code)}'

    # The loader self-decrypts bytes from $FC13 onwards using XOR with the
    # byte that follows each one. This means:
    #   decrypted[i] = encrypted[i] XOR encrypted[i+1]
    # for the first 668 bytes (indices 0..667 within the $FC13 region).
    # The last byte (index 668) is XORed with encrypted[669], which is one
    # byte beyond the 669-byte decrypted region.
    start_off = 0x13      # offset in buffer where decryption starts
    count = 669           # BC = $029D = 669

    encrypted = bytearray(code)
    decrypted = bytearray(code)
    for i in range(count - 1):
        decrypted[start_off + i] = encrypted[start_off + i] ^ encrypted[start_off + i + 1]
    decrypted[start_off + count - 1] = (
        encrypted[start_off + count - 1] ^ encrypted[start_off + count]
    )

    with open(output_path, 'wb') as f:
        f.write(decrypted)
    print(f'Decrypted {count} bytes from $FC13 to $FEBF (in 768-byte buffer)')
    print(f'Loader file size: {len(decrypted)} bytes (loaded at $FC00)')
    print(f'Saved to: {output_path}')


if __name__ == '__main__':
    decrypt(RAW_BLOCK_05, LOADER_DECRYPTED)